import datetime
from datetime import timedelta
from .models import Image as DBImage
from .models import Post, Blueskyskeet, Tumblrblock, Tag, Postjob
from . import db, scheduler

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
                #send tumblr post
                sendtumblrpost(dbpost)

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
    print(dbpost.title)
    #check for tumblr
    if dbpost.fortumblr:
        #send tumblr post
        sendtumblrpost(dbpost)

    #check for bluesky
    if dbpost.forbluesky:
        #send tumblr post
        sendblueskypost(dbpost)

    app.logger.info(f"POST SENT AT: {run_date}")

def sendtumblrpost(post):
    print("tumblr post sent")

def sendblueskypost(post):
    print("bluesky post sent")