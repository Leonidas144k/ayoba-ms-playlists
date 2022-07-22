import json
import mimetypes
from textwrap import wrap
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
import jwt
import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from prometheus_flask_exporter import PrometheusMetrics
from functools import wraps


# ##############################################################################
# GET VIDEO IDS FROM YOUTUBE
# ##############################################################################
def video_url_creator(id_lst):
    videos = []
    for vid_id in id_lst:
        video = 'https://youtube.com/embed/' + vid_id
        videos.append(video)
    return videos

# ##############################################################################
# INSTANTIATE FLASK
# ##############################################################################
app = Flask(__name__)
metrics = PrometheusMetrics(app)

host = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/AyobaPlaylist')
client = MongoClient(host = f'{host}?retryWrites=false')
db = client.get_default_database()
playlists = db.playlists


app.config['SECRET_KEY'] = 'f4f1e2f8-267d-46c6-a468-ff7700555b81'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'message' : 'Token Missing!'}), 403
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
        except:
            return jsonify({'message' : 'Token Invalid!'}), 403
        return f(*args, **kwargs)

    return decorated

@app.route('/protected')
@token_required
def protected():
    return jsonify({'message' : 'Only for valid tokens'})

@app.route('/login')
def login():
    auth = request.authorization

    if auth and auth.password == 'password':
        token = jwt.encode({'user':auth.username, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
        return jsonify({'token':token})

    return make_response('Could not Verify', 401, {'WWW-Authenticate':'Basic realm="Login Required"'})


# ##############################################################################
# INDEX
# ##############################################################################
@app.route('/')
def playlists_index():
    return render_template('playlists_index.html', playlists=playlists.find())


# ##############################################################################
# CREATE A PLAYLIST
# ##############################################################################
@app.route('/playlists/new') 
def playlists_new(): 
    return render_template('playlists_new.html', playlist = {}, title = 'New Playlist')


# ##############################################################################
# SUBMIT A PLAYLIST
# ##############################################################################
@app.route('/playlists', methods=['POST'])
def playlists_submit():
    video_ids = request.form.get('video_ids').split()
    videos = video_url_creator(video_ids)
    playlist = {
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'videos': videos,
        'video_ids': video_ids
    }
    playlists.insert_one(playlist)
    return redirect(url_for('playlists_index'))


# ##############################################################################
# SHOW PLAYLIST
# ##############################################################################
@app.route('/playlists/<playlist_id>')
def playlists_show(playlist_id):
    playlist = playlists.find_one({'_id': ObjectId(playlist_id)})
    return render_template('playlists_show.html', playlist=playlist)


# ##############################################################################
# EDIT PLAYLIST
# ##############################################################################
@app.route('/playlists/<playlist_id>/edit')
def playlists_edit(playlist_id):
    playlist = playlists.find_one({'_id': ObjectId(playlist_id)})
    return render_template('playlists_edit.html', playlist=playlist, title='Edit Playlist')


# ##############################################################################
# UPDATE PLAYLIST
# ##############################################################################
@app.route('/playlists/<playlist_id>', methods=['POST'])
def playlists_update(playlist_id):
    video_ids = request.form.get('video_ids').split()
    videos = video_url_creator(video_ids)
    updated_playlist = {
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'videos': videos,
        'video_ids': video_ids
    }
    playlists.update_one(
        {'_id': ObjectId(playlist_id)},
        {'$set': updated_playlist})
    return redirect(url_for('playlists_show', playlist_id=playlist_id))


# ##############################################################################
# DELETE PLAYLIST
# ##############################################################################
@app.route('/playlists/<playlist_id>/delete', methods=['POST'])
def playlists_delete(playlist_id):
    playlists.delete_one({'_id': ObjectId(playlist_id)})
    return redirect(url_for('playlists_index'))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))