from email.policy import default
from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(150))
    username = db.Column(db.String(150), unique=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(150))
    publishdate = db.Column(db.DateTime(timezone=True), default=func.now())
    repost = db.Column(db.Boolean, default=False, nullable=False)
    cycle = db.Column(db.Boolean, default=False, nullable=False)
    cycledate = db.Column(db.DateTime(timezone=True), default=func.now())
    containsimages = db.Column(db.Boolean, default=False, nullable=False)
    fortumblr = db.Column(db.Boolean, default=True, nullable=False)
    forbluesky = db.Column(db.Boolean, default=True, nullable=False)
    tumblrtags = db.Column(db.JSON, nullable=True)
    blogname = db.Column(db.String(150), default="")

class Tumblrblock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    order = db.Column(db.Integer, default=0)
    blocktype = db.Column(db.String(32), default="")
    imageids = db.Column(db.JSON)
    url = db.Column(db.String(256), default="")
    embed = db.Column(db.String(512), default="")
    quillops = db.Column(db.JSON)
    npf = db.Column(db.JSON)
    reblogid = db.Column(db.String(512), default="")

class Blueskyskeet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    order = db.Column(db.Integer, default=0)
    imageids = db.Column(db.JSON)
    text = db.Column(db.String(512))
    quillops = db.Column(db.JSON)
    urls = db.Column(db.JSON)
    mentions = db.Column(db.JSON)
    tags = db.Column(db.JSON)
    cid = db.Column(db.String(256), default="")
    uri = db.Column(db.String(256), default="")
    parenturi = db.Column(db.String(256), default="")
    parentcid = db.Column(db.String(256), default="")

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    url = db.Column(db.String(256), nullable=False)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    mimetype = db.Column(db.String(128))
    order = db.Column(db.Integer)
    ready = db.Column(db.Boolean, default=False, nullable=False)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(300))
    tagtype = db.Column(db.String(32))
    count = db.Column(db.Integer, default=1)
    date = db.Column(db.DateTime(timezone=True), default=func.now())

class Postjob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    title = db.Column(db.String(150))
    publishdate = db.Column(db.DateTime(timezone=True), default=func.now())
    repost = db.Column(db.Boolean, default=False, nullable=False)
    published = db.Column(db.Boolean, default=False, nullable=False)

class Watcher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    wtype = db.Column(db.String(32))
    url = db.Column(db.String(256))
    searchkeys = db.Column(db.JSON, nullable=True)
    titleprefix = db.Column(db.String(100))
    posttext = db.Column(db.String(100))
    titlekey = db.Column(db.String(100))
    updatekey = db.Column(db.String(100))
    lastupdate = db.Column(db.String(150))
    slugkey = db.Column(db.String(100))
    archival = db.Column(db.Boolean, default=False, nullable=False)
    pagesperupdate = db.Column(db.Integer, default=0)
    nextkey = db.Column(db.String(100))
    prevkey = db.Column(db.String(100))
    postcheckmarks = db.Column(db.JSON, nullable=True)
    bstags = db.Column(db.String(100))
    tbtags = db.Column(db.String(150))
    blogname = db.Column(db.String(150), default="")
    cycledelta = db.Column(db.JSON, nullable=True)
    scheduledata = db.Column(db.JSON, nullable=True)
    lastran = db.Column(db.DateTime(timezone=True), default=func.now())
    status = db.Column(db.String(32))
    running = db.Column(db.Boolean, default=True, nullable=False)
