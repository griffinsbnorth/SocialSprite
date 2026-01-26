from flask import Blueprint, render_template, request, current_app, flash, jsonify, send_file
from flask_login import login_required, current_user
from .models import Post, Blueskyskeet, Tumblrblock, Tag, Postjob, Watcher, User
from .models import Image as DBImage
from config import Config
from .processpost import Processpost
from .processwatcher import Processwatcher
from zoneinfo import ZoneInfo
from . import db
import json
import hmac
import hashlib
import os
from werkzeug.datastructures import MultiDict
import datetime
from datetime import timedelta

views = Blueprint('views', __name__)

@views.route('/')
@login_required
def home():
    latestjobs = Postjob.query.filter(Postjob.user_id == current_user.id,Postjob.published == True).order_by(Postjob.publishdate).limit(10).all()

    currentdate = datetime.datetime.now()
    events = getcalendarmonth(currentdate.year,currentdate.month)

    return render_template("home.html", user=current_user, events=events, latestjobs=latestjobs)

@views.route('/addpost', methods=['GET', 'POST'])
@login_required
def addpost():
    postdata = {
        'id': -1,
        'title': '', 
        'scheduledate': '', 
        'cycleweeks': 1,
        'time': '08:00',
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
    if not editpost:
        return render_template("404.html", user=current_user)

    scheduledatetime = editpost.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
    skeetsdata = getskeets(postid)
    tumblrdata = gettumblrblocks(postid)

    postdata = {
        'id': postid,
        'title': editpost.title, 
        'scheduledate': scheduledatetime.strftime('%Y-%m-%d'), 
        'cycleweeks': editpost.cycleweeks,
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

@views.route('/posts', methods=['GET', 'POST'])
@login_required
def posts():
    search_query = request.args.get('q', '')
    currentpage = request.args.get('page', 1, type=int)
    pagination = []
    numpages = 15
    if search_query:
        pagination = Post.query.filter(Post.title.ilike(f'%{search_query}%')).paginate(page=currentpage, per_page=numpages)
    else:
        pagination = Post.query.filter(Post.user_id == current_user.id).order_by(Post.publishdate).paginate(page=currentpage, per_page=numpages)

    for item in pagination.items:
        item.publishdate = item.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))

    return render_template("posts.html", user=current_user, pagination=pagination)

@views.route('/addwatcher', methods=['GET', 'POST'])
@login_required
def addwatcher():
    watcherdata = {
        'id': -1,
        'url': '',
        'wtype': 'comic',
        'titleprefix': '',
        'titlekey': '',
        'searchkeys': '',
        'updatekey': '',
        'prevkey': '',
        'nextkey': '',
        'slugkey': '',
        'posttext': '',
        'pagenum': 1,
        'scheduledata': {'month':0,'day_of_month':0,'day_of_week':[],'hour':-1,'minute':-1}, 
        'cycleweeks': 1,
        'repost': True,
        'cycle': True,
        'images': True,
        'tumblr': True,
        'bluesky': True,
        'tbhasimages': True,
        'bshasimages': True,
        'archival': False,
        'blogname': '',
        'ttags': '',
        'bstags': '',
        'toptbtags': gettoptags('tumblr'),
        'topbstags': gettoptags('bluesky')
        }

    if request.method == 'POST':
        data = request.form
        watcherprocessor = Processwatcher()
        watcherprocessor.processform(data, current_user.id)
        if watcherprocessor.success:
            flash(watcherprocessor.message, category='success')
        else:
            flash(watcherprocessor.message, category='error')

    return render_template("addwatcher.html", user=current_user, watcherdata=watcherdata, watcherop='ADD')

@views.route('/editwatcher/<int:watcherid>', methods=['GET', 'POST'])
def editwatcher(watcherid):
    if request.method == 'POST':
        data = request.form
        watcherprocessor = Processwatcher(watcherid)
        watcherprocessor.processform(data, current_user.id)
        if watcherprocessor.success:
            flash(watcherprocessor.message, category='success')
        else:
            flash(watcherprocessor.message, category='error')

    editwatcher = Watcher.query.get(watcherid)
    if not editwatcher:
        return render_template("404.html", user=current_user)

    scheduledata = editwatcher.scheduledata
    postcheckmarks = editwatcher.postcheckmarks

    watcherdata = {
        'id': watcherid,
        'url': editwatcher.url,
        'wtype': editwatcher.wtype,
        'titleprefix': editwatcher.titleprefix,
        'titlekey': editwatcher.titlekey,
        'searchkeys': editwatcher.searchkeys,
        'updatekey': editwatcher.updatekey,
        'prevkey': editwatcher.prevkey,
        'nextkey': editwatcher.nextkey,
        'slugkey': editwatcher.slugkey,
        'posttext': editwatcher.posttext,
        'pagenum': editwatcher.pagesperupdate,
        'scheduledata': {'month':scheduledata['month'],'day_of_month':scheduledata['day_of_month'],'day_of_week':scheduledata['day_of_week'],'hour':scheduledata['hour'],'minute':scheduledata['minute']}, 
        'cycleweeks': editwatcher.cycleweeks,
        'repost': 'repost' in postcheckmarks,
        'cycle': 'cycle' in postcheckmarks,
        'images': 'images' in postcheckmarks,
        'tumblr': 'tumblr' in postcheckmarks,
        'bluesky': 'bluesky' in postcheckmarks,
        'tbhasimages': 'tbhasimages' in postcheckmarks,
        'bshasimages': 'bshasimages' in postcheckmarks,
        'archival': editwatcher.archival,
        'blogname': editwatcher.blogname,
        'ttags': editwatcher.tbtags,
        'bstags': editwatcher.bstags,
        'toptbtags': gettoptags('tumblr'),
        'topbstags': gettoptags('bluesky')
        }

    return render_template("addwatcher.html", user=current_user, watcherdata=watcherdata, watcherop='EDIT')

@views.route('/watchers', methods=['GET', 'POST'])
@login_required
def watchers():
    search_query = request.args.get('q', '')
    currentpage = request.args.get('page', 1, type=int)
    pagination = []
    numpages = 15
    if search_query:
        pagination = Watcher.query.filter(Watcher.url.ilike(f'%{search_query}%')).paginate(page=currentpage, per_page=numpages)
    else:
        pagination = Watcher.query.filter(Watcher.user_id == current_user.id).order_by(Watcher.lastran).paginate(page=currentpage, per_page=numpages)

    for item in pagination.items:
        item.lastran = item.lastran.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
        item.scheduledata = formatscheduledata(item.scheduledata)

    return render_template("watchers.html", user=current_user, pagination=pagination)

@views.route('/queue', methods=['GET', 'POST'])
@login_required
def queuepage():
    search_query = request.args.get('q', '')
    currentpage = request.args.get('page', 1, type=int)
    pagination = []
    numpages = 15
    if search_query:
        pagination = Postjob.query.filter(Postjob.title.ilike(f'%{search_query}%')).paginate(page=currentpage, per_page=numpages)
    else:
        pagination = Postjob.query.filter(Postjob.user_id == current_user.id).order_by(Postjob.publishdate).paginate(page=currentpage, per_page=numpages)

    for item in pagination.items:
        item.publishdate = item.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))

    return render_template("queue.html", user=current_user, pagination=pagination)

@views.route('/deletewatcher', methods=['POST'])
def delete_watcher():  
    data = json.loads(request.data)
    watcherid = data['watcherid']
    watcher = Watcher.query.get(watcherid)
    if watcher:
        if watcher.user_id == current_user.id:
            watcherprocessor = Processwatcher(watcherid)
            watcherprocessor.removejob()
            db.session.delete(watcher)
            db.session.commit()

    return jsonify({})

@views.route('/runwatcher', methods=['POST'])
def runwatcher():  
    data = json.loads(request.data)
    watcherid = data['watcherid']
    from .watcher import watcher
    watcher(watcherid)

    return jsonify({})

@views.route('/setwatcherstatus', methods=['POST'])
def setwatcherstatus():  
    data = json.loads(request.data)
    watcherid = data['watcherid']
    watcher = Watcher.query.get(watcherid)
    if watcher:
        if watcher.user_id == current_user.id:
            watcherprocessor = Processwatcher(watcherid,site=watcher.url)
            watcher.running = not watcher.running
            watcherprocessor.setwatcher(watcher.running)
            if watcher.running:
                watcher.status = "Good"
            else:
                watcher.status = "Paused"
            db.session.commit()

    return jsonify({})

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
            postprocessor.removejobs()
            Postjob.query.filter(Postjob.post_id == postid, Postjob.published == False).delete()
            db.session.commit()

    return jsonify({})

@views.route('/runpost', methods=['POST'])
def runpost():  
    data = json.loads(request.data)
    postid = data['postid']
    from .sendpost import sendpost
    sendpost(postid)

    return jsonify({})

@views.route('/editrepost', methods=['POST'])
def edit_repost():  
    post = json.loads(request.data)
    postid = post['postid']
    repost = post['repost']
    post = Post.query.get(postid)
    postprocessor = Processpost(postid)
    if post:
        if post.user_id == current_user.id:
            post.repost = repost
            db.session.commit()
            postprocessor.generate_post_jobs(post)
            

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

@views.route('/deletepostjob', methods=['POST'])
def deletepostjob():  
    postjobdata = json.loads(request.data)
    postjobid = postjobdata['postjobid']
    postjob = Postjob.query.get(postjobid)
    if postjob:
        if postjob.user_id == current_user.id:
            db.session.delete(postjob)
            db.session.commit()

    return jsonify({})


@views.route('/loadfile', methods=['GET'])
def loadfile():
    source = request.args.get('source')
    filepath = Config.UPLOAD_FOLDER + '/' + source

    return send_file(filepath)

@views.route('/loadmonth', methods=['GET'])
def loadmonth():
    year = int(request.args.get('year'))
    month = int(request.args.get('month'))
    events = getcalendarmonth(year,month)

    return jsonify(events)

@views.route("/patreonpost", methods=["POST"])
def patreon_post():
    """
    Endpoint to receive Patreon webhook events
    """
    from dotenv import load_dotenv
    load_dotenv()
    # Verify the webhook signature
    webhook_secret = os.getenv("PATREON_WEBHOOK_SECRET")
    
    signature = request.headers.get("X-Patreon-Signature")
    if not signature:
        current_app.logger.info("No patreon signature in webhook request.")
        return jsonify({"error": "No signature"}), 401
    
    # Verify signature
    body = request.get_data()
    expected_sig = hmac.new(
        webhook_secret.encode('utf-8'),
        body,
        hashlib.md5
    ).hexdigest()
    
    if signature != expected_sig:
        current_app.logger.info("Invalid patreon signature from webhook request.")
        return jsonify({"error": "Invalid signature"}), 401
    
    # Process the webhook
    data = request.json
    
    if data.get("data", {}).get("type") == "post":
        blacklist = ['The stream is up!']
        post_data = data["data"]
        publishdate = datetime.datetime.now() + timedelta(hours=1)
        cycleweeks = 5
        user = User.query.filter(User.username == os.getenv("SS_USERNAME")).first()

        if not user:
            current_app.logger.info(f'Patreon webhook - Found no user.')
            return jsonify({"error": "Found no user"}), 401

        # Latest post
        latest_post = {
            "id": post_data["id"],
            "title": post_data["attributes"].get("title", ""),
            "content": post_data["attributes"].get("content", ""),
            "url": 'https://www.patreon.com' + post_data["attributes"].get("url", ""),
            "published_at": post_data["attributes"].get("published_at", "")
        }

        for blackitem in blacklist:
            if blackitem in latest_post['content']:
                return jsonify({"status": "ok"}), 200
            if blackitem in latest_post['title']:
                return jsonify({"status": "ok"}), 200

        tags = 'patreon'
        bstags = '#patreon'

        pdata = MultiDict()
        pdata['title'] = latest_post['title']
        pdata['scheduledate'] = publishdate.strftime("%Y-%m-%d")
        pdata['time'] = publishdate.strftime("%H:%M")
        pdata['cycleweeks'] = cycleweeks
        pdata['tags'] = tags
        pdata['blogname'] = ''
        pdata['fileorder'] = '{}'
        pdata['tumblr'] = 'tumblr'
        pdata['bluesky'] = 'bluesky'
        pdata['repost'] = 'repost'
        pdata['cycle'] = 'cycle'
        pdata.add('bsskeetlen', '1')
        bstext = '[{"attributes":{"link":"' + latest_post['url'] + '"},"insert":"' + latest_post['title'] + '"},{"insert":"New post up on patreon! ' +  bstags + '\\n"}]'
        pdata.add('bstext1', bstext)
        pdata.add('tbtype', 'link:1')
        pdata.add('tbtype', 'text:2')
        pdata.add('tblink1url', latest_post['url'])
        tbtext = '[{"insert":"' + latest_post['title'] + '"},{"attributes":{"header":1},"insert":"\\n"},{"insert":"New post up on patreon!\\n"}]'
        pdata.add('tbtext2', tbtext)

        files = MultiDict() #This should remain empty
        postprocessor = Processpost()
        postprocessor.processform(pdata, files, user.id)
    
    return jsonify({"status": "ok"}), 200

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

def formatscheduledata(scheduledata):
    month_str = '*'
    if scheduledata['month'] != '0':
        month_str = scheduledata['month']
    day_of_month_str = '*'
    if scheduledata['day_of_month'] != '0':
        day_of_month_str = scheduledata['day_of_month']
    daylist_str = '*'
    if scheduledata['day_of_week']:
        daylist_str = ','.join(scheduledata['day_of_week'])
    hour_str = '*'
    if scheduledata['hour'] != '-1':
        hour_str = scheduledata['hour']
    minute_str = '*'
    if scheduledata['minute'] != '-1':
        minute_str = scheduledata['minute']
            
    return minute_str + ' ' + hour_str + ' ' + day_of_month_str + ' ' + month_str + ' ' + daylist_str

def getcalendarmonth(year, month):
    startdate = datetime.datetime(year,month,1,tzinfo=ZoneInfo(Config.TIMEZONE))
    if month == 12:
        month = 1
        year += 1
    enddate = datetime.datetime(year,month + 1,1,tzinfo=ZoneInfo(Config.TIMEZONE))
    startdate = startdate.replace(tzinfo=ZoneInfo(Config.TIMEZONE)).astimezone(ZoneInfo("UTC"))
    enddate = enddate.replace(tzinfo=ZoneInfo(Config.TIMEZONE)).astimezone(ZoneInfo("UTC"))
    postjobs = Postjob.query.filter(Postjob.user_id == current_user.id,Postjob.publishdate >= startdate,Postjob.publishdate < enddate).order_by(Postjob.publishdate).all()
    
    events = {}
    for postjob in postjobs:
        start = postjob.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
        link =  f'/editpost/{postjob.post_id}'
        event = { 'startTime': start.strftime("%H:%M"), 'endTime': start.strftime("%H:%M"), 'text': postjob.title, 'link': link }
        year = int(start.strftime("%Y"))
        month = int(start.strftime("%m"))
        day = int(start.strftime("%d"))
        if year in events:
            if month in events[year]: 
                if day in events[year][month]:
                    events[year][month][day].append(event)
                else:
                    events[year][month][day] = [ event ]
            else:
                events[year][month] = { day: [ event ]}
        else:
            events[year] = { month: { day: [ event ]}}

    return events

