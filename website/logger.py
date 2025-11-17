import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener, SMTPHandler
import queue
import threading
import time

#code from https://medium.com/@haroonayaz/centralized-logging-system-in-flask-the-backbone-of-multithreaded-python-applications-in-depth-7bfc45aae1b3

# Set up the logging queue
log_queue = queue.Queue()

def setup_logging(app):
    import os
    # Create the logger
    logger = app.logger
    logger.setLevel(logging.DEBUG)

    # Set the base directory and log path
    basedir = os.path.abspath(os.path.dirname(__file__))
    log_dir = os.path.join(basedir, 'Logs')
    log_file = os.path.join(log_dir, 'app.log')

    # Ensure log directory exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Set up RotatingFileHandler and log formatter 
    file_handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=5, delay=True)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Email handler: https://flask.palletsprojects.com/en/stable/logging/#email-errors-to-admins
    mail_handler = SMTPHandler(
    mailhost='127.0.0.1',
    fromaddr=os.getenv("SS_SERVER_EMAIL"),
    toaddrs=[os.getenv("SS_EMAIL")],
    subject='Social Sprite Error'
)
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(formatter)

    if not app.debug:
        logger.addHandler(mail_handler)

    # Create the QueueHandler and add it to the logger
    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    # Create the QueueListener
    listener = QueueListener(log_queue, file_handler)
    
    # Function to run the logging listener in a separate thread
    def start_logging_listener():
        listener.start()
        while True:
            # Avoid busy waiting 
            time.sleep(10)

    # Return the listener thread to be started in the main server file
    logging_thread = threading.Thread(target=start_logging_listener, daemon=True, name="Logger Thread")
    return logging_thread