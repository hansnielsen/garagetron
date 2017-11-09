#!/usr/bin/python

from flask import Flask, redirect, request
import time
import threading

app = Flask('garage')

TEMPLATE = '''
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style type="text/css">
html, body {
    margin: auto;
    text-align: center;
}
a {
    font-size: 60pt;
}
</style>
<script>
var nextTimeout = null;

function post(which) {
    window.clearTimeout(nextTimeout);
    nextTimeout = null;

    var xhr = new XMLHttpRequest();
    xhr.onload = function (event) {
        var status = event.target.status;
        var elem = document.getElementById("status");
        elem.innerText = "Response: " + status;
        elem.style.display = "";

        nextTimeout = window.setTimeout(function () {
            elem.style.display = "none";
        }, 10000);
    }
    xhr.open("POST", "/garage/" + which);
    xhr.send();
}
</script>
</head><body>
<div><a href="#" onclick="post('garage')">Door</a></div>
<div><a href="#" onclick="post('light')">Light</a></div>
<div id="status" style="display: none; font-size: 24pt;" />
</body></html>
'''

class GpioToggler(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.pins = {}
        self.set_up_pin("garage", "408")
        self.set_up_pin("light", "409")

        # Once the other pins are ready, enable the opener
        self.enable("410")

    def enable(self, which):
        self.set_up_pin_raw(which, "0")

    def set_up_pin(self, name, which, value="0"):
        self.pins[name] = which
        self.set_up_pin_raw(which, value)


    def set_up_pin_raw(self, which, value):
        # export the pin
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write(which)
        except:
            # if this is already exported, the write will fail; continue anyways
            pass
        # set the direction
        with open("/sys/class/gpio/gpio%s/direction" % which, "w") as f:
            f.write("out")
        # set the output to zero
        with open("/sys/class/gpio/gpio%s/value" % which, "w") as f:
            f.write(value)

    def toggle_pin(self, pin):
        if self.pins.has_key(pin) == False:
            print "Bad pin %s" % pin
            return 400
        has_lock = self.lock.acquire(False)
        if has_lock:
            t = threading.Thread(target=self.toggle_pin_worker, args=(pin,))
            t.start()
            return 200
        else:
            return 409

    def toggle_pin_worker(self, pin):
        try:
            print "Toggling pin %s" % pin
            with open("/sys/class/gpio/gpio%s/value" % self.pins[pin], "w") as f:
                f.write("1")
                f.flush()
                time.sleep(0.25)
                f.write("0")
                f.flush()
            time.sleep(1.25)
            print "Unlocking!"
        except Exception as e:
            print "Something broke: %s" % e
        finally:
            self.lock.release()

@app.route('/')
def slash():
    return redirect('/garage')

@app.route('/garage')
def garage():
    return TEMPLATE

@app.route('/garage/<which>', methods=['POST'])
def garage_post(which):
    return "", toggler.toggle_pin(which)

if __name__ == '__main__':
    toggler = GpioToggler()
    app.run(host='0.0.0.0', port=80)
