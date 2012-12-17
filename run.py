import simplejson as json
import bleach
import os
import browserid
import datetime

from httplib2 import Http
from urllib import urlencode

import settings

from helper import *

from flask import (Flask, jsonify, redirect,
                   render_template, request, session, url_for, abort)

from flask.ext.gravatar import Gravatar

app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = settings.SESSION_SECRET

h = Http()

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False)

from models import User, Topic, Comment, Tag, all_tags, currentUser
from pagination import Pagination


### Template Stuff ###

@app.template_filter('date')
def datetimeformat(value, format='%H:%M / %d-%m-%Y'):
    return value.strftime(format)

def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

app.jinja_env.globals['url_for_other_page'] = url_for_other_page


### Our Routes ###

def page_start_end(page):
    start = settings.PER_PAGE * (page-1)
    end = start + settings.PER_PAGE
    return (start,end)

@app.route("/", defaults={'page':1})
@app.route("/page/<int:page>")
def main(page):
    count = Topic.objects.count()
    start,end = page_start_end(page)
    topics = Topic.objects[start:end]
    if not topics and page != 1:
        abort(404)
    pagination = Pagination(page, settings.PER_PAGE, count)
    return render_template('index.html', topics=topics, pagination=pagination)


@app.route('/set_email', methods=['POST'])
def set_email():
    """Verify via BrowserID and upon success, set
    the email for the user unless it already
    exists and return the token.
    """
    bid_data = browserid.verify(request.form['bid_assertion'])

    if bid_data['status'] == 'okay' and bid_data['email']:
        user, created = User.objects.get_or_create(email=bid_data['email'])
        created and user.save()

        session['user_id'] = user.id
        session['user_email'] = user.email

    return redirect(url_for('main'))


@app.route('/logout', methods=['GET'])
def logout():
    """Log the user out"""
    session['user_id'] = None
    session['user_email'] = None
    return redirect(url_for('main'))


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html')


@app.errorhandler(500)
def something_broke(error):
    return render_template('500.html')


@app.route("/topic/new/")
@authenticated
def new_topic_form():
    return render_template('new_topic.html')


@app.route("/topic/new/", methods=['POST'])
@authenticated
def new_topic_submit():
    title = request.form['title']
    content = request.form['content']
    tags = request.form['tags']

    if not title or not content:
        return render_template('new_topic.html', title=title, content=content, tags=tags, topic_error=True)
    else:
        topic = Topic(title=title, content=content, user=currentUser())
        topic.save()
        # Post-save add our tags
        topic.save_tags(tags.split(','))

        return redirect(url_for('view_topic', pk=topic.raw_id))


@app.route("/topic/<pk>/edit/")
@authenticated
def edit_topic_form(pk):
    topic = Topic.objects.with_id(pk)

    if topic.user != currentUser():
        abort(401)

    return render_template('edit_topic.html', topic=topic)


@app.route("/topic/<pk>/edit/", methods=['POST'])
@authenticated
def edit_topic_submit(pk):
    topic = Topic.objects.with_id(pk)

    if topic.user != currentUser():
        abort(401)

    topic.title = request.form['title']
    topic.content = request.form['content']
    tags = request.form['tags']

    if not topic.title or not topic.content:
        return render_template('edit_topic.html', title=topic.title, content=topic.content, tags=tags, topic_error=True)
    else:
        topic.save()
        topic.save_tags(tags.split(','))

        return redirect(url_for('view_topic', pk=topic.id))


@app.route("/topic/<pk>/")
@authenticated
def view_topic(pk):
    topic = Topic.objects.with_id(pk)
    user = currentUser()
    user.readTopic(topic)
    return render_template('topic.html', topic=topic)


@app.route("/topic/<pk>/history")
@authenticated
def view_topic_history(pk):
    topic = Topic.objects.with_id(pk)
    return render_template('topic_history.html', topic=topic)


@app.route("/topic/<id>/", methods=['POST'])
@authenticated
def comment_on_topic(id):
    topic = Topic.objects.with_id(id)
    content = request.form['content']

    if not content:
        return render_template('topic.html', topic=topic, comment_error=True)
    else:
        comment = Comment(content=content, user=currentUser())
        topic.comments.append(comment)
        topic.save()
        return redirect(url_for('view_topic', pk=topic.raw_id))


@app.route("/tags/")
@authenticated
def view_tags():
    return render_template('tags.html', tags=all_tags())


@app.route("/tags/<tags>", defaults={'page':1})
@app.route("/tags/<tags>/page/<int:page>")
@authenticated
def view_topics_with_tags(tags, page):
    tags = [Tag(tag).load() for tag in tags.split('+') if tag]
    tag_keys = ['Forum:Tag:%s:Topics' % tag.name for tag in tags]
    topic_ids = settings.DATABASE.sinter(tag_keys)
    count = len(topic_ids)
    start,end = page_start_end(page)
    topics = Topic.objects.filter(pk__in=topic_ids)[start:end]
    if not topics and page != 1:
        abort(404)
    pagination = Pagination(page, settings.PER_PAGE, count)
    return render_template('topics_with_tags.html', tags=tags, topics=topics, pagination=pagination)



@app.route("/profile/")
@authenticated
def edit_profile():
    user = currentUser()
    return render_template('profile.html', user=user)


@app.route("/profile/", methods=['POST'])
@authenticated
def update_profile():
    user = currentUser()
    user.name = request.form['username']
    user.save()
    return render_template('profile.html', user=user)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
