import settings
from models import User, Topic, Comment

class Forum(object):
    def __init__(self):
        pass

    def getTopicsLength(self):
        return db.llen('sorted:topic:modified')

    def getTopicsByModified(self, page, per_page):
        start = (page - 1) * per_page
        end = (start - 1) + per_page
        return [Topic(id) for id in db.lrange('sorted:topic:modified', start, end)]

    def getTopicsPager(self):
        topics = Topic.objects.all().order('updated_at')
        pages = len(topics)/settings.TOPICS_PER_PAGE
        page = get_page(pages)
        return {'page':page, 'pages':pages}
