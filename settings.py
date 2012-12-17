import redis
import os

# key must be 16, 24 or 32 bytes long
SECRET_KEY = 'SECRET_KEY'

SESSION_SECRET = 'SESSION_SECRET'

DOMAIN = os.getenv('DOMAIN', 'http://localhost:5000')

DEBUG = True

ALLOWED_TAGS = ['a', 'b', 'em', 'i', 'li', 'ol', 'strong', 'ul', 'br', 'h1', 'h2', 'u']

PER_PAGE = 6

REDIS_URL = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
DATABASE = redis.from_url(REDIS_URL)