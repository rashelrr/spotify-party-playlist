import requests
import urllib.parse
import os

from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, session, render_template, url_for

load_dotenv()

### Spotify API OAuth Tutorial from https://www.youtube.com/watch?v=olY_2MW4Eik
app = Flask(__name__)
app.secret_key = '8b31d560-c969-4dad-a27d-3fbcedae8d4f' # needed to use session

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

new_playlist_info = {}
host_userid = [""]
track_ids = []
recommended_tracks = []

@app.route('/')
def index():
    return "Welcome to my Spotify app! <a href='/login'>Login</a>"

@app.route('/login')
def login():
    # user subscription details, email address, private playlists, create public playlists
    scope = 'user-read-private user-read-email playlist-read-private playlist-modify-public playlist-modify-private user-top-read' 

    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True # keep this line for easier debugging, remove once project done
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    # below: login successful!
    # code: An authorization code that can be exchanged for an access token.
    if 'code' in request.args:
        # request for access token
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        # spotify api sends back access token, refresh token, and expires in data
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in'] # seconds

        return redirect('/playlist_host_form')

@app.route('/playlist_host_form/', methods=('GET', 'POST'))
def playlist_host_form():
    # POST: get data from form
    if request.method == 'POST':        
        # https://www.digitalocean.com/community/tutorials/how-to-use-web-forms-in-a-flask-application#step-1-displaying-messages
        new_playlist_info['playlist_name'] = request.form['playlistName']
        new_playlist_info['num_songs'] = int(request.form['numSongs'])
        new_playlist_info['genres'] = request.form['genres']

        # Later on: Confirm genres entered exist, else ask user to retype
        # or: choose multiple genres from a dropdown

        return redirect('/get_current_userid')

    # GET: Create Playlist Page
    return render_template('index.html')
    '''
    # originally code for getting user's (me) playlists from spotify api
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(API_BASE_URL + "me/playlists", headers=headers)
    playlists = response.json()

    return jsonify(playlists)'''

@app.route('/get_current_userid')
def get_current_userid():
    if 'access_token' not in session:
        return redirect('/login')
    
    # check if access token is expired
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + "me", headers=headers)
    resp_json = response.json()

    host_userid[0] = resp_json['id']

    return redirect('/create_playlist')

@app.route('/create_playlist')
def create_playlist():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    json = {
        'name': new_playlist_info['playlist_name'],
        'description': "New party playlist!",
        'public': True,
    }
    response = requests.post(API_BASE_URL + "users/" + host_userid[0] + "/playlists", headers=headers, json=json)
    resp_json = response.json()
    new_playlist_info['playlist_id'] = resp_json['id']

    return redirect('/get_host_top_tracks')

@app.route('/get_host_top_tracks')
def get_host_top_tracks():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    # limit: range 1-50
    params = {
        'limit': new_playlist_info['num_songs'] 
    }
    
    response = requests.get(API_BASE_URL + "me/top/tracks", headers=headers, params=params)
    resp_json = response.json()

    items = resp_json['items']
    for item in items:
        track_ids.append(item['id'])
    return redirect('/get_host_recs')
    
@app.route('/get_host_recs')
def get_host_recs():    
    # Get recommendations based on given top tracks
    ### to then filter these songs by genre: get artist's genre, and see if any of the genre filters match (if curr_genre_filter in artistGenres)
    
    for i in range(0, len(track_ids), 5):
        if 'access_token' not in session:
            return redirect('/login')

        if datetime.now().timestamp() > session['expires_at']:
            return redirect('/refresh_token')

        subsection_ids = track_ids[i : i + 5]
        headers = {
            'Authorization': f"Bearer {session['access_token']}",
        }
        params = {
            'seed_tracks': subsection_ids,
            'limit': 5
        }

        response = requests.get(API_BASE_URL + "recommendations", headers=headers, params=params)
        resp_json = response.json()
        tracks = resp_json['tracks']
        for track in tracks:
            recommended_tracks.append(track['uri']) 

    return redirect('/add_songs')

@app.route('/add_songs')
def add_songs():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    json = {
        'uris': recommended_tracks
    }

    response = requests.post(API_BASE_URL + "playlists/" + new_playlist_info['playlist_id'] + "/tracks", 
                             headers=headers, json=json)
    playlist_link = "https://open.spotify.com/playlist/" + new_playlist_info['playlist_id']
    msg = 'Your custom playlist is ready to listen to on Spotify! <a href="{}">Click here.</a>'.format(playlist_link)
    return msg


@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    # To refresh an access token, we must send a POST request 
    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()

        # update access_token and expires_at
        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/playlist_host_form')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

