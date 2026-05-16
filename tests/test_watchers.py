import json
import pytest
from tests.test_add_edit_posts import validate_post
from website.models import Watcher, User
from website.watcher import watcher as _watcher

# ADDING WATCHERS
def test_add_regular_comic_watcher(authenticated_client, regular_comic_watcher):
    response = authenticated_client.post('/addwatcher', data=regular_comic_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_watcher(regular_comic_watcher)

def test_add_archival_comic_watcher(authenticated_client, archival_comic_watcher):
    response = authenticated_client.post('/addwatcher', data=archival_comic_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_watcher(archival_comic_watcher)

def test_add_blog_watcher(authenticated_client, blog_watcher):
    response = authenticated_client.post('/addwatcher', data=blog_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_watcher(blog_watcher)

def test_add_youtube_watcher(authenticated_client, youtube_watcher):
    response = authenticated_client.post('/addwatcher', data=youtube_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_watcher(youtube_watcher)

def test_add_twitch_watcher(authenticated_client, twitch_watcher):
    response = authenticated_client.post('/addwatcher', data=twitch_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    validate_watcher(twitch_watcher)

# EDITING WATCHERS
def test_edit_watcher(authenticated_client, regular_comic_watcher):
    response = authenticated_client.post('/addwatcher', data=regular_comic_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    watcher = Watcher.query.filter(Watcher.url == regular_comic_watcher['url']).first()
    url = '/editwatcher/' + str(watcher.id)
    response = authenticated_client.get(url, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode()
    assert regular_comic_watcher['url'] in html

# RUNNING WATCHERS
def test_run_regular_comic_watcher(authenticated_client, regular_comic_watcher):
    response = authenticated_client.post('/addwatcher', data=regular_comic_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    test_watcher = Watcher.query.filter(Watcher.url == regular_comic_watcher['url']).first()
    data = _watcher(test_watcher.id)
    validate_post(data)

def test_run_archival_comic_watcher(authenticated_client, archival_comic_watcher):
    response = authenticated_client.post('/addwatcher', data=archival_comic_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    test_watcher = Watcher.query.filter(Watcher.url == archival_comic_watcher['url']).first()
    data = _watcher(test_watcher.id)
    validate_post(data)

def test_run_blog_watcher(authenticated_client, blog_watcher):
    response = authenticated_client.post('/addwatcher', data=blog_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    test_watcher = Watcher.query.filter(Watcher.url == blog_watcher['url']).first()
    data = _watcher(test_watcher.id)
    validate_post(data)

def test_run_youtube_watcher(authenticated_client, youtube_watcher):
    response = authenticated_client.post('/addwatcher', data=youtube_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    test_watcher = Watcher.query.filter(Watcher.url == youtube_watcher['url']).first()
    data = _watcher(test_watcher.id)
    validate_post(data)

def test_run_twitch_watcher(authenticated_client, twitch_watcher):
    response = authenticated_client.post('/addwatcher', data=twitch_watcher, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully' in response.data
    test_watcher = Watcher.query.filter(Watcher.url == twitch_watcher['url']).first()
    data = _watcher(test_watcher.id)
    if data:
        validate_post(data)


def validate_watcher(sample_watcher):
    watcher = Watcher.query.filter(Watcher.url == sample_watcher['url']).first()
    assert watcher != None
    if watcher:
        assert watcher.url == sample_watcher['url']
        assert watcher.wtype == sample_watcher['wtype']
        assert watcher.posttext == sample_watcher['posttext']
        scheduledata = watcher.scheduledata
        postcheckmarks = watcher.postcheckmarks

        user = User.query.filter(User.username == "test_user").first()
        assert user != None
        assert user.id == watcher.user_id

        if 'repost' in sample_watcher:
            assert 'repost' in postcheckmarks
        if 'cycle' in sample_watcher:
            assert 'cycle' in postcheckmarks
            assert watcher.cycleweeks == sample_watcher['weeks']
        if 'images' in sample_watcher:
            assert 'images' in postcheckmarks
        if 'tumblr' in sample_watcher:
            assert 'tumblr' in postcheckmarks
            assert watcher.tbtags == sample_watcher['ttags']
            assert watcher.blogname == sample_watcher['blogname']
            if 'tbhasimages' in sample_watcher:
                assert 'tbhasimages' in postcheckmarks
        if 'bluesky' in sample_watcher:
            assert 'bluesky' in postcheckmarks
            assert watcher.bstags == sample_watcher['bstags']
            if 'bshasimages' in sample_watcher:
                assert 'bshasimages' in postcheckmarks

        assert scheduledata['month'] == str(sample_watcher['month'])
        assert scheduledata['day_of_month'] == str(sample_watcher['day_of_month'])
        day_of_week = sample_watcher.getlist('day_of_week')
        assert scheduledata['day_of_week'] == day_of_week
        assert scheduledata['hour'] == str(sample_watcher['hour'])
        assert scheduledata['minute'] == str(sample_watcher['minute'])
        assert watcher.status == "Good"
        assert watcher.running == True

        if sample_watcher['wtype'] == 'comic':
            searchkeys = ','.join(watcher.searchkeys)
            assert searchkeys == sample_watcher['searchkeys']
            assert watcher.titleprefix == sample_watcher['titleprefix']
            assert watcher.titlekey == sample_watcher['titlekey']
            assert watcher.updatekey == sample_watcher['updatekey']
            archival = ('archival' in sample_watcher)
            slugkey = ('slugkey' in sample_watcher)
            if slugkey:
                assert watcher.slugkey == sample_watcher['slugkey']
            assert watcher.archival == archival
            assert watcher.pagesperupdate == int(sample_watcher['pagenum'])
            assert watcher.nextkey == sample_watcher['nextkey']
            assert watcher.prevkey == sample_watcher['prevkey']
