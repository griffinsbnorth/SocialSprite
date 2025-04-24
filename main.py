from website import create_app, sendpost

app = create_app()

def sendposts():
    with app.app_context():
        sendpost.sendposts()

if __name__ == '__main__':
    app.run()