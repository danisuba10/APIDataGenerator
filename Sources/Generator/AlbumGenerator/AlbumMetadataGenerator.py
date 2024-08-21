import requests
from Sources.Generator.SpotifyAPICredentials import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import random
import json
import os
import uuid

class JSONAlbumMetadaGenerator:
    def __init__(self) -> None:
        os.environ['SPOTIPY_CLIENT_ID'] = SPOTIPY_CLIENT_ID
        os.environ['SPOTIPY_CLIENT_SECRET'] = SPOTIPY_CLIENT_SECRET
        os.environ['SPOTIPY_REDIRECT_URI'] = SPOTIPY_REDIRECT_URI

        self.sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
        self.get_guid_api_url = "http://localhost:5231/api/Miscle/GetGUID"
        self.artist_image_path = f"C:\\Project Folder\\CSHARP\\Musify-o\\API\\Images\\Artists\\"
        self.album_image_path = f"C:\\Project Folder\\CSHARP\\Musify-o\\API\\Images\\Albums\\"


    def get_random_album(self):
        offset = random.randint(0, 1000)

        albums = self.sp.search(q="album", type="album", limit=1, offset=offset)['albums']['items']

        if albums:
            album = albums[0]
        else:
            album = None

        return self._generate_album_json(album)
    
    def _generate_album_json(self, album):
        album_artists = []
        for artist in album['artists']:

            artist_id = self.get_guid()

            artist_info = {
                "guid": artist_id,
                "name": artist['name'],
                "imgLocation": None
            }

            images = artist.get('images', [])
            if images:
                artist_image_url = images[0].get('url')
            else:
                artist_image_url = None

            if artist_image_url:
                self._download_image(artist_image_url, os.path.join(self.artist_image_path, f"{artist_id}.jpg"))

            album_artists.append(artist_info)
        album_songs = self._get_album_songs(album['id'])

        album_id = self.get_guid()

        album_json = {
            "guid": album_id,
            "name": album['name'],
            "imageLocation": None,
            "songs": album_songs,
            "artists": album_artists,
        }

        images = album.get('images', [])
        if images:
            album_image_url = images[0].get('url')
        else:
            album_image_url = None

        if album_image_url:
            self._download_image(album_image_url, os.path.join(self.album_image_path, f"{album_id}.jpg"))

        return album_json
    
    def _get_album_songs(self, album_id):
        songs = self.sp.album_tracks(album_id)['items']
        song_list = []
        for idx, song in enumerate(songs):
            song_artists = []
            
            for artist in song['artists']:
                artist_info = {
                "guid": None,
                "name": artist['name'],
                "imgLocation": None
                }
            song_artists.append(artist_info)

            song = {
                "title": song['name'],
                "duration": self._convert_duration(song['duration_ms']),
                "positionInAlbum": idx,
                "artists":song_artists
            }
            song_list.append(song)
        
        return song_list
    
    def _convert_duration(self, duration_ms):
        total_seconds = duration_ms // 1000
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    def generate_json(self):
        album = self.get_random_album()
        if album:
            return json.dumps(album, indent = 2)
        
        return None
    
    def get_guid(self):
        response = requests.get(self.get_guid_api_url, verify=False)
        if response.status_code == 200:
            id = response.text.strip().replace('"', '')
        else:
            id = uuid.uuid4()

        return id

    def _download_image(self, url, file_path):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
            else:
                print(f"Failed to download image from URL")
        except Exception as e:
            print(f"An error occured while downloading image {e}")
