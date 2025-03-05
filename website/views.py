from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

views = Blueprint('views', __name__)

@views.route('/')
@login_required
def home():
    return render_template("home.html", user=current_user)

@views.route('/addpost', methods=['GET', 'POST'])
@login_required
def addpost():
    if request.method == 'POST':
        data = request.files
        print(data)
    return render_template("addpost.html", user=current_user)

@views.route('/posts', methods=['GET', 'POST'])
@login_required
def posts():
    if request.method == 'POST':
        data = request.files
        print(data)
    return render_template("posts.html", user=current_user)

@views.route('/watchers', methods=['GET', 'POST'])
@login_required
def watchers():
    if request.method == 'POST':
        data = request.files
        print(data)
    return render_template("watchers.html", user=current_user)

@views.route('/queue', methods=['GET', 'POST'])
@login_required
def queuepage():
    if request.method == 'POST':
        data = request.files
        print(data)
    return render_template("queue.html", user=current_user)