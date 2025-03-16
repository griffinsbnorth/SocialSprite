from flask import Blueprint, render_template, request, current_app, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import Image as DBImage
from .models import Post
from PIL import Image as PILImage
from config import Config
from .validate import validatetextfield
import os
from atproto import models
from resizeimage import resizeimage
import datetime
from zoneinfo import ZoneInfo
from . import db
import json

views = Blueprint('views', __name__)
FILE_SIZE_LIMIT = 1000000

@views.route('/')
@login_required
def home():
    return render_template("home.html", user=current_user)

@views.route('/addpost', methods=['GET', 'POST'])
@login_required
def addpost():
    if request.method == 'POST':
        data = request.form
        print(data)

        title = request.form.get('title')
        scheduledate = request.form.get('scheduledate')
        cycledate = request.form.get('cycledate')
        time = request.form.get('time')
        if (time == ''):
            time = '00:00'

        validtitle = validatetextfield('Title', title, 150)
        validscheduledate = True
        validcycledate = True
        publishdatetime = datetime.datetime.now()
        cycledatetime = datetime.datetime.now()

        #create dates
        try:
            publishdatetime = datetime.datetime.strptime(scheduledate + "T" + time, "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo(Config.TIMEZONE))
            validscheduledate = bool(publishdatetime)
        except ValueError:
            validscheduledate = False
                
        try:
            cycledatetime = datetime.datetime.strptime(cycledate, "%Y-%m-%d").replace(tzinfo=ZoneInfo(Config.TIMEZONE))
            validcycledate = bool(cycledatetime)
        except ValueError:
            validcycledate = False

        if not validtitle['status']:
            flash(validtitle['message'], category='error')
        elif scheduledate == '':
            flash('Missing schedule date.', category='error')
        elif cycledate == '':
            flash('Missing cycle date.', category='error')
        elif not validscheduledate:
            flash('Invalid schedule date.', category='error')
        elif not validcycledate:
            flash('Invalid cycle date.', category='error')
        else:
            repost = request.form.get('repost') != None
            cycle = request.form.get('cycle') != None
            images = request.form.get('images') != None
            imagefiles = request.files.getlist('imgupload')
            tumblr = request.form.get('tumblr') != None
            tumblrblocklist = request.form.getlist('tbtype')
            bluesky = request.form.get('bluesky') != None

            if images and not imagefiles:
                flash('No attached images for image post.', category='error')
            elif tumblr and not tumblrblocklist:
                flash('Tumblr post has no blocks', category='error')
            else:
                processedimagefiles = []

                dbpost = Post(user_id=current_user.id, title=title, publishdate=publishdatetime.astimezone(ZoneInfo("UTC")), repost=repost, cycle=cycle, cycledate=cycledatetime.astimezone(ZoneInfo("UTC")), containsimages=images, fortumblr=tumblr, forbluesky=bluesky, tagids=[])
                db.session.add(dbpost)
                db.session.commit()

                #Prep images for post (if there's images)
                if images:
                    processedimagefiles = processimages(imagefiles,dbpost.id)

                #Prep Tumblr post blocks

                #Prep BlueSky skeets


    return render_template("addpost.html", user=current_user)

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

def processimages(imagefiles,postid):
    validimagefile = True
    processedimagefiles = []
    for imagefile in imagefiles:
        validimagefile = validimagefile and allowed_file(imagefile.filename)

    if validimagefile:
        for imgfile in imagefiles:
            sfilename = secure_filename(imgfile.filename)
            imgpath = os.path.join(Config.UPLOAD_FOLDER, sfilename)
            imgfile.save(imgpath)
            #resize image if needed
            im = PILImage.open(imgpath)
            imgsize = os.stat(imgpath).st_size
            scale = 1.0
            while imgsize > FILE_SIZE_LIMIT:
                if (scale < 1.0):
                    newheight = int(float(im.height) * scale)
                    im = resizeimage.resize_height(im, newheight)
                else:
                    im = im.resize(im.size,PILImage.NEAREST)
                im.save(imgpath)
                im = PILImage.open(imgpath)
                imgsize = os.stat(imgpath).st_size
                scale = scale - 0.1
            
            processed = True
            #get watermark

            #add to list of Image objects
            dbimg = DBImage(post_id=postid,url=sfilename, width=im.width, height=im.height,mimetype=imgfile.mimetype, ready=processed)
            processedimagefiles.append(dbimg)
    return processedimagefiles

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

@views.route('/deletepost', methods=['POST'])
def delete_post():  
    post = json.loads(request.data)
    postid = post['postid']
    post = Post.query.get(postid)
    if post:
        if post.user_id == current_user.id:
            db.session.delete(post)
            db.session.commit()

    return jsonify({})