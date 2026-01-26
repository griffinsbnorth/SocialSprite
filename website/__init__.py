from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
import os
from werkzeug.security import generate_password_hash
from flask_login import LoginManager

db = SQLAlchemy()
scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.DevelopmentConfig")
    db.init_app(app)
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        scheduler.init_app(app)
        scheduler.add_listener(scheduler_listener, EVENT_JOB_MISSED | EVENT_JOB_ERROR)
        scheduler.start()

    from .views import views
    from .auth import auth
    from .misc import misc

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(misc, url_prefix='/')

    from .models import User, Post, Tumblrblock, Blueskyskeet, Image, Tag, Postjob, Watcher

    with app.app_context():
        db.create_all()
        users = User.query.all()
        if (len(users) == 0):
            new_user = User(username=os.getenv("SS_USERNAME"), password=generate_password_hash(os.getenv("SS_PASSWORD"), method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def scheduler_listener(event):
    if event.exception:
        scheduler.app.logger.error(event.traceback)
    else:
        scheduler.app.logger.error(f"Job {event.job_id} missed scheduled run time: {event.scheduled_run_time}")

    with scheduler.app.app_context():
        from .models import Postjob, Post
        dbpostjob = Postjob.query.get(event.job_id)
        if dbpostjob:
            dbpost = Post.query.get(dbpostjob.post_id)
            if dbpost:
                from .processpost import Processpost
                import datetime
                import pytz
                from datetime import timedelta
                from config import Config
                tz = pytz.timezone(Config.TIMEZONE)
                currenttime = datetime.datetime.now(tz)
                #only reschedule jobs if they haven't already been resheduled via the generate_post_jobs function
                if dbpost.publishdate < currenttime:
                    dbpost.publishdate = currenttime + timedelta(hours=1)
                    #generate postjobs
                    postprocessor = Processpost(dbpost.id)
                    postprocessor.generate_post_jobs(dbpost)
                    db.session.commit()
