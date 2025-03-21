from flask import Blueprint, render_template, request, current_app, flash, jsonify, send_file
from flask_login import login_required, current_user
from .models import Post
from .models import Image as DBImage
from config import Config
from .processpost import Processpost
import os
import datetime
from zoneinfo import ZoneInfo
from . import db
import json

views = Blueprint('views', __name__)

@views.route('/')
@login_required
def home():
    return render_template("home.html", user=current_user)

@views.route('/addpost', methods=['GET', 'POST'])
@login_required
def addpost():
    postdata = {
        'id': -1,
        'title': '', 
        'scheduledate': '', 
        'cycledate': '',
        'time': '00:00',
        'repost': True,
        'cycle': True,
        'images': True,
        'tumblr': True,
        'bluesky': True,
        'files': []
        }

    if request.method == 'POST':
        data = request.form
        files = request.files
        postprocessor = Processpost()
        postprocessor.processform(data, files, current_user.id)

    return render_template("addpost.html", user=current_user, postdata=postdata, postop='ADD')

@views.route('/editpost/<int:postid>', methods=['GET', 'POST'])
def editpost(postid):
    editpost = Post.query.get(postid)
    scheduledatetime = editpost.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
    cycledatetime = editpost.cycledate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))

    if request.method == 'POST':
        data = request.form
        files = request.files
        postprocessor = Processpost(postid)
        postprocessor.processform(data, files, current_user.id)

    postdata = {
        'id': postid,
        'title': editpost.title, 
        'scheduledate': scheduledatetime.strftime('%Y-%m-%d'), 
        'cycledate': cycledatetime.strftime('%Y-%m-%d'),
        'time': scheduledatetime.strftime('%H:%M'),
        'repost': editpost.repost,
        'cycle': editpost.cycle,
        'images': editpost.containsimages,
        'tumblr': editpost.fortumblr,
        'bluesky': editpost.forbluesky,
        'files': getimagefiles(postid)
        }

    return render_template("addpost.html", user=current_user, postdata=postdata, postop='EDIT')

@views.route('/posts')
@login_required
def posts():
    currentpage = request.args.get('page', 1, type=int)
    pagination = Post.query.filter(Post.user_id == current_user.id).order_by(Post.publishdate).paginate(page=currentpage, per_page=2)
    for item in pagination.items:
        item.publishdate = item.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))

    return render_template("posts.html", user=current_user, pagination=pagination)

@views.route('/watchers', methods=['GET', 'POST'])
@login_required
def watchers():
    if request.method == 'POST':
        data = request.files
        print(data)
    return render_template("watchers.html", user=current_user)

@views.route('/queue', methods=['GET', 'POST'])
@login_required
def queuepage():
    if request.method == 'POST':
        data = request.files
        print(data)
    return render_template("queue.html", user=current_user)

@views.route('/deletepost', methods=['POST'])
def delete_post():  
    post = json.loads(request.data)
    postid = post['postid']
    post = Post.query.get(postid)
    postprocessor = Processpost(postid)
    if post:
        if post.user_id == current_user.id:
            db.session.delete(post)
            db.session.commit()
            #delete images associated with post
            pastimagefiles = DBImage.query.filter(DBImage.post_id == postid).all()
            for pastimage in pastimagefiles:
                     postprocessor.delete_image(pastimage)

    return jsonify({})

@views.route('/loadfile', methods=['GET'])
def loadfile():
    source = request.args.get('source')
    filepath = Config.UPLOAD_FOLDER + '/' + source

    return send_file(filepath)

def getimagefiles(postid):
    imagefiles = DBImage.query.filter(DBImage.post_id == postid).order_by(DBImage.order).all()
    imagefilelist = []
    for imagefile in imagefiles:
        imagefilelist.append({'source': imagefile.url, 'options': {'type': 'local'}})

    return imagefilelist
