import io
from flask import current_app
import re
import os
from atproto import models
import requests
from resizeimage import resizeimage
import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

from website.deltatonpf import deltaToNpf
from website.sendpost import sendpostjob
from . import db, scheduler
import json
from PIL import Image as PILImage
from config import Config
from werkzeug.utils import secure_filename
from .models import Image as DBImage
from .models import Post, Blueskyskeet, Tumblrblock, Tag, Postjob
import ua_generator

class Processpost():
    FILE_SIZE_LIMIT = 1000000

    def __init__(self, postid=-1, watcher_request=False, session=db.session):
        self.success = True
        self.message = ''
        self.postid = postid
        self.watcher_request = watcher_request
        self.session = session
        self.title = ''

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

    def removejobs(self):
        if self.postid != -1:
            postjobs = Postjob.query.filter(Postjob.post_id == self.postid, Postjob.published == False)
            for postjob in postjobs:
                job = scheduler.get_job(str(postjob.id))
                if job:
                    scheduler.remove_job(str(postjob.id))

    def processform(self, data, files, userid):
        try:
            printdata = json.dumps(data, indent=4, sort_keys=True)
            current_app.logger.info('Post processing in progress.')
            current_app.logger.info(f'Post processing files: {files}')
            current_app.logger.info(f'Post processing data: {printdata}')
            self.message = ''

            title = data.get('title')
            scheduledate = data.get('scheduledate')
            cycleweeks = data.get('weeks')
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
            blogname = data.get('blogname')
            if blogname == '':
                blogname = os.getenv("BLOGNAME")
            bluesky = data.get('bluesky') != None
            bsskeetsnumber = int(data.get('bsskeetlen'))
            tags = ''
            if tumblr:
                tags = data.get('tags')
            tumblrhasimages = data.get('tbhasimages') != None
            blueskyhasimages = data.get('bshasimages') != None

            validtitle = self.validatetextfield('Title', title, 150)
            validscheduledate = True
            publishdatetime = datetime.datetime.now()

            #create dates
            try:
                publishdatetime = datetime.datetime.strptime(scheduledate + "T" + time, "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo(Config.TIMEZONE))
                validscheduledate = bool(publishdatetime)
            except ValueError:
                validscheduledate = False

            if not validtitle['status']:
                self.message += validtitle['message'] + '\n'
            elif scheduledate == '':
                self.message += 'Missing schedule date.' + '\n'
            elif cycleweeks == 0:
                self.message += 'Missing cycle data.' + '\n'
            elif not validscheduledate:
                self.message += 'Invalid schedule date.' + '\n'
                scheduledate = ''
            elif images and not fileorder:
                self.message += 'No attached images for image post.' + '\n'
            elif images and not tumblrhasimages and not blueskyhasimages:
                self.message += 'No selected images for image post.' + '\n'
            elif tumblr and not tumblrblocklist:
                 self.message += 'Tumblr post has no blocks' + '\n'
            elif tumblr and tags == '':
                 self.message += 'Tumblr post needs tags' + '\n'
            elif bluesky and not bsskeetsnumber:
                 self.message += 'BlueSky post has no skeets' + '\n'
            else:
                 processedimagefiles = []
                 self.title = title
                
                 dbpost = Post()
                 if self.postid != -1:
                     dbpost = Post.query.get(self.postid)

                 dbpost.user_id = userid
                 dbpost.title = title
                 dbpost.publishdate = publishdatetime.astimezone(ZoneInfo("UTC"))
                 dbpost.repost = repost
                 dbpost.cycle = cycle
                 dbpost.cycleweeks = cycleweeks
                 dbpost.containsimages = images
                 dbpost.fortumblr = tumblr
                 dbpost.forbluesky = bluesky
                 dbpost.tumblrtags= []
                 dbpost.blogname = blogname
                 if self.postid == -1:
                     self.session.add(dbpost)

                 self.session.flush()

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
                     self.session.flush()

                 finalimagefiles = DBImage.query.filter(DBImage.post_id == dbpost.id).order_by(DBImage.order).all()
             
                 #Prep Tumblr post blocks
                 if tumblr:
                     addtbimages = images and tumblrhasimages
                     deletetbresult = Tumblrblock.query.filter(Tumblrblock.post_id == dbpost.id, Tumblrblock.order > len(tumblrblocklist)).delete()
                     if deletetbresult > 0:
                         self.session.flush()

                     dbtblocks = []
                     tbindex = 1
                     for tumblrblock in tumblrblocklist:
                         tbdata = tumblrblock.split(':')
                         match tbdata[0]:
                            case 'photo':
                                 if addtbimages:
                                     tbimgs = data.getlist('imgcheckbox' + tbdata[1])
                                     dbtblock = self.process_image_tblock(finalimagefiles, tbimgs, dbpost.id, tbindex)
                                     dbtblocks.append(dbtblock)
                                     tbindex += 1
                            case 'text':
                                 textops = {}
                                 npf = {}
                                 try:
                                    textops = json.loads(str(data.get('tbtext' + tbdata[1])),strict=False)
                                 except Exception as e:
                                     current_app.logger.error(f"Process post tumblr text - Could not parse into json, tbtext{tbindex}: {str(data.get('tbtext' + tbdata[1]))}   {e}")
                                     textops = {}
                                     raise e
                                 try:
                                     npfstring = str(data.get('npf' + tbdata[1]))
                                     print(npfstring)
                                     npf = json.loads(npfstring,strict=False)
                                 except Exception as e:
                                     current_app.logger.error(f"Process post tumblr text - Could not parse npf into json, tbtext{tbindex}: {str(data.get('tbtext' + tbdata[1]))}   {e}")
                                     npf = {}
                                     raise e
                                 dbtblock = self.process_tblock(tbdata[0], textops, '', '', dbpost.id, tbindex, npf)
                                 dbtblocks.append(dbtblock)
                                 tbindex += 1
                            case _:
                                prefix = 'tb' + tbdata[0] + tbdata[1]
                                url = data.get(prefix + 'url')
                                embed = data.get(prefix + 'embed')
                                if embed == None:
                                    embed = ''
                                dbtblock = self.process_tblock(tbdata[0], [], url, embed, dbpost.id, tbindex)
                                dbtblocks.append(dbtblock)
                                tbindex += 1
             
                     if dbtblocks:
                        self.session.flush()

                     #Prep Tumblr Tags
                     tags = data.get('tags').split(',')
                     processedtags = self.process_tags(tags, 'tumblr')
                     if processedtags:
                         dbpost.tumblrtags = processedtags
                         self.session.flush()

                 else:
                     deletetbresult = Tumblrblock.query.filter(Tumblrblock.post_id == dbpost.id).delete()
                     if deletetbresult > 0:
                         self.session.flush()

                 if bluesky:
                     #Prep BlueSky skeets
                     bsimgs = data.getlist('bsimgs')
                     addbsimages = images and blueskyhasimages
                     deletebsresult = Blueskyskeet.query.filter(Blueskyskeet.post_id == dbpost.id, Blueskyskeet.order > bsskeetsnumber).delete()
                     if deletebsresult > 0:
                         self.session.flush()

                     i = 1
                     start = 0
                     end = 4
                     dbskeets = []
                     while i <= bsskeetsnumber:
                         skeetimgs = []
                         if addbsimages:
                             skeetimgs = bsimgs[start:end]
                             start += 4
                             end += 4
                         skeet = {}
                         try:
                            skeet = json.loads(str(data.get('bstext' + str(i))),strict=False)
                         except Exception as e:
                            current_app.logger.error(f"Process post skeet text - Could not parse into json, bstext{i}: {str(data.get('bstext' + str(i)))}")
                            raise e
                         dbskeet = self.process_skeet(skeet, finalimagefiles, skeetimgs, dbpost.id, i)
                         dbskeets.append(dbskeet)
                         i += 1

                     if dbskeets:
                        self.session.flush()

                 else:
                     deletebsresult = Blueskyskeet.query.filter(Blueskyskeet.post_id == dbpost.id).delete()
                     if deletebsresult > 0:
                         self.session.flush()
             
                 #create post job
                 self.generate_post_jobs(dbpost)

        except Exception as ex:
            self.message = 'Something went wrong with post add/edit: ' + str(self.postid) + ' -- ' + str(ex)
            current_app.logger.error('Post processing exception raised.', exc_info=True) 

        #set success flag
        self.success = (self.message == '')
        if self.success:
            if self.postid == -1:
                self.message = 'Post successfully added: ' + self.title
            else:
                self.message = 'Post successfully edited: ' + self.title
            current_app.logger.info(self.message)
            self.session.commit()
        else:
            self.session.rollback()
            current_app.logger.error(f'{self.message} : post -> {self.title}')

    def processimages(self, imagefiles, postid, fileorder, watermarks):
        validimagefile = True
        processedimagefiles = []
        for imagefile in imagefiles:
            validimagefile = validimagefile and self.allowed_file(imagefile.filename)

        if validimagefile:
            for imgfile in imagefiles:
                sfilename = secure_filename(imgfile.filename)
                imgpath = os.path.join(Config.UPLOAD_FOLDER, sfilename)
                if self.watcher_request:
                    ua = ua_generator.generate()
                    fileextension = imgfile.url.rsplit('.', 1)[1].lower()
                    r = requests.get(imgfile.url, stream=True, headers=ua.headers.get())
                    if r.status_code == 200:
                        if fileextension == "gif":
                            sfilename = sfilename.replace('.gif','.png')
                            imgpath = os.path.join(Config.UPLOAD_FOLDER, sfilename)
                        try:
                            im = PILImage.open(io.BytesIO(r.content))
                            im.save(imgpath)
                        except:
                            self.message += 'Could not fetch image file from url\n'
                            return []
                    else:
                        self.message += 'Could not fetch image file from url\n'
                        return []
                else:
                    imgfile.save(imgpath)
                try:
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
                    dbimg = DBImage(post_id=postid,url=sfilename, width=im.width, height=im.height,mimetype=im.get_format_mimetype(), order=index, ready=processed)
                    processedimagefiles.append(dbimg)
                except:
                    self.message += 'Problems processing image files\n'
                    return []

            self.session.add_all(processedimagefiles)
            self.session.flush()
        else:
            self.message += 'Invalid image file(s)' + '\n'

        return processedimagefiles

    def allowed_file(self, filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

    def delete_image(self, imagefile):
        filename = imagefile.url
        self.session.delete(imagefile)

        duplicates = DBImage.query.filter(DBImage.url == filename).all()

        if not duplicates:
            filepath = Config.UPLOAD_FOLDER + '/' + filename
            if os.path.exists(filepath):
                os.remove(filepath)

    def process_skeet(self, skeet, images, bsimgs, postid, order):
        dbskeet = Blueskyskeet.query.filter(Blueskyskeet.post_id == postid, Blueskyskeet.order == order ).first()
        addtodb = not dbskeet
        if addtodb:
            dbskeet = Blueskyskeet()
        imageids = []
        for bsimg in bsimgs:
            if bsimg != 'none':
                for img in images:
                    if bsimg == img.url:
                        imageids.append(img.id)

        plaintxt = ''
        plaintxt = plaintxt.encode("UTF-8",errors="backslashreplace")
        links = []
        for component in skeet:
            txtencoded = component['insert'].encode("UTF-8",errors="backslashreplace")
            if 'attributes' in component:
                urlstart = len(plaintxt)
                urlend = urlstart + len(component['insert'])
                link = component['attributes']['link']
                links.append({
                    "start": urlstart,
                    "end": urlend,
                    "link": link
                })

            plaintxt += txtencoded

        dbskeet.post_id = postid
        dbskeet.order = order
        dbskeet.imageids = imageids
        dbskeet.text = plaintxt
        dbskeet.quillops = skeet
        dbskeet.urls = links
        dbskeet.mentions = self.parse_mentions(plaintxt)
        dbskeet.tags = self.parse_hashtags(plaintxt)
        dbskeet.uri = ''
        dbskeet.cid = ''
        dbskeet.parenturi = ''
        dbskeet.parentcid = ''
        if addtodb:
            self.session.add(dbskeet)
        return dbskeet

    def process_image_tblock(self, images, tbimgs, postid, order):
        dbtblock = Tumblrblock.query.filter(Tumblrblock.post_id == postid, Tumblrblock.order == order ).first()
        addtodb = not dbtblock
        if addtodb:
            dbtblock = Tumblrblock()
        imageids = []
        for tbimg in tbimgs:
            for img in images:
                if tbimg == img.url:
                    imageids.append(img.id)

        dbtblock.post_id = postid
        dbtblock.order = order
        dbtblock.imageids = imageids
        dbtblock.blocktype = 'photo'
        dbtblock.quillops = []
        dbtblock.url = ''
        dbtblock.embed = ''
        dbtblock.reblogid = ''
        if addtodb:
            self.session.add(dbtblock)
        return dbtblock

    def process_tblock(self, tbtype, textops, url, embed, postid, order, npf= {}):
        dbtblock = Tumblrblock.query.filter(Tumblrblock.post_id == postid, Tumblrblock.order == order ).first()
        addtodb = not dbtblock
        if addtodb:
            dbtblock = Tumblrblock()

        dbtblock.post_id = postid
        dbtblock.order = order
        dbtblock.imageids = []
        dbtblock.blocktype = tbtype
        dbtblock.quillops = textops
        dbtblock.url = url
        dbtblock.npf = npf
        dbtblock.embed = embed
        dbtblock.reblogid = ''
        if addtodb:
            self.session.add(dbtblock)
        return dbtblock

    def process_tags(self, tags, tagtype):
        processedtags = []
        for tag in tags:
            strippedtag = tag.strip()
            dbtag = Tag.query.filter(Tag.tag == strippedtag, Tag.tagtype == tagtype ).first()
            if dbtag:
                dbtag.count = dbtag.count + 1
            else:
                dbtag = Tag(tag = strippedtag, tagtype = tagtype, count = 1)
                self.session.add(dbtag)
            processedtags.append(dbtag.tag)

        return processedtags

    def parse_hashtags(self, text: str):
        spans = []
        tags = []

        hashtag_regex = rb"(#(\w+))"
        text_bytes = text
        for m in re.finditer(hashtag_regex, text_bytes):
            tag = m.group(1).decode("UTF-8",errors="replace")
            tags.append(tag)
            spans.append({
                "start": m.start(1),
                "end": m.end(1),
                "tag": tag
            })
        processedtags = self.process_tags(tags, "bluesky")
        if processedtags:
            self.session.flush()
        return spans

    #function from Bluesky documentation: https://docs.bsky.app/docs/advanced-guides/post-richtext#rich-text-facets
    def parse_mentions(self, text: str):
        spans = []
        # regex based on: https://atproto.com/specs/handle#handle-identifier-syntax
        mention_regex = rb"[$|\W](@([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)"
        text_bytes = text
        for m in re.finditer(mention_regex, text_bytes):
            spans.append({
                "start": m.start(1),
                "end": m.end(1),
                "handle": m.group(1)[1:].decode("UTF-8",errors="replace")
            })
        return spans

    def generate_post_jobs(self, post: Post):
        dbpostjobs = []
        posttitle = post.title + ': '
        if post.fortumblr:
            posttitle += "Tumblr "
        if post.forbluesky:
            posttitle += "BlueSky "
        dbpostjob = Postjob.query.filter(Postjob.post_id == post.id, Postjob.repost == False, Postjob.published == False).first()
        dbepostjobs = Postjob.query.filter(Postjob.post_id == post.id, Postjob.published == False).all()
        for dbepostjob in dbepostjobs:
            if scheduler.get_job(str(dbepostjob.id)):
                scheduler.remove_job(str(dbepostjob.id))
        addtodb = not dbpostjob
        if addtodb:
            dbpostjob = Postjob()
        
        #get appropriate post time
        tzpublishdate = post.publishdate.astimezone(ZoneInfo(Config.TIMEZONE))
        noweekends = tzpublishdate.weekday() < 5

        post.publishdate = self.find_next_timeslot(post.publishdate,noWeekends = noweekends)

        dbpostjob.user_id = post.user_id
        dbpostjob.post_id = post.id
        dbpostjob.title = posttitle
        dbpostjob.publishdate = post.publishdate
        dbpostjob.published = False
        dbpostjob.repost = False

        if addtodb:
            self.session.add(dbpostjob)

        self.session.flush()
        dbpostjobs.append(dbpostjob)
        if (post.repost):
            Postjob.query.filter(Postjob.post_id == post.id, Postjob.repost == True, Postjob.published == False).delete()
            noontime = post.publishdate + timedelta(hours=5)
            noontimetz = noontime.astimezone(ZoneInfo(Config.TIMEZONE))
            if noweekends and noontimetz.weekday() >= 5:
                daysToMonday = 7 - noontimetz.weekday()
                noontime = (noontimetz + timedelta(days=daysToMonday)).astimezone(ZoneInfo("UTC"))
            noontime = self.find_next_timeslot(noontime,noWeekends = noweekends)
            eveningtime = self.find_next_timeslot(noontime + timedelta(hours=6),noWeekends = noweekends)

            dbpostjob_noon = Postjob(post_id = post.id, user_id = post.user_id, title = posttitle, publishdate = noontime, repost = True, published = False)
            dbpostjob_evening = Postjob(post_id = post.id, user_id = post.user_id, title = posttitle, publishdate = eveningtime, repost = True, published = False)

            self.session.add(dbpostjob_noon)
            self.session.add(dbpostjob_evening)
            self.session.flush()
            dbpostjobs.append(dbpostjob_noon)
            dbpostjobs.append(dbpostjob_evening)
        else:
            Postjob.query.filter(Postjob.post_id == post.id, Postjob.repost == True, Postjob.published == False).delete()
     
        for dbjob in dbpostjobs:
            scheduler.add_job(str(dbjob.id),sendpostjob,args=[dbjob.id],trigger="date",run_date=dbjob.publishdate,replace_existing=True)
            current_app.logger.info(f"Post job scheduled for: {dbjob.publishdate}")

        return dbpostjobs

    def find_next_timeslot(self,scheduledate, hourlimit = 4, noWeekends = True):
        scheduledatetz = scheduledate.astimezone(ZoneInfo(Config.TIMEZONE))
        newdate = scheduledatetz
        enddate = newdate + timedelta(weeks=1, days=1)
        endhour = scheduledatetz.hour + hourlimit
        if endhour > 23:
            endhour = 23
        if endhour < 0:
            endhour = 1
        alljobs = scheduler.scheduler.get_jobs()
        allscheduledjobs = [x for x in alljobs if x.next_run_time != None]
        allscheduledjobs.sort(key=lambda x: x.next_run_time)
        for job in allscheduledjobs:
            jobtz = job.next_run_time.astimezone(ZoneInfo(Config.TIMEZONE))
            if jobtz >= newdate - timedelta(minutes=5) and jobtz <= newdate + timedelta(minutes=5):
                newdate = newdate + timedelta(hours=1)
                if newdate.hour == endhour:
                    hoursToNextSlot = 24 - newdate.hour + scheduledatetz.hour
                    newdate = newdate + timedelta(hours=hoursToNextSlot)
                if noWeekends and newdate.weekday() >= 5:
                    daysToMonday = 7 - newdate.weekday()
                    newdate = newdate + timedelta(days=daysToMonday)

        if newdate > enddate:
            newdate = scheduledatetz

        return newdate.astimezone(ZoneInfo("UTC"))

    def find_best_day(self,scheduledate):
        nextrundate = (scheduledate).astimezone(ZoneInfo(Config.TIMEZONE))
        nextrundate.hour = 8
        nextmonday = 0 - nextrundate.weekday()
        if nextmonday <= -5:
            nextmonday += 7
        start = (nextrundate + timedelta(days=nextmonday)).astimezone(ZoneInfo("UTC"))
        end = (nextrundate + timedelta(days=4 + nextmonday)).astimezone(ZoneInfo("UTC"))

        jobsperday = {0:0,1:0,2:0,3:0,4:0,5:0,6:0}
        bestday = 0
        alljobs = scheduler.scheduler.get_jobs()
        allscheduledjobs = [x for x in alljobs if x.next_run_time != None]
        for job in allscheduledjobs:
            if job.next_run_time >= start and job.next_run_time <= end:
                jobsperday[job.next_run_time.weekday()] += 1

        min_val = min(jobsperday.values())
        for day, val in jobsperday.items():
            if val == min_val:
                bestday = day
                break

        return start + timedelta(days=bestday)
