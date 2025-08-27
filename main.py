from website import create_app
from website.logger import setup_logging

app = create_app()

if __name__ == '__main__':
    logging_thread = setup_logging(app)
    logging_thread.start()
    app.run()