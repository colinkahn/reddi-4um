import redisco
from redisco import models

redisco.connection_setup()

class User(models.Model):
    name = models.Attribute()
    email = models.Attribute(required=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def username(self):
        return self.name or 'anon'

class Post(models.Model):
    title = models.Attribute(required=True)
    content = models.Attribute(required=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ReferenceField(User, required=True)

class Comment(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ReferenceField(User, required=True)
    post = models.ReferenceField(Post, required=True)
