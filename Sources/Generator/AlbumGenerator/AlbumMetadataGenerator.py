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
        self.get_guid_artist_byname = "http://localhost:5231/api/Artist/GetArtistID"
        self.get_guid_album_byname = "http://localhost:5231/api/Album/GetAlbumID"
        self.artist_image_path = f"C:\\Project Folder\\CSHARP\\Musify-o\\API\\Images\\Artists\\"
        self.album_image_path = f"C:\\Project Folder\\CSHARP\\Musify-o\\API\\Images\\Albums\\"

        self.artist_id_to_guid = {}
        self.albums_id_to_guid = {}

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
            artist_id = artist['id']
            if artist_id in self.artist_id_to_guid:
                artist_guid = self.artist_id_to_guid[artist_id]
            else:
                artist_guid = self._get_or_create_artist_guid(artist['name'])
                self.artist_id_to_guid[artist_id] = artist_guid

                artist_details = self.sp.artist(artist['id'])
                images = artist_details.get('images', [])

                if images:
                    artist_image_url = images[0].get('url')
                else:
                    artist_image_url = None
                    print(f"No image found for artist: {artist['name']} (ID: {artist_id})")

                if artist_image_url:
                    image_path = os.path.join(self.artist_image_path, f"{artist_guid}.jpg")
                    if not os.path.exists(image_path):
                        success = self._download_image(artist_image_url, image_path)
                        if not success:
                            print(f"Failed to download image for artist: {artist['name']} (ID: {artist_id})")
                    else:
                        print(f"Image already exists for artist: {artist['name']} (GUID: {artist_guid})")

            artist_info = {
                "guid": artist_guid,
                "name": artist['name'],
                "imgLocation": None
            }

            album_artists.append(artist_info)
        
        album_songs = self._get_album_songs(album['id'])

        album_id = album['id']
        if album_id in self.albums_id_to_guid:
            album_guid = self.albums_id_to_guid[album_id]
        else:
            album_guid = self._get_or_create_album_guid(album['name'])
            self.albums_id_to_guid[album_id] = album_guid

        album_json = {
            "guid": album_guid,
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
            print(f"No image found for album: {album['name']} (ID: {album_id})")

        if album_image_url:
            self._download_image(album_image_url, os.path.join(self.album_image_path, f"{album_guid}.jpg"))

        return album_json
    
    def _get_album_songs(self, album_id):
        songs = self.sp.album_tracks(album_id)['items']
        song_list = []
        for idx, song in enumerate(songs):
            song_artists = []
            
            for artist in song['artists']:

                artist_id = artist['id']
                if artist_id in self.artist_id_to_guid:
                    artist_guid = self.artist_id_to_guid[artist_id]
                else:
                    artist_guid = self._get_or_create_artist_guid(artist['name'])
                    self.artist_id_to_guid[artist_id] = artist_guid

                    artist_details = self.sp.artist(artist['id'])
                    images = artist_details.get('images', [])

                    if images:
                        artist_image_url = images[0].get('url')
                    else:
                        artist_image_url = None
                        print(f"No image found for artist: {artist['name']} (ID: {artist_id})")

                    if artist_image_url:
                        image_path = os.path.join(self.artist_image_path, f"{artist_guid}.jpg")
                        if not os.path.exists(image_path):
                            success = self._download_image(artist_image_url, image_path)
                            if not success:
                                print(f"Failed to download image for artist: {artist['name']} (ID: {artist_id})")
                        else:
                            print(f"Image already exists for artist: {artist['name']} (GUID: {artist_guid})")

                artist_info = {
                "guid": artist_guid,
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
            id = str(uuid.uuid4())

        return id

    def _download_image(self, url, file_path):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                return True
            else:
                print(f"Failed to download image from {url} (Status code: {response.status_code})")
                return False
        except Exception as e:
            print(f"An error occurred while downloading image from {url}: {e}")
            return False

    def _get_or_create_artist_guid(self, artist_name):
        try:
            response = requests.get(f"{self.get_guid_artist_byname}?name={requests.utils.quote(artist_name)}", verify=False)
            if response.status_code == 200:
                artist_guid = response.text.strip().replace('"', '')
            else:
                artist_guid = self.get_guid()
        except requests.RequestException as e:
            print(f"An error occurred during the API call: {e}")
            artist_guid = self.get_guid()

        return artist_guid
    
    def _get_or_create_album_guid(self, album_name):
        try:
            response = requests.get(f"{self.get_guid_album_byname}?name={requests.utils.quote(album_name)}", verify=False)
            if response.status_code == 200:
                album_guid = response.text.strip().replace('"', '')
            else:
                album_guid = self.get_guid()
        except requests.RequestException as e:
            print(f"An error occurred during the API call: {e}")
        
        return album_guid
