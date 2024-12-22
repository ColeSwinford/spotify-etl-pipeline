import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import sqlite3
import os
import re

#################### Extract ####################
# Spotify API credentials
creds = open('credentials.txt', 'r')    # File containing Spotify API credentials (SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET)
lines = creds.readlines()
SPOTIPY_CLIENT_ID = lines[0].split(' ')[-1].split('\n')[0]
SPOTIPY_CLIENT_SECRET = lines[1].split(' ')[-1].split('\n')[0]
sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))
# Playlist
def extract_playlist(sp, playlist_id):
        while True:
            try:
                playlist = sp.playlist(playlist_id)
                return playlist
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 429:
                    retry_after = int(e.headers.get('Retry-After', 1))
                    print(f"Rate limited. Retrying after {retry_after} seconds.")
                    time.sleep(retry_after)
                else:
                    print(f"Failed to fetch playlist: {e}")
                    exit()

#################### Transform ####################
def transform_playlist_info(playlist):
    track_data = []
    tracks = playlist['tracks']['items']
    for item in tracks:
        track = item['track']
        if track is not None:
            track_info = {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'release_date': track['album']['release_date'],
                'duration_ms': track['duration_ms'],
                'popularity': track['popularity'],
                'explicit': track['explicit'],
                'external_urls': track['external_urls']['spotify'],
                'available_markets': track['available_markets']
            }
            track_data.append(track_info)
    return track_data

#################### Load ####################
def sanitize_name(playlist_name):
    sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '', playlist_name.replace(' ', '_'))
    return sanitized_name
def load_data_to_sqlite(track_data, playlist_name):
    name = sanitize_name(playlist_name)
    db_name = 'spotify_tracks-' + name + '.db'
    # Check if database already exists
    if os.path.exists(db_name):
        print(f"Database already exists: {db_name}")
        delete = input("Do you want to delete the existing database? (y/n): ")
        if delete == 'y':
            os.remove(db_name)
            print(f"Removed existing database: {db_name}")
        elif delete == 'n':
            print(f"Keeping existing database: {db_name}")
            print("Exiting...")
            exit()
    # Create sqlite3 database      
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    # Create table
    cursor.execute('''
        CREATE TABLE tracks (
            id TEXT PRIMARY KEY,
            name TEXT,
            artist TEXT,
            album TEXT,
            release_date TEXT,
            duration_ms INTEGER,
            popularity INTEGER,
            explicit BOOLEAN,
            external_urls TEXT,
            available_markets TEXT
        )
    ''')
    # Insert data
    for track in track_data:
        cursor.execute('''
            INSERT OR REPLACE INTO tracks (
                id, name, artist, album, release_date, duration_ms, popularity, explicit, external_urls, available_markets
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            track['id'], track['name'], track['artist'], track['album'], track['release_date'], track['duration_ms'], track['popularity'], track['explicit'], track['external_urls'], ','.join(track['available_markets'])
        ))
    conn.commit()
    conn.close()

#################### Main ####################
playlist_url = input("Enter the Spotify playlist URL (must not be by Spotify or private): ")
playlist_id = playlist_url.split('/')[-1].split('?')[0]
print(f"Extracting playlist with ID: {playlist_id}")
playlist = extract_playlist(sp, playlist_id)
playlist_name = playlist['name']
print(f"Playlist '{playlist_name}' extracted successfully.")
print("Transforming playlist data...")
track_data = transform_playlist_info(playlist)
print("Playlist data transformed successfully.")
print("Loading data into SQLite database...")
load_data_to_sqlite(track_data, playlist_name)
print("Data loaded into SQLite database successfully.")