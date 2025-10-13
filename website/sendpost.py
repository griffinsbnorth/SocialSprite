import datetime
from datetime import timedelta
import json
import uuid
from .models import Image as DBImage
from .models import Post, Blueskyskeet, Tumblrblock, Tag, Postjob
from . import db, scheduler
import pytumblr2
from dotenv import load_dotenv
load_dotenv()
import os
from config import Config

def sendpostjob(postjobid):
    from .processpost import Processpost
    app = scheduler.app
    with app.app_context():
        run_date = datetime.datetime.now()
        dbpostjob = Postjob.query.get(postjobid)
        if dbpostjob:
            dbpost = Post.query.get(dbpostjob.post_id)
            print(dbpost.title)
            #check for tumblr
            if dbpost.fortumblr:
                poster = TumblrPostClient(dbpost,reblog=dbpostjob.repost)
                poster.sendtumblrpost()
                if poster.success:
                    app.logger.info(f"{poster.message}: {run_date}")
                else:
                    app.logger.error(poster.message)

            #check for bluesky
            if dbpost.forbluesky:
                #send tumblr post
                sendblueskypost(dbpost)

            dbpostjob.published = True
            db.session.flush()
            if dbpost.cycle and not dbpostjob.repost:
                #update cycledate and scheduledate
                datediff = dbpost.cycledate - dbpost.publishdate
                print(datediff)
                dbpost.publishdate = dbpost.cycledate
                print(dbpost.publishdate)
                dbpost.cycledate = dbpost.cycledate + datediff
                print(dbpost.cycledate)
                db.session.commit()
                #generate postjobs
                postprocessor = Processpost(dbpost.id)
                postprocessor.generate_post_jobs(dbpost)


        app.logger.info(f"POST SENT AT: {run_date}")

def sendpost(postid):
    app = scheduler.app
    dbpost = Post.query.get(postid)
    run_date = datetime.datetime.now()
    #check for tumblr
    if dbpost.fortumblr:
        poster = TumblrPostClient(dbpost)
        poster.sendtumblrpost()
        if poster.success:
            app.logger.info(f"{poster.message}: {run_date}")
        else:
            app.logger.error(poster.message)

    #check for bluesky
    if dbpost.forbluesky:
        #send tumblr post
        sendblueskypost(dbpost)

    app.logger.info(f"POST SENT AT: {run_date}")


def sendblueskypost(post):
    print("bluesky post sent")

class TumblrPostClient():
    def __init__(self, post, reblog=False, session=db.session):
        self.success = True
        self.message = ''
        self.post = post
        self.reblog = reblog
        self.session = session
        self.client = pytumblr2.TumblrRestClient(
            os.getenv("TUMBLR_CONSUMER_KEY"),
            os.getenv("TUMBLR_CONSUMER_SECRET"),
            os.getenv("TUMBLR_OAUTH_TOKEN"),
            os.getenv("TUMBLR_OAUTH_TOKEN_SECRET"),
        )
        self.content = []
        self.display = []
        self.blockindex = 0
        self.media_sources = {}

    def __str__(self):
        return f"{self.message}"

    def sendtumblrpost(self):
        #get tumblr blocks
        blocks = Tumblrblock.query.filter(Tumblrblock.post_id == self.post.id).order_by(Tumblrblock.order).all()
        self.content = []
        self.blockindex = 0
        self.display = []

        for block in blocks:
            match block.blocktype:
                case "text":
                    self.processtextblock(block.npf)
                case "photo":
                    self.processphotoblock(block.imageids)
                case "link":
                    item = {
                        "type": "link",
                        "url": block.url
                        }
                    self.content.append(item)
                    self.display.append({"blocks": [self.blockindex]})
                    self.blockindex += 1
                case "audio":
                    item = {
                        "type": "audio",
                        "provider": self.findprovider(block.url,"audio"),
                        "url": block.url
                        }
                    if block.embed:
                        item['embed_html'] = block.embed
                    self.content.append(item)
                    self.display.append({"blocks": [self.blockindex]})
                    self.blockindex += 1
                case "video":
                    item = {
                        "type": "video",
                        "provider": self.findprovider(block.url,"video"),
                        "url": block.url
                        }
                    if block.embed:
                        item['embed_html'] = block.embed
                    self.content.append(item)
                    self.display.append({"blocks": [self.blockindex]})
                    self.blockindex += 1
                case _:
                    pass
        
        #add layout info
        layout = [{ "type": "rows", "display": self.display}]
        print(self.content)
        print(layout)
        print(self.media_sources)
        #send post to API
        
        if self.reblog:
            response = self.client.reblog_post(
                self.post.blogname,  # reblogging TO
                self.post.blogname,  # rebloggin FROM
                self.post.reblogid,
                content=self.content,
                layout=layout,
                media_sources=self.media_sources,
                tags=self.post.tumblrtags
            )
        else:
            response = self.client.create_post(
                self.post.blogname,
                content=self.content,
                layout=layout,
                media_sources=self.media_sources,
                tags=self.post.tumblrtags
            )
            if "errors" in response:
                self.success = False
                self.message = json.dumps(response)
            else:
                self.success = True
                self.message = "Tumblr post sent"
            self.post.reblogid = response["id"]
            

    def processtextblock(self, npf):
        for item in npf['content']:
            if 'formatting' in item:
                if item['formatting'][0]['type'] == 'mention':
                    blogname = item['formatting'][0]['blog']
                    blogurl = blogname + '.tumblr.com'
                    #get blog uuid
                    bloginfo = self.client.blog_info(blogurl)
                    if 'blog' in bloginfo:
                        if 'uuid' in bloginfo['blog']:
                            blog = { "uuid": bloginfo['blog']['uuid'], "name": blogname, "url": blogurl,}
                            item['formatting'][0]['blog'] = blog
                        else:
                            item['formatting'][0]['type'] == 'bold'
                            item['formatting'][0].pop('blog')

            self.content.append(item)
            self.display.append({"blocks": [self.blockindex]})
            self.blockindex += 1

        return

    def processphotoblock(self,imageids):
        blocks = []
        images = DBImage.query.filter(DBImage.post_id == self.post.id).order_by(DBImage.order).all()
        top_img = True
        second_img = False
        for img in images:
            if img.id in imageids:
                resource_path = Config.UPLOAD_FOLDER + '/' + img.url
                identifier = str(img.id)
                mediablock = {                     
                        "type": img.mimetype,
                        "identifier": identifier,
                        "url": resource_path,
                        "width": img.width,
                        "height": img.height
                        }
                self.content.append({"type": "image", "media": [mediablock]})
                self.media_sources[identifier] = resource_path
                blocks.append(self.blockindex)
                self.blockindex += 1
                if top_img:
                    self.display.append({"blocks": blocks})
                    blocks = []
                    top_img= False
                else:
                    if second_img:
                        self.display.append({"blocks": blocks})
                        blocks = []
                    second_img = not second_img

        if blocks:
            self.display.append({"blocks": blocks})
                
        return

    def findprovider(self,url,type):
        searchurl = url.lower()
        provider = 'tumblr'
        if type == 'audio':
            if 'spotify' in searchurl:
                provider = 'spotify'
            elif 'bandcamp' in searchurl:
                provider = 'bandcamp'
            elif 'soundcloud' in searchurl:
                provider = 'soundcloud'
        else:
            if 'youtube' in searchurl:
                provider = 'youtube'
            elif 'vimeo' in searchurl:
                provider = 'vimeo'

        return provider
