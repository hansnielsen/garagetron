#!/usr/bin/python

from flask import Flask, redirect, request
import requests

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
    return redirect('/garage?code=%d' % call('door'))

@app.route('/garage/light')
def light():
    return redirect('/garage?code=%d' % call('light'))

if __name__ == '__main__':
    app.run(port=4545)
