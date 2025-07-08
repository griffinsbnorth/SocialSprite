import re
from xmlrpc.client import MAXINT
import requests
from bs4 import BeautifulSoup
import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from werkzeug.datastructures import MultiDict
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import math
from website.models import Watcher
from .processpost import Processpost
import json
import ua_generator
import feedparser
from . import db, scheduler

def watcher(watcherid):
    app = scheduler.app
    with app.app_context():
        watcher = Watcher.query.get(watcherid)

        running = False
        match watcher.wtype:
            case "comic":
                watchercomic(watcher)
            case "blog":
                watcherblog(watcher)
            case "youtube":
                watcheryoutube(watcher)
            case "twitch":
                watchertwitch(watcher)

        if not running:
            jobname = "w" + str(watcher.id)
            scheduler.pause_job(jobname)

def watchertwitch(watcher:Watcher):
    return

def watcherblog(watcher:Watcher):
    feed_url = watcher.url
    lastupdate = watcher.lastupdate
    postcheckmarks = watcher.postcheckmarks
    tbtags = watcher.tbtags
    bstags = watcher.bstags
    blogname = watcher.blogname
    posttext = watcher.posttext
    #cycledelta is a list of time ---> days, weeks
    cycledelta = [int(watcher.cycledelta["days"]), int(watcher.cycledelta["weeks"])]

    fileorder = {}
    fileindex = 0
    filenamelist = []
    data = MultiDict()
    files = MultiDict()

    blog_feed = feedparser.parse(feed_url)
    posts = blog_feed.entries

    if lastupdate != posts[0].published:
        postprocessor = Processpost(watcher_request=True)

        #setting publish time
        publishdate = datetime.datetime.now() + timedelta(hours=5)
        cycledate = datetime.datetime.now() + timedelta(weeks=1)
        if 'cycle' in postcheckmarks:
            cycledate = datetime.datetime.now() + timedelta(days=cycledelta[0],weeks=cycledelta[1])

        soup = BeautifulSoup(posts[0].content[0].value, 'html5lib')
        summarysoup = BeautifulSoup(posts[0].summary, 'html5lib')
        #find image
        if 'images' in postcheckmarks:
            imgs = soup.body.findAll('img')

            if imgs:
                for img in imgs:
                    #add to file list
                    url_parsed = urlparse(img['src'])
                    filename = unquote(PurePosixPath(url_parsed.path).name)
                    if filename.startswith('https'):
                        splitpathname = filename.split('/')
                        filename = splitpathname.pop()
                    if postprocessor.allowed_file(filename):
                        file = WatcherFile(filename,img['src'])
                        files.add('imgupload', file)
                        #add to fileorder
                        fileorder[filename] = fileindex
                        filenamelist.append(filename)
                        fileindex += 1
                data['fileorder'] = json.dumps(fileorder)
            else: 
                postcheckmarks.remove('images')
                postcheckmarks.remove('bshasimages')
                postcheckmarks.remove('tbhasimages')
                data['fileorder'] = '{}'

        #prep bluesky post data
        if 'bluesky' in postcheckmarks:
            if 'bshasimages' in postcheckmarks:
                imageslots = 0
                for fname in filenamelist:
                    if (imageslots < 4):
                        data.add('bsimgs', fname)
                        imageslots += 1

                remainingemptyfiles = 4 - imageslots
                for i in range(remainingemptyfiles):
                    data.add('bsimgs', 'none')

            data.add('bsskeetlen', '1')
            if not posttext:
                posttext = "Read more!"
            wordlimit = 290 - len(posttext) - len(bstags)
            bstextbody = posts[0].title + ': ' + summarysoup.getText()
            if len(bstextbody) > wordlimit:
                bstextbody = bstextbody[:wordlimit]
            bstextbody += "... "
            bstext = '[{"insert":"' + re.sub(r'([\"])', r'\\\1', bstextbody) + '"},'
            bstext += '{"attributes":{"link":"' + posts[0].link + '"},"insert":"' + re.sub(r'([\"])', r'\\\1', posttext) + '"},'
            bstext += '{"insert":" ' + bstags + '\\n"}]'
            data.add('bstext1', bstext)

        #prep tumblr data
        if 'tumblr' in postcheckmarks:
            hasphotos = 'tbhasimages' in postcheckmarks
            htmltotumblrpost(soup.body,data,files.getlist('imgupload'),hasphotos,link = posts[0].link)
        
        #prep data
        data['title'] = posts[0].title
        data['scheduledate'] = publishdate.strftime("%Y-%m-%d")
        data['time'] = publishdate.strftime("%H:%M")
        data['cycledate'] = cycledate.strftime("%Y-%m-%d")
        data['tags'] = tbtags
        data['blogname'] = blogname

        #add checks
        for postcheckmark in postcheckmarks:
            data[postcheckmark] = postcheckmark

        #send to create post
        postprocessor.processform(data, files, watcher.user_id)

        #update watcher
        if postprocessor.success:
            watcher.lastupdate = posts[0].published
            watcher.status = "Good"
            watcher.running = True
        else:
            watcher.status = "Error"
            watcher.running = False

        db.session.commit()
    return watcher.running

def watcheryoutube(watcher:Watcher):
    # url of youtube feed
    feed_url = watcher.url
    lastupdate = watcher.lastupdate
    postcheckmarks = watcher.postcheckmarks
    posttext = watcher.posttext
    tbtags = watcher.tbtags
    bstags = watcher.bstags
    blogname = watcher.blogname
    #cycledelta is a list of time ---> days, weeks
    cycledelta = [int(watcher.cycledelta["days"]), int(watcher.cycledelta["weeks"])]

    files = MultiDict() #This should remain empty

    #setting publish time
    publishdate = datetime.datetime.now() + timedelta(hours=5)
    cycledate = datetime.datetime.now() + timedelta(weeks=1)
    if 'cycle' in postcheckmarks:
        cycledate = datetime.datetime.now() + timedelta(days=cycledelta[0],weeks=cycledelta[1])

    lastpublishdatetime = datetime.datetime.min.replace(tzinfo=ZoneInfo("UTC"))
    if lastupdate:
        lastpublishdatetime = datetime.datetime.strptime(lastupdate, "%Y-%m-%dT%H:%M:%S%z")


    blog_feed = feedparser.parse(feed_url)
    posts = blog_feed.entries
    for post in posts:
        publishdatetime = datetime.datetime.strptime(post.published, "%Y-%m-%dT%H:%M:%S%z")
        if publishdatetime > lastpublishdatetime:
            data = MultiDict()
            newtags = generatetags(post.title + ' ' + post.summary)
            data['title'] = post.title
            data['scheduledate'] = publishdate.strftime("%Y-%m-%d")
            data['time'] = publishdate.strftime("%H:%M")
            data['cycledate'] = cycledate.strftime("%Y-%m-%d")
            if newtags:
                data['tags'] = newtags + ',' + tbtags
            else:
                data['tags'] = tbtags
            data['blogname'] = blogname
            data['fileorder'] = '{}'
            #add checks
            for postcheckmark in postcheckmarks:
                data[postcheckmark] = postcheckmark
            
            #prep bluesky post data
            if 'bluesky' in postcheckmarks:
                data.add('bsskeetlen', '1')
                newbstags = '#' + newtags.replace(',',' #')
                bstext = '[{"attributes":{"link":"' + post.link + '"},"insert":"' + re.sub(r'([\"])', r'\\\1', post.title) + '"},{"insert":" '
                if posttext:
                    bstext += posttext + ' '
                if newtags:
                    bstext += newbstags + ' ' + bstags + '\\n"}]'
                else:
                    bstext += bstags + '\\n"}]'
                data.add('bstext1', bstext)

            #prep tumblr post data
            if 'tumblr' in postcheckmarks:
                data.add('tbtype', 'video:1')
                data.add('tbtype', 'text:2')
                data.add('tbvideo1url', post.link)
                embedcode = '<iframe width="560" height="315" '
                embedcode += 'src="https://www.youtube.com/embed/' + post.yt_videoid +'" title="YouTube video player" '
                embedcode += 'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; '
                embedcode += 'picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'
                data.add('tbvideo1embed', embedcode)
                tbtext = '[{"insert":"' + re.sub(r'([\"])', r'\\\1', post.title) + '"},{"attributes":{"header":1},"insert":"\\n"}'
                if posttext:
                    tbtext += ',{"insert":"\\n' + posttext + '\\n"}'
                tbtext += ']'
                data.add('tbtext2', tbtext)

             #send to create post
            postprocessor = Processpost(watcher_request=True)
            postprocessor.processform(data, files, watcher.user_id)

            publishdate = publishdate + timedelta(days=7)

    if posts:
        #update watcher
        if postprocessor.success:
            watcher.lastupdate = posts[0].published
            watcher.status = "Good"
            watcher.running = True
        else:
            watcher.status = "Error"
            watcher.running = False

        db.session.commit()
    return watcher.running

def watchercomic(watcher:Watcher):
    ua = ua_generator.generate()
    
    URL = watcher.url
    searchkeys = watcher.searchkeys
    titleprefix = watcher.titleprefix
    titlekey = watcher.titlekey
    updatekey = watcher.updatekey
    lastupdate = watcher.lastupdate
    slugkey = watcher.slugkey
    archival = watcher.archival
    nextkey = watcher.nextkey
    prevkey= watcher.prevkey
    pagesperupdate = watcher.pagesperupdate
    posttext = watcher.posttext

    postcheckmarks = watcher.postcheckmarks
    tbtags = watcher.tbtags
    bstags = watcher.bstags
    blogname = watcher.blogname
    #cycledelta is a list of time ---> days, weeks
    cycledelta = [int(watcher.cycledelta["days"]), int(watcher.cycledelta["weeks"])]

    #variables exclusive to function
    fileorder = {}
    fileindex = 0
    filenamelist = []
    data = MultiDict()
    files = MultiDict()
    prevpages = []
    nextpages = []
    firsturl = URL
    lasturl = URL

    #get page content
    r = requests.get(url=URL,headers=ua.headers.get())
    soup = BeautifulSoup(r.content, 'html5lib')

    #check if you should run task
    updateattr = updatekey.split(':')
    updatetext = getelement(updatekey, soup).get_text()
    if updatetext != lastupdate:
        postprocessor = Processpost(watcher_request=True)
        #check for extra pages
        if archival:
            nextattr = nextkey.split(':')
            nextdiv = soup.find(nextattr[0], attrs = {nextattr[1]:nextattr[2]} )
            lasturl, nextpages, updatetext = getnextpages(URL,nextdiv,nextattr,updatetext,updateattr,pagesperupdate)
        else:
            if lastupdate:
                prevattr = prevkey.split(':')
                prevdiv = soup.find(prevattr[0], attrs = {prevattr[1]:prevattr[2]} )
                firsturl, prevpages = getprevpages(URL,updatetext,prevdiv,prevattr,lastupdate,updateattr)

        #setting publish time
        publishdate = datetime.datetime.now() + timedelta(hours=5)
        cycledate = datetime.datetime.now() + timedelta(weeks=1)
        if 'cycle' in postcheckmarks:
            cycledate = datetime.datetime.now() + timedelta(days=cycledelta[0],weeks=cycledelta[1])

        #get slug if needed
        slug = ''
        if slugkey:
            slug = getelement(slugkey, soup).getText()
        #prep source link for posts
        sourcelink = URL + slug
        if prevpages:
            sourcelink = firsturl

        #title
        title = titleprefix
        if titlekey == 'slug':
            if prevpages or nextpages:
                title = titleprefix + ': ' + getslug(firsturl) + ' - ' + getslug(lasturl)
            else:
                title = titleprefix + ': ' + getslug(URL)
        else:
            firstpage = getelement(titlekey, soup).get_text()
            lastpage = ''
            if prevpages:
                lastpage = ' - ' + firstpage
                firstpage = getelement(titlekey, prevpages[-1]).get_text()

            if nextpages:
                lastpage = ' - ' + getelement(titlekey, nextpages[-1]).get_text()

            title = titleprefix + ': ' + firstpage  + lastpage

        title = re.sub(r'([\"])', r'\\\1', title)

        #find image
        if 'images' in postcheckmarks:
            imgs = []
            previmgs = []
            for prevpage in prevpages:
                previmgs = previmgs + getimages(searchkeys,prevpage)
            if previmgs:
                imgs = list(reversed(previmgs))
            imgs = imgs + getimages(searchkeys,soup)
            for nextpage in nextpages:
                imgs = imgs + getimages(searchkeys,nextpage)

            if imgs:
                for img in imgs:
                    #add to file list
                    url_parsed = urlparse(img['src'])
                    filename = unquote(PurePosixPath(url_parsed.path).name)
                    if filename.startswith('https'):
                        splitpathname = filename.split('/')
                        filename = splitpathname.pop()
                    if postprocessor.allowed_file(filename):
                        file = WatcherFile(filename,img['src'])
                        files.add('imgupload', file)
                        #add to fileorder
                        fileorder[filename] = fileindex
                        filenamelist.append(filename)
                        fileindex += 1
                data['fileorder'] = json.dumps(fileorder)
            else: 
                postcheckmarks.remove('images')
                postcheckmarks.remove('bshasimages')
                postcheckmarks.remove('tbhasimages')
                data['fileorder'] = '{}'

        #prep bluesky post data
        if 'bluesky' in postcheckmarks:
            bsskeetlen = 1
            if 'bshasimages' in postcheckmarks:
                bsskeetlen = int(math.ceil(len(filenamelist)/4.0))
                totalfileslots = bsskeetlen * 4
                for fname in filenamelist:
                    data.add('bsimgs', fname) 

                remainingemptyfiles = totalfileslots - len(filenamelist)
                for i in range(remainingemptyfiles):
                    data.add('bsimgs', 'none')

            data.add('bsskeetlen', str(bsskeetlen))
            for i in range(bsskeetlen):
                bstextkey = 'bstext' + str(i + 1)
                txtpart = ''
                if (bsskeetlen > 1):
                    txtpart = ' (pt ' + str(i + 1) + ') '
                bstext = '[{"attributes":{"link":"' + sourcelink + '"},"insert":"' + title + txtpart + '"},'
                if posttext:
                    bstext += '{"insert":"\\n' + posttext + '\\n"},'
                bstext += '{"insert":" ' + bstags + '\\n"}]'
                data.add(bstextkey, bstext)

        #prep tumblr post data
        if 'tumblr' in postcheckmarks:
            tbindex = 1
            if 'tbhasimages' in postcheckmarks:
                data.add('tbtype', 'photo:1')
                tbindex += 1
                tbimgkey = 'imgcheckbox1'
                for fname in filenamelist:
                    data.add(tbimgkey, fname)

            data.add('tbtype', 'text:' + str(tbindex))
            tbtext = '[{"insert":"' + title + '"},{"attributes":{"header":1},"insert":"\\n"},'
            if posttext:
                tbtext += '{"insert":"\\n' + posttext + '\\n"},'
            tbtext += '{"insert":"\\n(Source: ' + sourcelink + ')\\n"}]'
            data.add('tbtext' + str(tbindex), tbtext)


        #prep data
        data['title'] = title
        data['scheduledate'] = publishdate.strftime("%Y-%m-%d")
        data['time'] = publishdate.strftime("%H:%M")
        data['cycledate'] = cycledate.strftime("%Y-%m-%d")
        data['tags'] = tbtags
        data['blogname'] = blogname

        #add checks
        for postcheckmark in postcheckmarks:
            data[postcheckmark] = postcheckmark

        #send to create post
        postprocessor.processform(data, files, watcher.user_id)

        #update watcher
        if postprocessor.success:
            watcher.lastupdate = updatetext
            watcher.status = "Good"
            watcher.running = True
            if archival:
                tempsoup = soup
                if nextpages:
                    tempsoup = nextpages[-1]
                nextdiv = getelement(nextkey, tempsoup)
                if nextdiv:
                    url_prefix = ''
                    if "http" not in nextdiv['href']:
                        url_parsed = urlparse(URL)
                        url_prefix = url_parsed.scheme + '://' + url_parsed.netloc

                    watcher.url = url_prefix + nextdiv['href']
                else:
                    #cancel the watcher and turn off!
                    watcher.status = "Paused"
                    watcher.running = False
        else:
            watcher.status = "Error"
            watcher.running = False

        db.session.commit()

    return watcher.running

def getslug(fullurl):
    url_parsed = urlparse(fullurl)
    slugname = unquote(PurePosixPath(url_parsed.path).name)
    return slugname

def getelement(key, soup):
    keyattr = key.split(':')
    return soup.find(keyattr[0], attrs = {keyattr[1]:keyattr[2]} )

def getprevpages(URL,updatetext,prevdiv,prevattr,lastupdate,updateattr):
    ua = ua_generator.generate()
    url_prefix = ''
    if prevattr[1] == 'rel':
        url_parsed = urlparse(URL)
        url_prefix = url_parsed.scheme + '://' + url_parsed.netloc
    firsturl = URL
    prevpages = []
    pagesperupdate = 10
    if not prevdiv:
        updatetext = lastupdate
    while updatetext != lastupdate or pagesperupdate > 1:
        tempurl = prevdiv['href']
        r = requests.get(url=url_prefix + tempurl,headers=ua.headers.get())
        tempsoup = BeautifulSoup(r.content, 'html5lib')
        updatetext = tempsoup.find(updateattr[0], attrs = {updateattr[1]:updateattr[2]}).get_text()
        prevdiv = tempsoup.find(prevattr[0], attrs = {prevattr[1]:prevattr[2]} )
        if not prevdiv:
            updatetext = lastupdate
        if updatetext != lastupdate or pagesperupdate > 1:
            firsturl = tempurl
            prevpages.append(tempsoup)
        pagesperupdate = pagesperupdate - 1
        if pagesperupdate <= 0:
            updatetext = lastupdate
    return (firsturl,prevpages)

def getnextpages(URL,nextdiv,nextattr,currentupdate,updateattr,pagesperupdate):
    ua = ua_generator.generate()
    url_prefix = ''
    if nextattr[1] == 'rel':
        url_parsed = urlparse(URL)
        url_prefix = url_parsed.scheme + '://' + url_parsed.netloc
    lasturl = URL
    nextpages = []
    updatetext = currentupdate
    lastupdate = currentupdate
    if not nextdiv:
        updatetext = 'none'
        pagesperupdate = 0
    while updatetext == currentupdate or pagesperupdate > 1:
        tempurl = nextdiv['href']
        r = requests.get(url=url_prefix + tempurl,headers=ua.headers.get())
        tempsoup = BeautifulSoup(r.content, 'html5lib')
        updatetext = tempsoup.find(updateattr[0], attrs = {updateattr[1]:updateattr[2]}).get_text()
        nextdiv = tempsoup.find(nextattr[0], attrs = {nextattr[1]:nextattr[2]} )
        if not nextdiv:
            updatetext = 'none'
            pagesperupdate = 0
        if updatetext == currentupdate or pagesperupdate > 1:
            lasturl = tempurl
            lastupdate = updatetext
            nextpages.append(tempsoup)
        pagesperupdate = pagesperupdate - 1
        if pagesperupdate <= 0:
            updatetext = 'none'
    return (lasturl,nextpages,lastupdate)

def getimages(searchkeys,soup):
    imgs = []
    for searchkey in searchkeys:
        if not imgs:
            divattr = searchkey.split(':')
            if divattr[0] != 'img':
                imgdivs = soup.findAll(divattr[0], attrs = {divattr[1]:divattr[2]})
                for imgdiv in imgdivs:
                    divimgs = imgdiv.findAll('img')
                    imgs = imgs + divimgs
            else:
                imgs = soup.findAll(divattr[0], attrs = {divattr[1]:divattr[2]})

    return imgs

def generatetags(searchtext):
    tags = ''
    searchtext = searchtext.lower()
    regex = r'#(\w+)'
    hashtag_list = re.findall(regex, searchtext)
    for hashtag in hashtag_list:
        tags += hashtag + ','
    
    if hashtag_list:
        tags = tags[:-1]
    return tags

class WatcherFile:
  def __init__(self, filename, url):
    self.filename = filename
    self.url = url

def htmltotumblrpost(soup,data,files,hasphotos,index = 0,wordlimit = MAXINT, posttext = "Read more!", link = '', linksenabled = True):
    text = '['
    headertxt = ''
    listtxt = ''
    listsize = 0
    openattribute = ''
    tbtype = ''
    wholetext = ''
    tumblrlimit = 4096
    attribute = ''
    blocktext = ''
    for el in soup.descendants:
        wholetextlen = len(wholetext)
        if wholetextlen < wordlimit:
            tagtype = el.name
            match tagtype:
                case "img":
                    if hasphotos:
                        if tbtype != "photo":
                            if tbtype == "text" and len(text) > 1:
                                blocktext = ''
                                text = text[:-1] + ']'
                                data.add('tbtext' + str(index), text)
                                text = '['
                            tbtype = "photo"
                            index += 1
                            data.add('tbtype', 'photo:' + str(index))
                        tbimgkey = 'imgcheckbox' + str(index)
                        for file in files:
                            if file.url == el['src']:
                                data.add(tbimgkey, file.filename)
                case None:                    
                    inserttxt = el.getText()
                    inserttxt = re.sub(r'([\n])', r'\\n', inserttxt)
                    overblocklimit = len(blocktext + inserttxt) > tumblrlimit and len(text) > 1
                    if overblocklimit:
                        text = text[:-1] + ']'
                        data.add('tbtext' + str(index), text)
                        text = '['
                    if overblocklimit or tbtype != "text":
                        blocktext = ''
                        tbtype = "text"
                        index += 1
                        data.add('tbtype', 'text:' + str(index))

                    if openattribute == 'li':
                        text += listtxt
                    text += attribute
                    if attribute:
                        text += '},'
                    wholetext += inserttxt
                    blocktext += inserttxt
                    if not attribute and (not openattribute or openattribute == 'h'):
                        text += '{'


                    text += '"insert":"' + re.sub(r'([\"])', r'\\\1', inserttxt)
                    if openattribute and headertxt:
                        text += '"},' + headertxt + '"insert":"\\n"},'
                    else:
                        text += '"},'

                    headertxt = ''
                    attribute = ''
                    openattribute = ''

                case "b" | "strong":
                    if 'bold' not in attribute:
                        if attribute:
                            attribute += ',"bold":true'
                        else:
                            attribute += '{"attributes":{"bold":true'
                    openattribute = 'b'
                case "i" | "em":
                    if 'italic' not in attribute:
                        if attribute:
                            attribute += ',"italic":true'
                        else:
                            attribute += '{"attributes":{"italic":true'
                    openattribute = 'i'
                case "del":
                    if 'strike' not in attribute:
                        if attribute:
                            attribute += ',"strike":true'
                        else:
                            attribute += '{"attributes":{"strike":true'
                    openattribute = 'del'
                case "ins":
                    if 'underline' not in attribute:
                        if attribute:
                            attribute += ',"underline":true'
                        else:
                            attribute += '{"attributes":{"underline":true'
                    openattribute = 'ins'
                case "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "h7":
                    headertype = '2'
                    if tagtype == "h1":
                        headertype = '1'
                    if blocktext:
                        if blocktext[-3:] != '\\n':
                            text += '{"insert":"\\n"},'
                    headertxt = '{"attributes":{"header":' + headertype + '},'
                    openattribute = 'h'
                case "ul":
                    listtxt = '{"attributes":{"list":"bullet"},"insert":"\\n"},{'
                case "ol":
                    listtxt = '{"attributes":{"list":"ordered"},"insert":"\\n"},{'
                case "li":
                    openattribute = 'li'
                case "a":
                    if el.getText():
                        if linksenabled and 'link' not in attribute:
                            if attribute:
                                attribute += ',"link":"' + el['href'] + '"'
                            else:
                                attribute += '{"attributes":{"link":"' + el['href'] + '"'
                            openattribute = 'a'
                        else:
                            text += '{"insert":" (' + el['href'] + ') "},'
                            openattribute = ''
                case "br":
                    text += '{"insert":"\\n"},'
                    openattribute = ''
                case "p":
                    if blocktext:
                        if blocktext[-3:] != '\\n':
                            text += '{"insert":"\\n"},'
                    openattribute = ''
                case _:
                    pass
    if len(text) > 1:
        text = text[:-1] + ']'
        data.add('tbtext' + str(index), text)
    if wordlimit != MAXINT:
        index += 1
        data.add('tbtype', 'text:' + str(index))
        if linksenabled:
            text = '[{"attributes":{"link":"' + link + '"},"insert":"' + posttext + '"}]'
        else:
            text = '[{"insert":"' + posttext + ' (Source: ' + link +')\\n"}]'
        data.add('tbtext' + str(index), text)

    return