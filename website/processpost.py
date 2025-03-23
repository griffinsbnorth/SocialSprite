from flask import current_app
import os
from atproto import models
from resizeimage import resizeimage
import datetime
from zoneinfo import ZoneInfo
from . import db
import json
from PIL import Image as PILImage
from config import Config
from werkzeug.utils import secure_filename
from .models import Image as DBImage
from .models import Post

class Processpost():
    FILE_SIZE_LIMIT = 1000000

    def __init__(self, postid=-1):
        self.success = True
        self.message = ''
        self.postid = postid
        self.postdata = {}

    def __str__(self):
        return f"{self.message}"

    def validatetextfield(self, fieldname, text, maxlength, minlength = 0):
        message = ''
        status = True
        if len(text) <= minlength:
            message = fieldname + ' too short.'
            status = False
        elif len(text) > maxlength:
            message = fieldname + ' too long.'
            status = False

        return {'status': status,'message': message}

    def sanitize_input(self, user_input):
        return re.sub(r'[^\w\s]', '', user_input)  # Removes special characters

    def processform(self, data, files, userid):
        print(files)
        print(data)
        self.message = ''

        title = data.get('title')
        scheduledate = data.get('scheduledate')
        cycledate = data.get('cycledate')
        time = data.get('time')
        if (time == ''):
            time = '00:00'
        repost = data.get('repost') != None
        cycle = data.get('cycle') != None
        images = data.get('images') != None
        imagefiles = files.getlist('imgupload')
        fileorder = json.loads(str(data.get('fileorder')))
        watermarks = data.getlist('watermark')
        if watermarks == None:
            watermarks = []
        tumblr = data.get('tumblr') != None
        tumblrblocklist = data.getlist('tbtype')
        bluesky = data.get('bluesky') != None
        tags = ''
        if tumblr:
            tags = data.get('tags')
        tumblrhasimages = data.get('tbhasimages') != None
        blueskyhasimages = data.get('bshasimages') != None

        validtitle = self.validatetextfield('Title', title, 150)
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
            self.message += validtitle['message'] + '\n'
        elif scheduledate == '':
            self.message += 'Missing schedule date.' + '\n'
        elif cycledate == '':
            self.message += 'Missing cycle date.' + '\n'
        elif not validscheduledate:
            self.message += 'Invalid schedule date.' + '\n'
            scheduledate = ''
        elif not validcycledate:
            self.message += 'Invalid cycle date.' + '\n'
            cycledate = ''
        elif images and not fileorder:
            self.message += 'No attached images for image post.' + '\n'
        elif images and not tumblrhasimages and not blueskyhasimages:
            self.message += 'No selected images for image post.' + '\n'
        elif tumblr and not tumblrblocklist:
             self.message += 'Tumblr post has no blocks' + '\n'
        elif tumblr and tags == '':
             self.message += 'Tumblr post needs tags' + '\n'
        else:
             processedimagefiles = []
                
             dbpost = Post()
             if self.postid != -1:
                 dbpost = Post.query.get(self.postid)

             dbpost.user_id = userid
             dbpost.title = title
             dbpost.publishdate = publishdatetime.astimezone(ZoneInfo("UTC"))
             dbpost.repost = repost
             dbpost.cycle = cycle
             dbpost.cycledate = cycledatetime.astimezone(ZoneInfo("UTC"))
             dbpost.containsimages = images
             dbpost.fortumblr = tumblr
             dbpost.forbluesky = bluesky
             dbpost.tagids= []
             if self.postid == -1:
                 db.session.add(dbpost)

             db.session.commit()

             pastimagefiles = DBImage.query.filter(DBImage.post_id == dbpost.id).all()
             pastimagesfound = len(pastimagefiles) > 0
             #Prep images for post (if there's images)
             if images:
                 #Prep new images
                 processedimagefiles = self.processimages(imagefiles, dbpost.id, fileorder, watermarks)
                 #Prep past images
                 for pastimage in pastimagefiles:
                     neworder = fileorder.get(pastimage.url, None)
                     if neworder != None:
                         pastimage.order = neworder
                         pastimage.ready = pastimage.url not in watermarks
                     else:
                         self.delete_image(pastimage)
             else:
                 #delete any past associated images
                 for pastimage in pastimagefiles:
                     self.delete_image(pastimage)

             if pastimagesfound:
                 db.session.commit()

             #Prep Tumblr post blocks

             #Prep BlueSky skeets

        #set success flag
        self.success = (self.message == '')
        self.postdata = {
            'title': title, 
            'scheduledate': scheduledate, 
            'cycledate': cycledate,
            'time': time,
            'repost': repost,
            'cycle': cycle,
            'images': images,
            'tumblr': tumblr,
            'bluesky': bluesky
            }

    def processimages(self, imagefiles, postid, fileorder, watermarks):
        validimagefile = True
        processedimagefiles = []
        for imagefile in imagefiles:
            validimagefile = validimagefile and self.allowed_file(imagefile.filename)

        if validimagefile:
            for imgfile in imagefiles:
                sfilename = secure_filename(imgfile.filename)
                imgpath = os.path.join(Config.UPLOAD_FOLDER, sfilename)
                imgfile.save(imgpath)
                #resize image if needed
                im = PILImage.open(imgpath)
                imgsize = os.stat(imgpath).st_size
                scale = 1.0
                while imgsize > self.FILE_SIZE_LIMIT:
                    if (scale < 1.0):
                        newheight = int(float(im.height) * scale)
                        im = resizeimage.resize_height(im, newheight)
                    else:
                        im = im.resize(im.size,PILImage.NEAREST)
                    im.save(imgpath)
                    im = PILImage.open(imgpath)
                    imgsize = os.stat(imgpath).st_size
                    scale = scale - 0.1
            
                processed = imgfile.filename not in watermarks

                #add to list of Image objects
                index = fileorder[imgfile.filename]
                dbimg = DBImage(post_id=postid,url=sfilename, width=im.width, height=im.height,mimetype=imgfile.mimetype, order=index, ready=processed)
                processedimagefiles.append(dbimg)

            db.session.add_all(processedimagefiles)
            db.session.commit()
        else:
            self.message += 'Invalid image file(s)' + '\n'

        return processedimagefiles

    def allowed_file(self, filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

    def delete_image(self, imagefile):
        filename = imagefile.url
        db.session.delete(imagefile)

        duplicates = DBImage.query.filter(DBImage.url == filename).all()

        if not duplicates:
            filepath = Config.UPLOAD_FOLDER + '/' + filename
            if os.path.exists(filepath):
                os.remove(filepath)


