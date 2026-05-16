import json
import pytest
from config import Config
from zoneinfo import ZoneInfo
from website.models import Post, Tumblrblock, Image as DBImage, Blueskyskeet, Postjob



# ADDING POSTS
def test_addpost_no_images(authenticated_client, sample_post):
    response = authenticated_client.post('/addpost', data=sample_post, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_post(sample_post)

def test_addpost_images(authenticated_client, sample_post_with_image):
    response = authenticated_client.post('/addpost', data=sample_post_with_image, content_type='multipart/form-data', buffered=True, follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_post(sample_post_with_image)

def test_addpost_just_bluesky(authenticated_client, bluesky_post):
    response = authenticated_client.post('/addpost', data=bluesky_post, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_post(bluesky_post)

def test_addpost_just_tumblr(authenticated_client, tumblr_post):
    response = authenticated_client.post('/addpost', data=tumblr_post, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_post(tumblr_post)

def test_addpost_incorrect(authenticated_client, sample_post):
    sample_post['title'] = "Incorrect post"
    sample_post['images'] = 'images'
    sample_post['tbhasimages'] = 'tbhasimages'
    sample_post['bshasimages'] = 'bshasimages'
    sample_post.add('tbtype', 'photo:2')

    response = authenticated_client.post('/addpost', data=sample_post, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' not in response.data

# EDITING POSTS
def test_editpost_no_images(authenticated_client, sample_post):
    response = authenticated_client.post('/addpost', data=sample_post, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    post = Post.query.filter(Post.title == sample_post["title"]).first()
    url = '/editpost/' + str(post.id)
    response = authenticated_client.get(url, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode()
    assert sample_post['title'] in html

def test_editpost_images(authenticated_client, sample_post_with_image):
    response = authenticated_client.post('/addpost', data=sample_post_with_image, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    post = Post.query.filter(Post.title == sample_post_with_image["title"]).first()
    url = '/editpost/' + str(post.id)
    response = authenticated_client.get(url, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode()
    assert sample_post_with_image['title'] in html


def validate_post(samplepost):
    post = Post.query.filter(Post.title == samplepost["title"]).first()
    assert post != None
    if post:
        assert post.title == samplepost['title']
        scheduledatetime = post.publishdate.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(Config.TIMEZONE))
        assert scheduledatetime.strftime('%Y-%m-%d') == samplepost['scheduledate']
        repost = ('repost' in samplepost)
        assert post.repost == repost
        dbpostjobs = Postjob.query.filter(Postjob.post_id == post.id, Postjob.published == False).all()
        if repost:
            assert len(dbpostjobs) == 3
        else:
            assert len(dbpostjobs) == 1
        cycle = ('cycle' in samplepost)
        assert post.cycle == cycle
        if cycle:
            assert post.cycleweeks == samplepost['weeks']
        containsimages = ('images' in samplepost)
        fortumblr = ('tumblr' in samplepost)
        forbluesky = ('bluesky' in samplepost)
        assert post.containsimages == containsimages
        assert post.fortumblr == fortumblr
        assert post.forbluesky == forbluesky
        assert ','.join(post.tumblrtags) == samplepost['tags']
        assert post.blogname == samplepost['blogname']
        images = DBImage.query.filter(DBImage.post_id == post.id).order_by(DBImage.order).all()
        if containsimages:
            assert images != None
            fileorder = {}
            for img in images:
                fileorder[img.url] = img.order
            assert samplepost['fileorder'] == json.dumps(fileorder)
        if fortumblr:
            tumblrblocklist = samplepost.getlist('tbtype')
            blocks = Tumblrblock.query.filter(Tumblrblock.post_id == post.id).order_by(Tumblrblock.order).all()
            assert len(tumblrblocklist) == len(blocks)
            for block in blocks:
                tbtype = block.blocktype + ":" + str(block.order)
                assert tbtype in tumblrblocklist
                match block.blocktype:
                    case 'photo':
                        tbimgs = samplepost.getlist('imgcheckbox' + str(block.order))
                        imageids = []
                        for tbimg in tbimgs:
                            for img in images:
                                if tbimg == img.url:
                                    imageids.append(img.id)
                        assert imageids == block.imageids
                    case 'text':
                        quillops = samplepost.get('tbtext' + str(block.order))
                        textops = json.loads(quillops,strict=False)
                        assert str(textops) == str(block.quillops)
                        textnpf = json.loads(samplepost.get('npf' + str(block.order)),strict=False)
                        assert str(textnpf) == str(block.npf)
                    case _:
                        prefix = 'tb' + block.blocktype + str(block.order)
                        url = samplepost.get(prefix + 'url')
                        embed = samplepost.get(prefix + 'embed')
                        if embed == None:
                            embed = ''
                        assert url == block.url
                        assert embed == block.embed
        if forbluesky:
            skeets = Blueskyskeet.query.filter(Blueskyskeet.post_id == post.id).order_by(Blueskyskeet.order).all()
            assert samplepost.get('bsskeetlen') == str(len(skeets))
            for skeet in skeets:
                quillops = samplepost.get('bstext' + str(skeet.order))
                textops = json.loads(quillops,strict=False)
                assert str(textops) == str(skeet.quillops)
                bsimgs = samplepost.getlist('bsimgs')
                imageids = []
                for bsimg in bsimgs:
                    for img in images:
                        if bsimg == img.url:
                            imageids.append(img.id)
                assert imageids == skeet.imageids