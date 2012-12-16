import requests
from settings import DOMAIN as domain

headers = { 'content-type': 'application/x-www-form-urlencoded'}

def verify(assertion):
    r = requests.post('https://browserid.org/verify', params={'assertion':assertion, 'audience':domain}, headers=headers, verify=False)
    return r.json
