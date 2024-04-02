import requests
import urllib.parse
import os

from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, session, render_template

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

@app.route('/')
def index():
    return "Welcome to my Spotify app <a href='/login'>Host Login</a>"

@app.route('/login')
def login():
    # user subscription details, email address, private playlists, create public playlists
    scope = 'user-read-private user-read-email playlist-read-private playlist-modify-public playlist-modify-private' 

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

        return redirect('/createPlaylist')

@app.route('/createPlaylist', methods=('GET', 'POST'))
def get_playlists():
    if request.method == 'POST': # data from form
        if 'access_token' not in session:
            return redirect('/login')
    
        # check if access token is expired
        if datetime.now().timestamp() > session['expires_at']:
            return redirect('/refresh_token')
        
        # https://www.digitalocean.com/community/tutorials/how-to-use-web-forms-in-a-flask-application#step-1-displaying-messages
        playlistName = request.form['pname']
        numSongs = int(request.form['numSongs'])
        genres = request.form['genres']

        # Later on: Confirm genres entered exist, else ask user to retype
        # TODO: create new empty playlist with playlistname
        # get user's top tracks
        # filter top tracks by genres given
        # get recommendations based on top tracks
        return 

    ### GET: Playlist Page
    return render_template('index.html')
    '''headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(API_BASE_URL + "me/playlists", headers=headers)
    playlists = response.json()

    return jsonify(playlists)'''

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

        return redirect('/createPlaylist')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

