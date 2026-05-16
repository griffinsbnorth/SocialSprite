import pytest
from config import TestingConfig
from tests.configtest import Testconfig
from website import create_app, db
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta
import json
import pytest
import pytz
from werkzeug.datastructures import MultiDict

from config import Config
from website.watcher import generateNpfFromText

@pytest.fixture(scope="session")
def app():
    import os
    db_fname = './instance/test_database.db'
    if os.path.exists(db_fname):
        os.unlink(db_fname)

    app = create_app("config.TestingConfig")
    ctx = app.app_context()
    ctx.push()
    yield app
    dir_path = TestingConfig.UPLOAD_FOLDER
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    db.session.rollback()
    db.session.remove()
    db.drop_all()
    db.engine.dispose()
        
    ctx.pop()
    if os.path.exists(db_fname):
            os.unlink(db_fname)    

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

@pytest.fixture()
def authenticated_client(client):
    client.post('/login', data={
        'user': 'test_user',
        'password': 'test_password'
    }, follow_redirects=True)
    return client

@pytest.fixture
def sample_image():
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

@pytest.fixture
def sample_post():
    testdata = MultiDict()
    tz = pytz.timezone(Config.TIMEZONE)
    publishdate = datetime.now(tz) + timedelta(days=1)
    testdata['title'] = "Test post no images"
    testdata['scheduledate'] = publishdate.strftime("%Y-%m-%d")
    testdata['time'] = publishdate.strftime("%H:%M")
    testdata['weeks'] = 3
    testdata['tags'] = "#test"
    testdata['blogname'] = "test"
    testdata['fileorder'] = '{}'
    testdata.add('bsskeetlen', '1')
    testdata.add('bstext1', '[{"insert":"Test test test \\n"}]')
    testdata.add('tbtype', 'text:1')
    tbtext = '[{"insert":"TEST"},{"attributes":{"header":1},"insert":"\\n"}]'
    testdata.add('tbtext1', tbtext)
    npf = generateNpfFromText(tbtext)
    testdata.add('npf1', str(npf))
    testdata['repost'] = 'repost'
    testdata['cycle'] = 'cycle'
    testdata['tumblr'] = 'tumblr'
    testdata['bluesky'] = 'bluesky'
    return testdata

@pytest.fixture
def sample_post_with_image(sample_post, sample_image):
    sample_post['title'] = "Test post with images"
    sample_post['images'] = 'images'
    sample_post['tbhasimages'] = 'tbhasimages'
    sample_post['bshasimages'] = 'bshasimages'
    filename = 'test.png'
    fileorder = {}
    fileorder[filename] = 0
    sample_post['fileorder'] = json.dumps(fileorder)
    file = (sample_image , filename)
    sample_post.add('imgupload', file)
    sample_post.add('tbtype', 'photo:2')
    sample_post.add('imgcheckbox2', filename)
    sample_post.add('bsimgs', filename)
    sample_post.add('bsimgs', 'none')
    sample_post.add('bsimgs', 'none')
    sample_post.add('bsimgs', 'none')

    return sample_post

@pytest.fixture
def bluesky_post(sample_post):
    new_sample_post = sample_post.deepcopy()
    new_sample_post['title'] = "Test post just bluesky"
    new_sample_post.pop('tumblr')
    new_sample_post.pop('tbtype')
    new_sample_post.pop('tbtext1')
    new_sample_post.pop('npf1')
    new_sample_post['tags'] = ''
    return new_sample_post

@pytest.fixture
def tumblr_post(sample_post):
    new_sample_post = sample_post.deepcopy()
    new_sample_post['title'] = "Test post just tumblr"
    new_sample_post.pop('bluesky')
    new_sample_post.pop('bstext1')
    return new_sample_post

@pytest.fixture
def base_watcher():
    testdata = MultiDict()
    testdata['month'] = 1
    testdata['day_of_month'] = 0
    testdata.add('day_of_week', '2')
    testdata.add('day_of_week', '4')
    testdata['hour'] = 1
    testdata['minute'] = 5
    testdata['repost'] = 'repost'
    testdata['cycle'] = 'cycle'
    testdata['weeks'] = 3
    testdata['images'] = 'images'
    testdata['tumblr'] = 'tumblr'
    testdata['bluesky'] = 'bluesky'
    testdata['tbhasimages'] = 'tbhasimages'
    testdata['bshasimages'] = 'bshasimages'
    testdata['blogname'] = 'test'
    testdata['bstags'] = '#test #testo'
    testdata['ttags'] = 'presto'
    testdata['posttext'] = 'test test testo'
    return testdata

@pytest.fixture
def regular_comic_watcher(base_watcher):
    base_watcher['wtype'] = 'comic'
    base_watcher['url'] = Testconfig.COMIC_URL
    base_watcher['searchkeys'] = Testconfig.SEARCH_KEYS
    base_watcher['titleprefix'] = 'Test Comic'
    base_watcher['titlekey'] = Testconfig.TITLE_KEY
    base_watcher['updatekey'] = Testconfig.UPDATE_KEY
    base_watcher['prevkey'] = Testconfig.PREV_KEY
    base_watcher['nextkey'] = Testconfig.NEXT_KEY
    base_watcher['slugkey'] = Testconfig.SLUG_KEY
    base_watcher['pagenum'] = '1'
    return base_watcher

@pytest.fixture
def archival_comic_watcher(regular_comic_watcher):
    new_watcher = regular_comic_watcher.deepcopy()
    new_watcher.pop('slugkey')
    new_watcher['url'] = Testconfig.ARCHIVAL_URL
    new_watcher['archival'] = 'archival'
    new_watcher['pagenum'] = '3'
    return new_watcher

@pytest.fixture
def twitch_watcher(base_watcher):
    new_watcher = base_watcher.deepcopy()
    new_watcher['wtype'] = 'twitch'
    new_watcher['url'] = Testconfig.TWITCH_URL
    new_watcher.pop('repost')
    new_watcher.pop('cycle')
    new_watcher.pop('images')
    return new_watcher

@pytest.fixture
def youtube_watcher(base_watcher):
    new_watcher = base_watcher.deepcopy()
    new_watcher['wtype'] = 'youtube'
    new_watcher['url'] = Testconfig.YOUTUBE_RSS
    new_watcher.pop('repost')
    new_watcher.pop('cycle')
    new_watcher.pop('images')
    return new_watcher

@pytest.fixture
def blog_watcher(base_watcher):
    base_watcher['wtype'] = 'blog'
    base_watcher['url'] = Testconfig.BLOG_RSS
    return base_watcher