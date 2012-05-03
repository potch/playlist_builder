import commands
import re
import json

from flask import (abort, Flask, session, redirect, render_template,
                   request, url_for)
from rdio import Rdio
from settings import *


app = Flask(__name__)

users = {}

def get_user(u):
    if not u in users:
        user = rdio_req('findUser', {'vanityName': u, 'extras': 'username'})
        users[u] = user
    return users[u]


def require_login(f):
    def wrapped():
        if not 'user' in session:
            print "failed auth check"
            return redirect(url_for('index'))
        return f;
    return wrapped


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET'])
def login():
    args = request.args
    if 'token' in session and 'oauth_verifier' in args:
        verifier = request.args.get('oauth_verifier')
        rdio = Rdio((RDIO_CONSUMER_KEY, RDIO_CONSUMER_SECRET), session['token'])
        rdio.complete_authentication(verifier)
        session['token'] = rdio.token
        user = rdio.call('currentUser')['result']
        session['user'] = user['key']
        users[user['key']] = user
        username = rdio.call('currentUser', {'extras': 'username'})['result']['username']
        return redirect(url_for('playlists', username=username))
    rdio = Rdio((RDIO_CONSUMER_KEY, RDIO_CONSUMER_SECRET))
    auth_url = rdio.begin_authentication(SITE_URL + '/login')
    session['token'] = rdio.token
    return redirect(auth_url)


@require_login
@app.route('/<username>/playlists')
def playlists(username):
    user = get_user(username)
    if not user:
        abort(404)
    playlists = rdio_req("getPlaylists", {'user': user['key']})
    return render_template('playlists.html', user=user,
                           playlists=playlists)


@require_login
@app.route('/<username>/playlist/<playlist>')
def playlist(username, playlist):
    objs = rdio_req('get', {'keys': playlist, 'extras': 'tracks'})
    if playlist in objs:
        return render_template('playlist.html', playlist=objs[playlist])
    abort(404)


@require_login
@app.route('/playlist/<key>/build')
def playlist_build(key):
    user = get_user(session['user'])
    obj = request.args.get('item', None)
    view = request.args.get('view', 'artists')
    items = get_obj_listing(obj, view)
    return render_template('build.html', playlist=key, view=view,
                           items=items)


def get_obj_listing(obj, view):
    rdio = Rdio((RDIO_CONSUMER_KEY, RDIO_CONSUMER_SECRET), session['token'])
    user = session['user']
    if obj:
        req = rdio.call('get', {'keys':obj})
        res = req['result'][obj]
        if res['type'] == 'al':
            req = rdio.call('get', {'keys':','.join(res['trackKeys'])})
            res = req['result']
            tracks = res.values()
            return tracks

    if view == 'albums':
        req = rdio.call('getAlbumsInCollection', {'user': user})
        return req['result']

    if view == 'tracks':
        req = rdio.call('getTracksInCollection', {'user': user})
        return req['result']

    req = rdio.call('getArtistsInCollection', {'user': user})
    return req['result']


def rdio_req(method, args):
    rdio = Rdio((RDIO_CONSUMER_KEY, RDIO_CONSUMER_SECRET))
    req = rdio.call(method, args)
    return req['result']


@app.route('/get_listing')
def get_listing():
    return json.dumps({'foo':'bar'})


if __name__ == "__main__":
    app.debug = DEBUG
    app.secret_key = SECRET_KEY
    app.run()