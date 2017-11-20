#!/usr/bin/python

from flask import Flask, redirect, request, session, render_template_string, abort
import time
import threading
import os
from base64 import b64encode

import config

app = Flask('garage')

TEMPLATE = '''
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Garage door opener</title>
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
var csrfToken = "{{ csrf_token }}";

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
    xhr.setRequestHeader("X-CSRF-Token", csrfToken);
    xhr.send();
}
</script>
</head><body>
{% for pin in pins %}
<div><a href="#" onclick="post('{{ pin }}')">{{ pins[pin]["desc"] }}</a></div>
{% endfor %}
<div id="status" style="display: none; font-size: 24pt;" />
</body></html>
'''

class GpioToggler(object):
    def __init__(self, config):
        self.lock = threading.Lock()
        self.pins = {}
        for pin in config["remote_outputs"]:
            self.set_up_pin(pin)

        # Once the other pins are ready, enable the opener
        for pin in config["poweron_outputs"]:
            self.set_up_pin_raw(pin["gpio"], pin["default_value"])

    def set_up_pin(self, pin):
        self.pins[pin["id"]] = {
            "desc": pin["desc"],
            "gpio": pin["gpio"],
            "active_low": pin["active_low"],
        }
        self.set_up_pin_raw(pin["gpio"], "1" if pin["active_low"] else "0")

    def set_up_pin_raw(self, which, default_value):
        # export the pin
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write("%d" % which)
        except:
            # if this is already exported, the write will fail; continue anyways
            pass
        # set the direction
        with open("/sys/class/gpio/gpio%s/direction" % which, "w") as f:
            f.write("out")
        # set the output to the default
        with open("/sys/class/gpio/gpio%s/value" % which, "w") as f:
            f.write(default_value)

    def toggle_pin(self, pin):
        if self.pins.has_key(pin) == False:
            print("Bad pin %s" % pin)
            return 400
        has_lock = self.lock.acquire(False)
        if has_lock:
            t = threading.Thread(target=self.toggle_pin_worker, args=(self.pins[pin],))
            t.start()
            return 200
        else:
            return 409

    def toggle_pin_worker(self, pin):
        try:
            print("Toggling pin %d" % pin["gpio"])
            with open("/sys/class/gpio/gpio%s/value" % pin["gpio"], "w") as f:
                f.write("0" if pin["active_low"] else "1")
                f.flush()
                time.sleep(0.25)
                f.write("1" if pin["active_low"] else "0")
                f.flush()
            time.sleep(1.25)
            print("Unlocking!")
        except Exception as e:
            print("Something broke: %s" % e)
        finally:
            self.lock.release()

def csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = b64encode(os.urandom(24))
    return session['_csrf_token']

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get('_csrf_token', None)
        if not token or token != request.headers.get('X-CSRF-Token'):
            print("Got bad CSRF token in request! Origin was %s" % (request.headers.get("Origin")))
            abort(400)

@app.route('/')
def slash():
    return redirect('/garage')

@app.route('/garage')
def garage():
    params = {
      "csrf_token": csrf_token(),
      "pins": toggler.pins,
    }
    return render_template_string(TEMPLATE, **params)

@app.route('/garage/<which>', methods=['POST'])
def garage_post(which):
    return "", toggler.toggle_pin(which)

if __name__ == '__main__':
    toggler = GpioToggler(config.OPENER_CONFIG)
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0', port=80)
