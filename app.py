import base64
import random
import time

import settings

db = settings.DATABASE

class Application:
    def __init__(self):
        self.token = ''

    def get_or_create_email(self, email):
        """Find the email address in the system
        or create it if it doesn't exist.
        """
        email = email.lower().strip()
        if not db.get('user:%s' % email):
            token = self._generate_token(email)
            db.set('user:%s' % email, token)
            db.set('user:%s' % token, email)

        token = db.get('user:%s' % email)
        email = db.get('user:%s' % token)

        self.token = token
        return {'email':email, 'token':token}

    def get_email_by_token(self, token):
        """Return user's email by token reference"""
        return db.get('user:%s' % self.token)

    def _generate_token(self, email):
        """Generate a token based on the timestamp
        and the user's email address.
        """
        random_int = str(random.randrange(100, 10000))
        token_string = '%s%s%s' % (random_int,
                                   email,
                                   str(int(time.time())))
        return base64.b64encode(token_string)