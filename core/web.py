

from datetime import timedelta
import json
import time
import uuid
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
import redis
import waitress
from server import SystemReceiver
from util import Config, SYSTEM_IMAGES
import os


def get_remote_address():
    """Get the remote address from the request, falling back to X-Real-IP."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return request.remote_addr
    return request.headers.get("X-Real-IP", request.remote_addr)

def get_limiter_login_fail_key():
    """Get the Redis key for tracking login failures."""
    return f"login_fail:{get_remote_address()}"

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

LIMITER = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/0",
)

def login_backoff_limit():
    if LOCAL_DEBUG:
        return "100 per minute"
    
    fails = int(r.get(get_limiter_login_fail_key()) or 0)

    # tiered policy:
    #   0 fails → 5/min
    #   1 fail  → 3/min
    #   2+ fails → 1 per (2**(fails-1)) seconds, capped 300s
    if fails == 0:
        return "5 per minute"
    if fails == 1:
        return "3 per minute"

    window = min(2 ** (fails - 1), 300)  # seconds
    # Flask-Limiter time units are whole nouns; use "second" if window==1 else "seconds"
    unit = "second" if window == 1 else "seconds"
    return f"1 per {window} {unit}"

def frp_backoff_limit():
    ip = get_remote_address()
    fails = int(r.get(f"frp_fail:{ip}") or 0)
    if fails == 0:
        return "100 per minute"
    window = min(2 ** fails, 600)
    return f"20 per minute; 1 per {window} seconds"

LOCAL_DEBUG = False

class Dashboard:
    def __init__(self, config: Config, receiver: SystemReceiver, local_debug: bool = False):
        global LOCAL_DEBUG

        self.config = config
        self.receiver = receiver
        self.local_debug = local_debug
        LOCAL_DEBUG = local_debug

        self.USERNAME = config.dashboard_username
        self.PASSWORD = config.dashboard_password

        self.app = Flask("SysMon", template_folder='core/templates')
        self.app.config.update(
            APPLICATION_ROOT=config.dashboard_application_root,
            SECRET_KEY=uuid.uuid4().hex,
            WTF_CSRF_TIME_LIMIT=3600,
            SESSION_COOKIE_SECURE=not self.local_debug,       # only sent over HTTPS
            SESSION_COOKIE_HTTPONLY=True,     # JS can’t read
            SESSION_COOKIE_SAMESITE="Strict", # no cross-site requests
            PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        )
        self.app.jinja_env.globals["local_debug"] = local_debug



        self.app.errorhandler(404)(self.standard_error)
        self.app.errorhandler(405)(self.standard_error)

        self.app.add_url_rule('/', 'index', self.index)
        self.app.add_url_rule('/login', 'login', self.login, methods=['GET', 'POST'])
        self.app.add_url_rule('/logout', 'logout', self.logout)
        self.app.add_url_rule('/system_image/<name>', 'system_image', self.system_image)



    def run(self):
        print(f"Starting Flask server on {self.config.dashboard_host}:{self.config.dashboard_port}")
        waitress.serve(self.app, host=self.config.dashboard_host, port=self.config.dashboard_port)


    def standard_error(self, error):
        return render_template("status_code.jinja", status_code=404), 404
    


    @LIMITER.limit(login_backoff_limit)
    def login(self):
        if session.get('logged_in'):
            return redirect(self.app.config['APPLICATION_ROOT'] + url_for('index'))

        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if username == self.USERNAME and password == self.PASSWORD:
                if not self.local_debug:
                    r.delete(get_limiter_login_fail_key())
                session.clear()
                session.permanent = True
                session['logged_in'] = True
                return redirect(self.app.config['APPLICATION_ROOT'] + url_for('index'))
            else:
                if not self.local_debug:
                    pipe = r.pipeline()
                    key = get_limiter_login_fail_key()
                    pipe.incr(key)
                    pipe.expire(key, 900)  # reset after 15 minutes quiet
                    pipe.execute()

                flash('Invalid username or password', 'error')

        return render_template("login.jinja")

    def logout(self):
        session.pop('logged_in', None)
        flash('Logged out successfully', 'success')
        return redirect(self.app.config['APPLICATION_ROOT'] + url_for('login'))
    
    def system_image(self, name: str, status: str = "on") -> str:
        # images_dir = os.path.join(self.app.template_folder, 'system_images')
        # files = os.listdir(images_dir)
        # for file in files:
        #     if file.replace('.png', '').lower() == name.lower():
        #         return Response(
        #             open(os.path.join(images_dir, file), 'rb').read(),
        #             mimetype='image/png'
        #         )
            
        return SYSTEM_IMAGES.get(name, ["on", "off", "on"])

    def index(self):
        if not session.get('logged_in'):
            return redirect(self.app.config['APPLICATION_ROOT'] + url_for('login'))

        return render_template("index.jinja", 
                            #    proxy_map=self.nginx_manager.proxy_map, 
                            #    gateway_server_list=self.frp_manager.get_server_list(), 
                            #    gateway_client_list=self.frp_manager.get_client_list(), 
                            #    gateway_connection_list=self.frp_manager.get_connection_list(), 
                            #    domain=self.nginx_manager.domain, 
                                providers=self.receiver.db.providers,
                                application_root=self.app.config['APPLICATION_ROOT'])
