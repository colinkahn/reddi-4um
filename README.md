Reddi-4um
===========

A simple forum written with Flask using Redis.

### Example

A working version hosted up on Heroku [here](http://reddi-4um.herokuapp.com/).

### ToDo

Add a bunch of features to make this more like a 'real' forum

* Ranking for comments (redis / ajax)
* Ranking for topics (redis)
* Paging for topics and comments
* **(Check!)** Tagging for Topics (mongo? redis?)
* Categories for Topics (redis)
* **(Check!)** Unread Message Tracking
* **(Check!)** msg-history -- When message are modified, everyone can see the change history. (Redis)

[Django Forum Apps Comparison](https://code.djangoproject.com/wiki/ForumAppsComparison)


### Tagging

#### In Redis

	\# set of all tags
	db.zadd('Forum:Tags', tag, #of)
	\# set of tags for each topic
	db.sadd('Forum:Topic:%s' % pk, tag)

##### Advantages

* Sets! score == popularity

#### In Mongo

	\# as a ListField
	tags = ListField(StringField(max_length=30))
	\# added directly to a topic
	topic.append(tag)

##### Advantages

* Simplicity! Add directly to a model


### Message History

	db.zadd('Forum:History:Topic:<id>', <content>, <timestamp> (or) <version>)


### Unread Message Tracking ###

* Each user has an unread message queue (redis list of post ids)
* When a user goes to a page that post is removed from the queue


---

Store all topics in Redis in sorted set using timestamp updated for ranking

for gettings pagination / tags 

get intersection for tags returning topic ids then get those ids from the total sorted set of topics
