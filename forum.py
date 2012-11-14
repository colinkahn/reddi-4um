import settings
import datetime
from helper import clean, get_page

db = settings.DATABASE

class DateMixin:
    @property
    def created_at(self):
        created_at = db.get('%(type)s:%(id)s:created_at' % self)
        return self._as_date(created_at)

    @created_at.setter
    def created_at(self, value):
        db.set('%(type)s:%(id)s:created_at' % self, str(value))

    @property
    def modified_at(self):
        modified_at = db.get('%(type)s:%(id)s:modified_at' % self)
        return self._as_date(modified_at)

    @modified_at.setter
    def modified_at(self, value):
        db.set('%(type)s:%(id)s:modified_at' % self, str(value))

    def _as_date(self, value):
        try:
            return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            return datetime.datetime.now()


class Comment(object, DateMixin):
    def __init__(self, id):
        self.id = id
        self.type = 'comment'

    @property
    @clean
    def content(self):
        return db.get('comment:%s:content' % self.id)

    @content.setter
    def content(self, value):
        db.set('comment:%s:content' % self.id, value)

    @property
    def user(self):
        id = db.get('comment:%s:user' % self.id)
        return User(id)


class Topic(object, DateMixin):
    def __init__(self, id):
        self.id = id
        self.type = 'topic'

    @property
    @clean
    def title(self):
        return db.get('topic:%s:title' % self.id)

    @title.setter
    def title(self, value):
        db.set('topic:%s:title' % self.id, value)

    @property
    @clean
    def content(self):
        return db.get('topic:%s:content' % self.id)

    @content.setter
    def content(self, value):
        db.set('topic:%s:content' % self.id, value)

    @property
    def comments(self):
        ids = db.lrange('topic:%s:comments' % self.id, 0, -1)
        return [Comment(id) for id in ids]

    def addComment(self, comment):
        db.rpush('topic:%s:comments' % self.id, comment.id)
        db.set('comment:%s:topic' % comment.id, self.id)

    @property
    def user(self):
        id = db.get('topic:%s:user' % self.id)
        return User(id)


class User(object):
    def __init__(self, id):
        self.id = id
        self.type = 'user'

    @property
    @clean
    def name(self):
        return db.get('user:%s:name' % self.id) or 'anon'

    @name.setter
    def name(self, value):
        db.set('user:%s:name' % self.id, value)

    @property
    def email(self):
        return db.get('user:%s:email' % self.id)

    @name.setter
    def email(self, value):
        db.set('user:%s:id' % value, self.id)
        db.set('user:%s:email' % self.id, value)

    def addTopic(self, topic):
        db.sadd('user:%s:topics' % self.id, topic.id)
        db.set('topic:%s:user' % topic.id, self.id)

    def addComment(self, comment):
        db.sadd('user:%s:comments' % self.id, comment.id)
        db.set('comment:%s:user' % comment.id, self.id)


class Forum(object):
    def __init__(self):
        pass

    def userFromBidOrNew(self, email):
        id = db.get('user:%s:id' % email)
        user = id and User(id) or self.newUser()
        user.email = email
        return user

    def newUser(self):
        id = db.incr('userUID')
        db.sadd('users', id)
        return User(id)

    def newTopic(self):
        id = db.incr('topicUID')
        db.sadd('topics', id)
        return Topic(id)

    def newComment(self):
        id = db.incr('commentUID')
        db.sadd('comments', id)
        return Comment(id)

    def getTopics(self):
        return [Topic(id) for id in sorted(db.smembers('topics'))]

    def getTopicsLength(self):
        return db.llen('sorted:topic:modified')

    def setTopicAsModified(self, topic):
        # Remove it from where it was
        db.lrem('sorted:topic:modified', topic.id)
        # Add it back to the end
        db.lpush('sorted:topic:modified', topic.id)

    def getTopicsByModified(self, page, per_page):
        start = (page - 1) * per_page
        end = (start - 1) + per_page
        return [Topic(id) for id in db.lrange('sorted:topic:modified', start, end)]

    def getTopicsPager(self):
        pages = self.getTopicsLength()/settings.TOPICS_PER_PAGE
        page = get_page(pages)
        return {'page':page, 'pages':pages}
