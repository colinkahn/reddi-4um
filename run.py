import simplejson as json
import time

from httplib2 import Http
from urllib import urlencode

import settings

from app import Application

from flask import (Flask, jsonify, redirect,
                   render_template, request, session, url_for)

app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = settings.SESSION_SECRET

h = Http()
a = Application()

@app.route("/")
def main():
    return render_template('index.html')


@app.route('/set_email', methods=['POST'])
def set_email():
    """Verify via BrowserID and upon success, set
    the email for the user unless it already
    exists and return the token.
    """
    bid_fields = {'assertion':request.form['bid_assertion'],
                  'audience':settings.DOMAIN}
    headers = {'Content-type':'application/x-www-form-urlencoded'}
    h.disable_ssl_certificate_validation=True
    resp, content = h.request('https://browserid.org/verify',
                              'POST',
                              body=urlencode(bid_fields),
                              headers=headers)
    bid_data = json.loads(content)
    if bid_data['status'] == 'okay' and bid_data['email']:
        a.get_or_create_email(bid_data['email'])
        session['user_token'] = a.token
        session['user_email'] = bid_data['email']

    return redirect(url_for('main'))


@app.route('/logout', methods=['GET'])
def logout():
    """Log the user out"""
    session['user_token'] = None
    session['user_email'] = None
    return redirect(url_for('main'))


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html')


@app.errorhandler(500)
def something_broke(error):
    return render_template('500.html')


if __name__ == "__main__":
    app.run()