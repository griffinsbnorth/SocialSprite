import sched
from flask import current_app
import re
import os
from atproto import models
import datetime
from zoneinfo import ZoneInfo

from config import Config
from . import db, scheduler
from .watcher import watcher
from .models import Watcher

class Processwatcher():

    def __init__(self, watcherid=-1):
        self.success = True
        self.message = ''
        self.watcherid = watcherid

    def __str__(self):
        return f"{self.message}"

    def validatesearchkey(self, searchkey):
        message = ''
        keysplit = searchkey.split(':')
        if (len(keysplit) != 3):
            message += searchkey + ' not formatted correctly.\n'

        return message

    def removejob(self):
        if self.watcherid != -1:
            job = scheduler.get_job("w" + str(self.watcherid))
            if job:
                scheduler.remove_job("w" + str(self.watcherid))


    def processform(self, data, userid):
        print(data)
        wtype = data.get('wtype')
        wurl = data.get('url')

        month = data.get('month')
        day_of_month = data.get('day_of_month')
        day_of_week = data.getlist('day_of_week')
        print(day_of_week)
        hour = data.get('hour')
        minute = data.get('minute')

        repost = data.get('repost') != None

        cycle = data.get('cycle') != None
        days = data.get('days')
        weeks = data.get('weeks')

        images = data.get('images') != None
        tumblr = data.get('tumblr') != None
        bluesky = data.get('bluesky') != None
        tbhasimages = data.get('tbhasimages') != None
        bshasimages = data.get('bshasimages') != None

        blogname = data.get('blogname')
        if blogname == '':
            blogname = os.getenv("BLOGNAME")
        bstags = data.get('bstags')
        tbtags = data.get('ttags')

        posttext = data.get('posttext')
        searchkeys = []
        titleprefix = ""
        titlekey = ""
        updatekey = ""
        prevkey = ""
        nextkey = ""
        slugkey = ""
        archival = False
        pagenum = 0

        self.message = ''
        if (month == 0 and day_of_month == 0 and not day_of_week and hour == -1 and minute == -1):
            self.message += 'At least one schedule behaviour must be chosen' + '\n'
        if (cycle and days == 0 and weeks == 0):
            self.message += 'Missing cycle data.' + '\n'
        if (images and not tbhasimages and not bshasimages):
            self.message += 'Images is selected but no social media was selected to add images to.' + '\n'
        if (not tumblr and not bluesky):
            self.message += 'No social media selected for post generation.' + '\n'
        if (wtype == "comic"):
            searchkeysstring = data.get('searchkeys')
            searchkeys = searchkeysstring.split(',')
            titleprefix = data.get('titleprefix')
            titlekey = data.get('titlekey')
            updatekey = data.get('updatekey')
            prevkey = data.get('prevkey')
            nextkey = data.get('nextkey')
            slugkey = data.get('slugkey')
            archival = data.get('archival') != None
            pagenum = int(data.get('pagenum'))
            if (archival and pagenum == 0):
                self.message += 'Pages per update can\'t be empty if archival.' + '\n'
            if (titlekey != "slug"):
                self.message += self.validatesearchkey(titlekey)
            if slugkey:
                self.message += self.validatesearchkey(slugkey)
            self.message += self.validatesearchkey(updatekey)
            self.message += self.validatesearchkey(prevkey)
            self.message += self.validatesearchkey(nextkey)
            if searchkeys:
                for searchkey in searchkeys:
                    self.message += self.validatesearchkey(searchkey)
            else:
                self.message += 'Image search keys can\'t be empty.' + '\n'

        if self.message == '':
            dbwatcher = Watcher()
            if self.watcherid != -1:
                 dbwatcher = Watcher.query.get(self.watcherid)

            scheduledata = {}
            scheduledata['month'] = month
            scheduledata['day_of_month'] = day_of_month
            daylist = []
            for day in day_of_week:
                daylist.append(day)
            scheduledata['day_of_week'] = daylist
            scheduledata['hour'] = hour
            scheduledata['minute'] = minute

            postcheckmarks = []
            if repost:
                postcheckmarks.append('repost')
            if cycle:
                postcheckmarks.append('cycle')
            if images:
                postcheckmarks.append('images')
            if tumblr:
                postcheckmarks.append('tumblr')
            if bluesky:
                postcheckmarks.append('bluesky')
            if tbhasimages:
                postcheckmarks.append('tbhasimages')
            if bshasimages:
                postcheckmarks.append('bshasimages')

            dbwatcher.user_id = userid
            dbwatcher.wtype = wtype
            dbwatcher.url = wurl
            dbwatcher.searchkeys = searchkeys
            dbwatcher.titleprefix = titleprefix
            dbwatcher.posttext = posttext
            dbwatcher.titlekey = titlekey
            dbwatcher.updatekey = updatekey
            dbwatcher.slugkey = slugkey
            dbwatcher.archival = archival
            dbwatcher.pagesperupdate = pagenum
            dbwatcher.nextkey = nextkey
            dbwatcher.prevkey = prevkey
            dbwatcher.postcheckmarks = postcheckmarks
            dbwatcher.bstags = bstags
            dbwatcher.tbtags = tbtags
            dbwatcher.blogname = blogname
            dbwatcher.cycledelta = {'days':days,'weeks':weeks}
            dbwatcher.scheduledata = scheduledata

            if self.watcherid == -1:
                dbwatcher.lastupdate = ""
                dbwatcher.lastran = datetime.datetime.now().astimezone(ZoneInfo("UTC"))
                dbwatcher.status = "Good"
                dbwatcher.running = True
                db.session.add(dbwatcher)

            db.session.commit()

            month_str = '*'
            if month != '0':
                month_str = month
            day_of_month_str = '*'
            if day_of_month != '0':
                day_of_month_str = day_of_month
            daylist_str = ''
            for day in day_of_week:
                daylist_str += day + ','
            if daylist_str:
                daylist_str = daylist_str[:-1]
            else:
                daylist_str = '*'
            hour_str = '*'
            if hour != '-1':
                hour_str = hour
            minute_str = '*'
            if minute != '-1':
                minute_str = minute
            
            print(month_str + ' ' + day_of_month_str + ' ' + hour_str + ' ' + minute_str + ' ' + daylist_str)
            jobname = "w" + str(dbwatcher.id)
            job = scheduler.get_job(jobname)
            if job:
                job = scheduler.modify_job(jobname,"default",trigger="cron",month=month_str,day=day_of_month_str,hour=hour_str,minute=minute_str,day_of_week=daylist_str,timezone=ZoneInfo(Config.TIMEZONE))
                print(f"Watcher rescheduled for: {job.next_run_time}")
            else:
                job = scheduler.add_job(jobname,watcher,args=[dbwatcher.id],trigger="cron",month=month_str,day=day_of_month_str,hour=hour_str,minute=minute_str,day_of_week=daylist_str,timezone=ZoneInfo(Config.TIMEZONE))
                print(f"Watcher scheduled for: {job.next_run_time}")

        #set success flag
        self.success = (self.message == '')
        if self.success:
            if self.watcherid == -1:
                self.message = 'Watcher successfully added'
            else:
                self.message = 'Watcher successfully edited'
        return

    def setwatcher(self,running):
        jobname = "w" + str(self.watcherid)
        job = scheduler.get_job(jobname)
        if job:
            if running:
                job.resume()
                print(f"Watcher resumed schedule.")
            else:
                job.pause()
                print(f"Watcher paused.")
        else:
            print("Job for watcher not found")

