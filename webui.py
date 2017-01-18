import logging
import os
import re

import requests
from flask import Flask
from flask import render_template
from flask import request
from flask import send_from_directory
from flask_httpauth import HTTPBasicAuth

import config
import db

logger = logging.getLogger("WEB-UI")
logger.setLevel(logging.DEBUG)

app = Flask("sonarrAnnounced")
auth = HTTPBasicAuth()
cfg = config.init()


def run():
    app.run(debug=False, host=cfg['server.host'], port=int(cfg['server.port']), use_reloader=False)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


# panel routes
@auth.get_password
def get_pw(username):
    if not username == cfg['server.user']:
        return None
    else:
        return cfg['server.pass']
    return None


@app.route('/assets/<path:path>')
@auth.login_required
def send_asset(path):
    return send_from_directory("templates/assets/{}".format(os.path.dirname(path)), os.path.basename(path))


@app.route("/")
@auth.login_required
@db.db_session
def index():
    return render_template('index.html', snatched=db.Snatched.select().order_by(db.desc(db.Snatched.date)).limit(20),
                           announced=db.Announced.select().order_by(db.desc(db.Announced.date)).limit(20))


@app.route("/trackers", methods=['GET', 'POST'])
@auth.login_required
def trackers():
    if request.method == 'POST':
        if 'iptorrents_torrentpass' in request.form:
            cfg['iptorrents.torrent_pass'] = request.form['iptorrents_torrentpass']
            cfg['iptorrents.nick'] = request.form['iptorrents_nick']
            cfg['iptorrents.nick_pass'] = request.form['iptorrents_nickpassword']
            logger.debug("saved iptorrents settings")

        if 'morethan_torrentpass' in request.form:
            cfg['morethan.auth_key'] = request.form['morethan_authkey']
            cfg['morethan.torrent_pass'] = request.form['morethan_torrentpass']
            cfg['morethan.nick'] = request.form['morethan_nick']
            cfg['morethan.nick_pass'] = request.form['morethan_nickpassword']
            logger.debug("saved morethan settings")

        if 'btn_torrentpass' in request.form:
            cfg['btn.auth_key'] = request.form['btn_authkey']
            cfg['btn.torrent_pass'] = request.form['btn_torrentpass']
            cfg['btn.nick'] = request.form['btn_nick']
            cfg['btn.nick_pass'] = request.form['btn_nickpassword']
            logger.debug("saved btn settings")

        if 'ttn_torrentpass' in request.form:
            cfg['ttn.auth_key'] = request.form['ttn_authkey']
            cfg['ttn.torrent_pass'] = request.form['ttn_torrentpass']
            cfg['ttn.nick'] = request.form['ttn_nick']
            cfg['ttn.nick_pass'] = request.form['ttn_nickpassword']
            logger.debug("saved ttn settings")

        if 'freshon_torrentpass' in request.form:
            cfg['freshon.torrent_pass'] = request.form['freshon_torrentpass']
            cfg['freshon.nick'] = request.form['freshon_nick']
            cfg['freshon.nick_pass'] = request.form['freshon_nickpassword']
            logger.debug("saved freshon settings")

        cfg.sync()

    return render_template('trackers.html')


@app.route("/logs")
@auth.login_required
def logs():
    logs = []
    with open('status.log') as f:
        for line in f:
            log_parts = re.search('(^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s-\s(\S+)\s+-\s(.+)', line)
            if log_parts:
                logs.append({'time': log_parts.group(1),
                             'tag': log_parts.group(2),
                             'msg': log_parts.group(3)})

    return render_template('logs.html', logs=logs)


@app.route("/settings", methods=['GET', 'POST'])
@auth.login_required
def settings():
    if request.method == 'POST':
        cfg['server.host'] = request.form['server_host']
        cfg['server.port'] = request.form['server_port']
        cfg['server.user'] = request.form['server_user']
        cfg['server.pass'] = request.form['server_pass']

        cfg['sonarr.url'] = request.form['sonarr_url']
        cfg['sonarr.apikey'] = request.form['sonarr_apikey']

        if 'debug_file' in request.form:
            cfg['bot.debug_file'] = True
        else:
            cfg['bot.debug_file'] = False

        if 'debug_console' in request.form:
            cfg['bot.debug_console'] = True
        else:
            cfg['bot.debug_console'] = False

        cfg.sync()
        logger.debug("Saved settings: %s", request.form)

    return render_template('settings.html')


@app.route("/sonarr/check", methods=['POST'])
@auth.login_required
def check():
    try:
        data = request.json
        if 'apikey' in data and 'url' in data:
            # Check if api key is valid
            logger.debug("Checking whether apikey: %s is valid for: %s", data.get('apikey'), data.get('url'))

            headers = {'X-Api-Key': data.get('apikey')}
            resp = requests.get(url="{}/api/diskspace".format(data.get('url')), headers=headers).json()
            logger.debug("check response: %s", resp)

            if 'error' not in resp:
                return 'OK'

    except Exception as ex:
        logger.exception("Exception while checking sonarr apikey:")

    return 'ERR'


@app.context_processor
def inject_conf_in_all_templates():
    global cfg
    return dict(conf=cfg)
