import requests
from settings import DOMAIN as domain

class BrowserId():
    headers = { 'content-type': 'application/x-www-form-urlencoded'}

    def __init__(assertion):
        self.assertion = assertion
   
    def verify():
        r = requests.post('https://browserid.org/verify', verify=False,params={'assertion':self.assertion, 'audience':domain} 
        data = r.json
        if data['status'] == 'okay' and data['email']:
            user = User.objects.filter(email=data['email']).first()
            if not user:
                user = User(email=data['email'])
                user.save()

            session['user_id'] = user.id
            session['user_email'] = user.email
