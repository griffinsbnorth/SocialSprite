from flask import Blueprint, render_template, request, current_app, flash, jsonify, send_file
from flask_login import login_required, current_user
from .models import Post, Blueskyskeet, Tumblrblock, Tag, Postjob
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
        'files': [],
        'skeets': [],
        'bsimgmap': {},
        'blocks': [],
        'tbimgmap': {},
        'blogname': '',
        'tags': '',
        'toptbtags': gettoptags('tumblr'),
        'topbstags': gettoptags('bluesky')
        }

    if request.method == 'POST':
        data = request.form
        files = request.files
        postprocessor = Processpost()
        postprocessor.processform(data, files, current_user.id)
        if postprocessor.success:
            flash(postprocessor.message, category='success')
        else:
            flash(postprocessor.message, category='error')

    return render_template("addpost.html", user=current_user, postdata=postdata, postop='ADD')

@views.route('/editpost/<int:postid>', methods=['GET', 'POST'])
def editpost(postid):
    if request.method == 'POST':
        data = request.form
        files = request.files
        postprocessor = Processpost(postid)
        postprocessor.processform(data, files, current_user.id)
        if postprocessor.success:
            flash(postprocessor.message, category='success')
        else:
            flash(postprocessor.message, category='error')

    editpost = Post.query.get(postid)
    scheduledatetime = editpost.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
    cycledatetime = editpost.cycledate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
    skeetsdata = getskeets(postid)
    tumblrdata = gettumblrblocks(postid)

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
        'files': getimagefiles(postid),
        'skeets': skeetsdata['skeets'],
        'bsimgmap': skeetsdata['bsimgmap'],
        'blocks': tumblrdata['blocks'],
        'tbimgmap': tumblrdata['tbimgmap'],
        'blogname': editpost.blogname,
        'tags': ','.join(editpost.tumblrtags),
        'toptbtags': gettoptags('tumblr'),
        'topbstags': gettoptags('bluesky')
        }

    return render_template("addpost.html", user=current_user, postdata=postdata, postop='EDIT')

@views.route('/posts')
@login_required
def posts():
    currentpage = request.args.get('page', 1, type=int)
    pagination = Post.query.filter(Post.user_id == current_user.id).order_by(Post.publishdate).paginate(page=currentpage, per_page=15)
    for item in pagination.items:
        item.publishdate = item.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
        item.cycledate = item.cycledate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))

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
    currentpage = request.args.get('page', 1, type=int)
    pagination = Postjob.query.filter(Postjob.user_id == current_user.id).order_by(Postjob.publishdate).paginate(page=currentpage, per_page=15)
    for item in pagination.items:
        item.publishdate = item.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))

    return render_template("queue.html", user=current_user, pagination=pagination)

@views.route('/deletepost', methods=['POST'])
def delete_post():  
    post = json.loads(request.data)
    postid = post['postid']
    post = Post.query.get(postid)
    postprocessor = Processpost(postid)
    if post:
        if post.user_id == current_user.id:
            for ttag in post.tumblrtags:
                dbtag = Tag.query.filter(Tag.tag == ttag, Tag.tagtype == 'tumblr').first()
                if dbtag:
                    dbtag.count -= 1
                    if dbtag.count == 0:
                        db.session.delete(dbtag)

            db.session.delete(post)
            db.session.commit()
            #delete images associated with post
            pastimagefiles = DBImage.query.filter(DBImage.post_id == postid).all()
            for pastimage in pastimagefiles:
                     postprocessor.delete_image(pastimage)
            #delete skeets associated with post
            dbskeets = Blueskyskeet.query.filter(Blueskyskeet.post_id == postid)
            for dbskeet in dbskeets:
                for bstag in dbskeet.tags:
                    dbtag = Tag.query.filter(Tag.tag == bstag['tag'], Tag.tagtype == 'bluesky').first()
                    if dbtag:
                        dbtag.count -= 1
                        if dbtag.count == 0:
                            db.session.delete(dbtag)
                            db.session.commit()

            Blueskyskeet.query.filter(Blueskyskeet.post_id == postid).delete()
            #delete tumblr blocks associated with post
            Tumblrblock.query.filter(Tumblrblock.post_id == postid).delete()
            #delete unpublished postjobs
            Postjob.query.filter(Postjob.post_id == postid, Postjob.published == False).delete()
            db.session.commit()

    return jsonify({})

@views.route('/editrepost', methods=['POST'])
def edit_repost():  
    post = json.loads(request.data)
    postid = post['postid']
    repost = post['repost']
    post = Post.query.get(postid)
    if post:
        if post.user_id == current_user.id:
            post.repost = repost
            db.session.commit()

    return jsonify({})

@views.route('/editcycle', methods=['POST'])
def edit_cycle():  
    post = json.loads(request.data)
    postid = post['postid']
    cycle = post['cycle']
    post = Post.query.get(postid)
    if post:
        if post.user_id == current_user.id:
            post.cycle = cycle
            db.session.commit()

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

def getskeets(postid):
    skeets = Blueskyskeet.query.filter(Blueskyskeet.post_id == postid).order_by(Blueskyskeet.order).all()
    skeetsdata = []
    bsimages = {}
    selectorindex = 0
    selectorindexend = 4
    for skeet in skeets:
        
        for imageid in skeet.imageids:
            imagefile = DBImage.query.get(imageid)
            if imagefile:
                bsimages[selectorindex] = imagefile.url
            selectorindex += 1

        selectorindex = selectorindexend
        selectorindexend += 4
        skeetsdata.append(skeet.quillops)

    return {'skeets': skeetsdata, 'bsimgmap': bsimages}

def gettumblrblocks(postid):
    blocks = Tumblrblock.query.filter(Tumblrblock.post_id == postid).order_by(Tumblrblock.order).all()
    tumblrdata = []
    tbimages = {}
    for block in blocks:
        imagelist = []
        for imageid in block.imageids:
            imagefile = DBImage.query.get(imageid)
            if imagefile:
                imagelist.append(imagefile.url)
        if imagelist:
            tbimages[str(block.order)] = imagelist

        blockdata = {'blocktype': block.blocktype, 'text': block.quillops, 'url': block.url, 'embed': block.embed}
        tumblrdata.append(blockdata)

    return {'blocks': tumblrdata, 'tbimgmap': tbimages}

def gettoptags(tagtype):
    toptags = Tag.query.filter(Tag.tagtype == tagtype).order_by(Tag.count.desc()).limit(10).all()
    toptaglist = []
    for toptag in toptags:
        toptaglist.append(toptag.tag)
    return toptaglist



