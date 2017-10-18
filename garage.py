#!/usr/bin/python

from flask import Flask, redirect, request
import requests
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
</head><body>
<div><a href="/garage/door">Door</a></div>
<div><a href="/garage/light">Light</a></div>
</body></html>
'''

class GpioToggler(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.pins = {}
        self.set_up_pin("garage", "408")
        self.set_up_pin("light", "409")

    def set_up_pin(self, name, which):
        self.pins[name] = which

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
            f.write("0")

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
                time.sleep(1)
                f.write("0")
                f.flush()
            time.sleep(2)
            print "Unlocking!"
        except Exception as e:
            print "Something broke: %s" % e
        self.lock.release()

@app.route('/')
def slash():
    return redirect('/garage')

@app.route('/garage')
def garage():
    code = request.args.get('code')
    if code is not None and code.isdigit():
        return TEMPLATE + ('Response: %s' % code)
    return TEMPLATE

@app.route('/garage/door')
def door():
    return redirect('/garage?code=%s' % toggler.toggle_pin("garage"))

@app.route('/garage/light')
def light():
    return redirect('/garage?code=%s' % toggler.toggle_pin("light"))

if __name__ == '__main__':
    toggler = GpioToggler()
    app.run(host='0.0.0.0', port=4545)
