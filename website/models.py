from email.policy import default
from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(150))
    username = db.Column(db.String(150))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(150))
    publishdate = db.Column(db.DateTime(timezone=True), default=func.now())
    repost = db.Column(db.Boolean, default=False, nullable=False)
    cycle = db.Column(db.Boolean, default=False, nullable=False)
    containsimages = db.Column(db.Boolean, default=False, nullable=False)
    fortumblr = db.Column(db.Boolean, default=True, nullable=False)
    forbluesky = db.Column(db.Boolean, default=True, nullable=False)
    tagids = db.Column(db.JSON)

class Tumblrblock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    order = db.Column(db.Integer, default=0)
    blocktype = db.Column(db.String(32))
    imageids = db.Column(db.JSON)
    text = db.Column(db.String(1024))
    url = db.Column(db.String(256))
    blogname = db.Column(db.String(150))
    embed = db.Column(db.String(512))
    content = db.Column(db.JSON)
    reblogid = db.Column(db.String(512))

class Blueskyskeet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    order = db.Column(db.Integer, default=0)
    imageids = db.Column(db.JSON)
    text = db.Column(db.String(512))
    skeet = db.Column(db.JSON)
    cid = db.Column(db.String(256))
    uri = db.Column(db.String(256))
    cid = db.Column(db.String(256))
    parenturi = db.Column(db.String(256))
    parentcid = db.Column(db.String(256))

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    url = db.Column(db.String(256), nullable=False)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    aspectratio = db.Column(db.String(32))
    mimetype = db.Column(db.String(128))
    ready = db.Column(db.Boolean, default=False, nullable=False)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(300))
    tagtype = db.Column(db.String(32))
    count = db.Column(db.Integer, default=1)

class Postjob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    title = db.Column(db.String(150))
    publishdate = db.Column(db.DateTime(timezone=True), default=func.now())
    repost = db.Column(db.Boolean, default=False, nullable=False)
    published = db.Column(db.Boolean, default=False, nullable=False)

class Watcher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    url = db.Column(db.String(256))
    lastran = db.Column(db.DateTime(timezone=True), default=func.now())
    status = db.Column(db.String(32))
    script = db.Column(db.String(32))
    running = db.Column(db.Boolean, default=True, nullable=False)
