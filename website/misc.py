from flask import jsonify, Blueprint
from flask_login import login_required
import threading
import os
import psutil

misc = Blueprint('misc', __name__)

def get_process_info():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    cpu_usage = process.cpu_percent(interval=1)
    return {
        "cpu_usage": cpu_usage,
        "memory_info": {
            "rss": f"{memory_info.rss / 1024 / 1024:.2f} MB",
            "vms": f"{memory_info.vms / 1024 / 1024:.2f} MB",
        }
    }

@misc.route('/threads')
@login_required
def list_threads():
    threads = threading.enumerate()
    thread_info = []
    for thread in threads:
        thread_info.append({
            'name': thread.name,
            'id': thread.ident,
            'daemon': thread.daemon
        })
    return jsonify(thread_info)

@misc.route('/monitoring')
@login_required
def memory_usage():
    return jsonify(get_process_info())