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
        data = request.form
        print(data)

        title = request.form.get('title')
        scheduledate = request.form.get('scheduledate')
        time = request.form.get('time')
        if (time == ''):
            time = '00:00'
        print(time)
        repost = request.form.get('repost') != None
        cycle = request.form.get('cycle') != None
        images = request.form.get('images') != None
        tumblr = request.form.get('tumblr') != None
        bluesky = request.form.get('bluesky') != None



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