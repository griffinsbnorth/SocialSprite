from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash
from flask_login import LoginManager

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.DevelopmentConfig")
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

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