# -*- coding: utf-8 -*-
import md5
from functools import wraps
from flask import redirect, session, url_for, request
import bleach

import settings


def authenticated(f):
    """Check if user is logged in"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_email'):
            return redirect(url_for('main'))
        return f(*args, **kwargs)
    return decorated

def clean(f):
    """Clean return value"""
    @wraps(f)
    def decorated(*args, **kwargs):
        r = f(*args, **kwargs)
        return bleach.clean(r, tags=settings.ALLOWED_TAGS)
    return decorated