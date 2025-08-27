from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('user')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                current_app.logger.info('%s logged in successfully', user.username)
                return redirect(url_for('views.home'))
            else:
                current_app.logger.info('%s failed to log in', user.username)
                flash('Incorrect password, try again.', category='error')
        else:
            flash('User does not exist.', category='error')
            current_app.logger.info('%s failed to log in', username)

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    current_app.logger.info('%s logged out successfully', current_user)
    return redirect(url_for('auth.login'))

@auth.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        oldpassword1 = request.form.get('oldpassword1')
        oldpassword2 = request.form.get('oldpassword2')
        newpassword = request.form.get('newpassword')
        
        if len(oldpassword1) == 0:
            flash('Must provide old password.', category='error')
        elif len(oldpassword2) == 0:
            flash('Must confirm old password.', category='error')
        elif oldpassword1 != oldpassword2:
            flash('Passwords don\'t match.', category='error')
        elif len(newpassword) < 7:
            flash('New password must be at least 7 characters.', category='error')
        elif oldpassword1 == newpassword:
            flash('New password cannot be the old password', category='error')
        elif not check_password_hash(current_user.password, oldpassword1):
            flash('Old password is incorrect', category='error')
        else:
            current_user.password = generate_password_hash(newpassword, method='pbkdf2:sha256')
            db.session.commit()
            flash('Password updated!', category='success')

    return render_template("settings.html", user=current_user)