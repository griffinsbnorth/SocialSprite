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