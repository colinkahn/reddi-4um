import datetime
import calendar
from mongoengine import *
from mongoengine import signals
from settings import DATABASE as redisDB
from diff_match_patch import diff_match_patch
from flask import session

connect('forum')

### Helpers ###

to_timestamp = lambda dt: calendar.timegm(dt.utctimetuple())
from_timestamp = lambda ts: datetime.datetime.fromtimestamp(float(ts))

currentUser = lambda: User.objects.with_id(session['user_id'])

class Version(object):
    def __init__(self, content,timestamp):
        self.content = content
        self.date = from_timestamp(timestamp)


class Tag(object):
    def __init__(self,name):
        self.name = name

    def load(self):
        self.topic_ids = redisDB.smembers('Forum:Tag:%s:Topics' % self.name)
        return self

    def topic_count(self):
        return redisDB.scard('Forum:Tag:%s:Topics' % self.name)

    def topics(self):
        return Topic.objects.filter(pk__in=[pk for pk in self.topic_ids if pk])



def all_tags():
    tags = []
    names = redisDB.smembers('Forum:Tags:All')
    for name in names:
        tag = Tag(name).load()
        # A tag might not be currently used, if is add it
        if len(tag.topic_ids):
            tags.append(tag)

    return tags

def diff_prettyHtml(self, diffs):
    html = []
    for (op, data) in diffs:
        text = data

        if op == self.DIFF_INSERT:
            html.append("<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
        elif op == self.DIFF_DELETE:
            html.append("<del style=\"background:#ffe6e6;\">%s</del>" % text)
        elif op == self.DIFF_EQUAL:
            html.append("<span>%s</span>" % text)

    return "".join(html)

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

    def storeInRedis(self):
        redisDB.sadd('Forum:Users:All', self.raw_id)

    def readTopic(self, topic):
        redisDB.sadd('Forum:User:%s:HasRead' % self.raw_id, topic.raw_id)


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
        dmp = diff_match_patch()

        # Get the last version of the text
        last = redisDB.lrange('Forum:History:Topic:%s:Raw' % self.raw_id, -1, -1)
        if not len(last):
            diff = self.content
        else:
            # Make our diff
            diffs = dmp.diff_main(last[0], self.content)
            # User our custom prettyHtml function
            diff = diff_prettyHtml(dmp, diffs)

        # rpush the current content onto raw
        redisDB.rpush('Forum:History:Topic:%s:Raw' % self.raw_id, self.content)
        # add the diff to our ranked history
        redisDB.zadd('Forum:History:Topic:%s' % self.raw_id, diff, to_timestamp(self.updated_at))

    @property
    def history_count(self):
        return redisDB.zcount('Forum:History:Topic:%s' % self.raw_id, '-inf', '+inf')

    @property
    def history(self):
        return [Version(*t) for t in redisDB.zrange('Forum:History:Topic:%s' % self.raw_id, 0, -1, withscores=True)]

    def update_paging(self):
        redisDB.zadd('Forum:Paging:Topics', self.raw_id, to_timestamp(self.updated_at))

    def save_tags(self, tags):
        if not self.raw_id:
            raise BaseException("Topic must have an ID before saving tags")

        key = 'Forum:Tags:Topic:%s' % self.raw_id

        # Strip whitespace and `#` and make lowercase
        tagstrip = lambda tag: tag.strip(' #').lower()
        tags = [tagstrip(tag) for tag in tags if tagstrip(tag)]
        # Find which tags we're not using anymore
        torem = [tag for tag in redisDB.smembers(key) if tag not in tags]

        p = redisDB.pipeline()

        # Add our Topic id to each tags set
        [p.sadd('Forum:Tag:%s:Topics' % tag, self.raw_id) for tag in tags]
        # Remove the tags we're not using anymore
        [p.srem('Forum:Tag:%s:Topics' % tag, self.raw_id) for tag in torem]

        # Add to our Topics tags the new keys
        p.sadd(key, *tags)
        # And remove the old ones
        [p.srem(key, tag) for tag in torem]

        # Update our global tags
        p.sadd('Forum:Tags:All', *tags)

        p.execute()

    @property
    def tags(self):
        return sorted(redisDB.smembers('Forum:Tags:Topic:%s' % self.raw_id))

    @property
    def tag_objects(self):
        return [Tag(name).load() for name in self.tags]

    def add_to_unread_queues(self):
        '''
        Add this Topic to each users unread queue
        '''
        users = redisDB.smembers('Forum:Users:All')
        [redisDB.srem('Forum:User:%s:HasRead' % pk, self.raw_id) for pk in users]

    @property
    def unread(self):
        '''
        Returns True if the current user hasn't read this Topic
        '''
        user = currentUser()
        return not redisDB.sismember('Forum:User:%s:HasRead' % user.raw_id, self.raw_id)


### Signals ###

def redis_updates_for_user(sender, document, **kwargs):
    document.storeInRedis()

signals.post_save.connect(redis_updates_for_user, sender=User)

def update_updated_at(sender, document, **kwargs):
    document.updated_at = datetime.datetime.now()

signals.pre_save.connect(update_updated_at, sender=Topic)

def redis_updates_for_topic(sender, document, **kwargs):
    document.update_history()
    document.add_to_unread_queues()

signals.post_save.connect(redis_updates_for_topic, sender=Topic)
