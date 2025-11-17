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
from atproto import Client, client_utils, models, IdResolver

def sendpostjob(postjobid):
    from .processpost import Processpost
    app = scheduler.app
    with app.app_context():
        run_date = datetime.datetime.now()
        dbpostjob = Postjob.query.get(postjobid)
        if dbpostjob:
            dbpost = Post.query.get(dbpostjob.post_id)
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
                poster = BlueSkyClient(dbpost,repost=dbpostjob.repost)
                poster.sendblueskypost()
                if poster.success:
                    app.logger.info(f"{poster.message}: {run_date}")
                else:
                    app.logger.error(poster.message)

            dbpostjob.published = True
            db.session.flush()
            if dbpost.cycle and not dbpostjob.repost:
                #update cycledate and scheduledate
                datediff = (dbpost.cycledate - dbpost.publishdate) * 2
                dbpost.publishdate = dbpost.cycledate
                dbpost.cycledate = dbpost.cycledate + datediff
                #generate postjobs
                postprocessor = Processpost(dbpost.id)
                postprocessor.generate_post_jobs(dbpost)
                if datediff.days >= 180:
                    dbpost.cycle = False

            db.session.commit()

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
        poster = BlueSkyClient(dbpost)
        poster.sendblueskypost()
        if poster.success:
            app.logger.info(f"{poster.message}: {run_date}")
        else:
            app.logger.error(poster.message)

    db.session.commit()

    app.logger.info(f"POST SENT AT: {run_date}")

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
        if self.reblog and self.post.reblogid:
            response = self.client.reblog_post(
                self.post.blogname,  # reblogging TO
                self.post.blogname,  # rebloggin FROM
                self.post.reblogid,
                self.post.uuid,
                self.post.reblogkey
            )
            if "errors" in response:
                self.message = json.dumps(response)
                self.message += " Reblog failed. Defaulting to regular post. "
            else:
                self.success = True
                self.message = "Tumblr post reblogged"
                return

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

        #send post to API
        response = self.client.create_post(
            self.post.blogname,
            content=self.content,
            layout=layout,
            media_sources=self.media_sources,
            tags=self.post.tumblrtags
        )
        if "errors" in response:
            self.success = False
            self.message += json.dumps(response)
        else:
            self.success = True
            self.message += "Tumblr post sent"
            postid = response["id"]
            response = self.client.get_single_post(self.post.blogname,postid)
            if "errors" in response:
                self.success = False
                self.message += json.dumps(response)
            else:
                self.post.reblogid = postid
                self.post.uuid = response['blog']['uuid']
                self.post.reblogkey = response['reblog_key']
            

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

class BlueSkyClient():
    def __init__(self, post, repost=False, session=db.session):
        self.success = True
        self.message = ''
        self.post = post
        self.repost = repost
        self.session = session
        self.client = Client()
        self.client.login(os.getenv("BLUESKY_USERNAME"), os.getenv("BLUESKY_PASSWORD"))
        self.dbimages = DBImage.query.filter(DBImage.post_id == self.post.id).order_by(DBImage.order).all()

    def __str__(self):
        return f"{self.message}"

    def sendblueskypost(self):
        skeets = Blueskyskeet.query.filter(Blueskyskeet.post_id == self.post.id).order_by(Blueskyskeet.order).all()

        if skeets and self.repost:
            try:
                response = self.client.get_posts([skeets[0].uri])
                if len(response['posts']) > 0:
                    self.client.repost(uri=skeets[0].uri, cid=skeets[0].cid)
                    self.message = "BlueSky repost sent"
                    return
                else:
                    self.message = "Repost failed. Trying regular posting. "
            except Exception as ex:
                self.message += str(ex)

        root = None
        parent = None
        for skeet in skeets:
            facets = self.processfacets(skeet)
            
            if skeet.imageids:
                try:
                    aspects, images = self.processimages(skeet.imageids)
                    if root == None:
                        root = models.create_strong_ref(self.client.send_images(text=skeet.text.decode('UTF-8'),facets=facets,images=images,image_aspect_ratios=aspects))
                        parent = root
                    else:
                        parent_ref = parent
                        parent = models.create_strong_ref(self.client.send_images(text=skeet.text.decode('UTF-8'),facets=facets,images=images,image_aspect_ratios=aspects,reply_to=models.AppBskyFeedPost.ReplyRef(parent=parent_ref, root=root)))
                except Exception as ex:
                    self.success = False
                    self.message += str(ex)
            else:
                try:
                    if root == None:
                        root = models.create_strong_ref(self.client.send_post(text=skeet.text.decode('UTF-8'),facets=facets))
                        parent = root
                    else:
                        parent_ref = parent
                        parent = models.create_strong_ref(self.client.send_post(text=skeet.text.decode('UTF-8'),facets=facets,reply_to=models.AppBskyFeedPost.ReplyRef(parent=parent_ref, root=root)))
                except Exception as ex:
                    self.success = False
                    self.message += str(ex)

            try:
                skeet.parentcid = root.cid
                skeet.parenturi = root.uri
                skeet.cid = parent.cid
                skeet.uri = parent.uri
            except Exception as ex:
                self.success = False
                self.message += str(ex)
                   
        if self.success:
            self.message += " BlueSky post sent"

    def processfacets(self, skeet):
        facets = []
        for url in skeet.urls:
            facet = models.AppBskyRichtextFacet.Main(
                features=[models.AppBskyRichtextFacet.Link(uri=url["link"])],
                index=models.AppBskyRichtextFacet.ByteSlice(byte_start=url["start"], byte_end=url["end"]),
            )
            facets.append(facet)

        for tag in skeet.tags:
            facet = models.AppBskyRichtextFacet.Main(
                features=[models.AppBskyRichtextFacet.Tag(tag=tag["tag"])],
                index=models.AppBskyRichtextFacet.ByteSlice(byte_start=tag["start"], byte_end=tag["end"]),
            )
            facets.append(facet)

        for mention in skeet.mentions:
            resolver = IdResolver()
            did = resolver.handle.resolve(mention["handle"])
            if did:
                facet = models.AppBskyRichtextFacet.Main(
                    features=[models.AppBskyRichtextFacet.Mention(did=did)],
                    index=models.AppBskyRichtextFacet.ByteSlice(byte_start=mention["start"], byte_end=mention["end"]),
                )
                facets.append(facet)

        return facets

    def processimages(self,imageids):
        aspects = []
        images = []
        for dbimg in self.dbimages:
            if dbimg.id in imageids:
                path = Config.UPLOAD_FOLDER + '/' + dbimg.url
                aspects.append(models.AppBskyEmbedDefs.AspectRatio(height=dbimg.height, width=dbimg.width))
                with open(path, 'rb') as f:
                    images.append(f.read())
        
        return (aspects, images)
