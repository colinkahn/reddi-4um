import datetime
import calendar
from mongoengine import *
from mongoengine import signals
from settings import DATABASE as redisDB

connect('forum')

### Helpers ###

to_timestamp = lambda dt: calendar.timegm(dt.utctimetuple())
from_timestamp = lambda ts: datetime.datetime.fromtimestamp(float(ts))

class Version(object):
    def __init__(self, content,timestamp):
        self.content = content
        self.date = from_timestamp(timestamp)

### Mixins ###

class RawIdMixin(object):
    @property
    def raw_id(self):
        return str(self.id)


### Models ###

class User(Document, RawIdMixin):
    name = StringField()
    email = EmailField(required=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    @property
    def username(self):
        return self.name or 'anon'


class Comment(EmbeddedDocument, RawIdMixin):
    content = StringField(required=True)
    user = ReferenceField(User, required=True)
    created_at = DateTimeField(default=datetime.datetime.now)


class Topic(Document, RawIdMixin):
    title = StringField(required=True)
    content = StringField(required=True)
    user = ReferenceField(User, required=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    comments = ListField(EmbeddedDocumentField(Comment))

    meta = {
        'ordering': ['-updated_at']
    }

    def update_history(self):
        '''
        Adds a new version to the Topics history
        '''
        redisDB.zadd('Forum:History:Topic:%s' % self.raw_id, self.content, to_timestamp(self.updated_at))

    @property
    def history_count(self):
        return redisDB.zcount('Forum:History:Topic:%s' % self.raw_id, '-inf', '+inf')

    @property
    def history(self):
        return [Version(*t) for t in redisDB.zrange('Forum:History:Topic:%s' % self.raw_id, 0, -1, withscores=True)]


### Signals ###

def update_updated_at(sender, document, **kwargs):
    document.updated_at = datetime.datetime.now()

signals.pre_save.connect(update_updated_at, sender=Topic)

def redis_updates_for_topic(sender, document, **kwargs):
    document.update_history()

signals.post_save.connect(redis_updates_for_topic, sender=Topic)