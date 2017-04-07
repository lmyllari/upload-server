# for worker processes
import gevent
from gevent import Greenlet
from gevent.queue import JoinableQueue, Empty
from gevent.event import Event
from gevent.subprocess import Popen, PIPE

# for gevent webserver
from gevent.pywsgi import WSGIServer

# for flask
from flask import Flask, jsonify, request, render_template, send_from_directory

def worker(queue, quit):
    count = 0
    while not quit.is_set():
        try:
            task = queue.get(timeout=1)
            task.set_state(TaskState.Processing)
            gevent.sleep(5)
            task.set_state(TaskState.Completed)
            queue.task_done()
            count += 1
        except Empty:
            pass
    print("worker shutdown, " + str(count) + " items processed")

class TaskState:
    Pending, Processing, Completed, Failed = range(4)

class Task:
    def __init__(self, name):
        self.name = name
        self.state = TaskState.Pending
        self.state_change = Event()
    def set_state(self, newstate):
        self.state = newstate
        self.state_change.set()
        gevent.sleep(0) # wake up anyone waiting
        self.state_change.clear()
    def get_state(self):
        return self.state
    def wait_for_state_change(self, timeout=None):
        return self.state_change.wait(timeout)

class TaskList:
    def __init__(self):
        self.queue = JoinableQueue
        self.all_tasks = {}
    def add_task(self, task):
        self.all_tasks[task.name] = task
        self.queue.put(task)

app = Flask(__name__)
PORT = 5000

@app.route("/")
def main():
    """
    Main web site entry point.
    """
    return "hello world"


if __name__=='__main__':
    worker_count = 4
    workers = []

    task_queue = JoinableQueue()
    tasks = {}

    quit_workers = Event()
    for i in range(worker_count):
        w = Greenlet.spawn(worker, task_queue, quit_workers)
        workers.append(w)

    http_server = WSGIServer(('', PORT), app)
    http_server.start()

    # loop until interrupted
    while True:
        try:
            gevent.sleep(5)
            task_queue.join()
        except (KeyboardInterrupt, SystemExit):
            break

    http_server.stop()

    quit_workers.set()
    for w in workers:
        w.join()