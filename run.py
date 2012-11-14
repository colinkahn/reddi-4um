import simplejson as json
import time
import bleach
import os

from httplib2 import Http
from urllib import urlencode

import settings

from helper import *

from flask import (Flask, jsonify, redirect,
                   render_template, request, session, url_for)

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

from forum import Forum, Topic, Comment, User

f = Forum()

currentUser = lambda: User(session['user_id'])


@app.template_filter('date')
def datetimeformat(value, format='%H:%M / %d-%m-%Y'):
    return value.strftime(format)

@app.route("/")
def main():
    pager = f.getTopicsPager()
    topics = f.getTopicsByModified(pager['page'], settings.TOPICS_PER_PAGE)
    return render_template('index.html', topics=topics, pager=pager)


@app.route('/set_email', methods=['POST'])
def set_email():
    """Verify via BrowserID and upon success, set
    the email for the user unless it already
    exists and return the token.
    """
    bid_fields = {'assertion':request.form['bid_assertion'],
                  'audience':settings.DOMAIN}
    headers = {'Content-type':'application/x-www-form-urlencoded'}
    h.disable_ssl_certificate_validation=True
    resp, content = h.request('https://browserid.org/verify',
                              'POST',
                              body=urlencode(bid_fields),
                              headers=headers)
    bid_data = json.loads(content)
    if bid_data['status'] == 'okay' and bid_data['email']:
        user = f.userFromBidOrNew(bid_data['email'])
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

    if not title or not content:
        return render_template('new_topic.html', title=title, content=content, topic_error=True)
    else:
        # Get a new topic object
        topic = f.newTopic()
        # Set its title and content
        topic.title = title
        topic.content = content
        # Set it as just modified
        f.setTopicAsModified(topic)
        # Get the current user
        user = currentUser()
        # Add the topic to that users topics
        user.addTopic(topic)

        return redirect(url_for('view_topic', id=topic.id))


@app.route("/topic/<int:id>/")
@authenticated
def view_topic(id):
    topic = Topic(id)
    comments = topic.comments
    return render_template('topic.html', topic=topic, comments=comments)


@app.route("/topic/<int:id>/", methods=['POST'])
@authenticated
def comment_on_topic(id):
    topic = Topic(id)
    content = request.form['content']

    if not content:
        comments = topic.comments
        return render_template('topic.html', topic=topic, comments=comments, comment_error=True)
    else:
        # Get a new comment object
        comment = f.newComment()
        # Set it's content
        comment.content = content
        # Add the comment to this topic
        topic.addComment(comment)
        # Set topic as just modified
        f.setTopicAsModified(topic)
        # Get the current user
        user = currentUser()
        # Add the comment to that users comments
        user.addComment(comment)

        return redirect(url_for('view_topic', id=topic.id))


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
    return render_template('profile.html', user=user)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
