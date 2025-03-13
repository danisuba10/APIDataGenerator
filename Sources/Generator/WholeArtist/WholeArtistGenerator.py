import os
import re
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import shutil
from bs4 import BeautifulSoup
import json
from Sources.Generator.SpotifyAPICredentials import (
    SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI,
    API_USERNAME, API_PASSWORD
)
from collections import deque
import logging
import sys

class UTF8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # Fallback to ASCII-safe encoding
            msg = record.getMessage().encode('ascii', errors='replace').decode('ascii')
            stream.write(msg + self.terminator)
            self.flush()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("generator.log", encoding="utf-8"),  # Log to a file with UTF-8 encoding
        UTF8StreamHandler(sys.stdout)  # Log to the console with UTF-8 support
    ]
)

class WholeArtistGenerator:
    def __init__(self):
        os.environ['SPOTIPY_CLIENT_ID'] = SPOTIPY_CLIENT_ID
        os.environ['SPOTIPY_CLIENT_SECRET'] = SPOTIPY_CLIENT_SECRET
        os.environ['SPOTIPY_REDIRECT_URI'] = SPOTIPY_REDIRECT_URI

        self.sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(), retries=0)
        self.api_url = "http://localhost:5231/"

        self.jwt_token = self.login_to_local_api()
        self.processed_artists = {}  # Track processed artists to avoid duplicates

    def sanitize_filename(self, filename):
        # Replace invalid characters with an underscore
        return re.sub(r'[<>:"/\\|?*\[\]]', '_', filename)

    def login_to_local_api(self):
        try:
            url = f"{self.api_url}/user/login"
            login_data = {
                "userName": API_USERNAME,
                "password": API_PASSWORD
            }
            response = requests.post(url, data=login_data)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to login to local API: {e}")
            raise

    def get_random_artist(self):
        try:
            results = self.sp.search(q="", type="artist", limit=1, offset=0)
            artists = results["artists"]["items"]
            return artists[0] if artists else None
        except Exception as e:
            logging.error(f"Failed to fetch random artist: {e}")
            return None

    def get_artist_albums(self, artist_id):
        try:
            albums = []
            results = self.sp.artist_albums(artist_id, album_type="album", limit=50)
            albums.extend(results["items"])
            while results["next"]:
                results = self.sp.next(results)
                albums.extend(results["items"])
            return albums
        except Exception as e:
            logging.error(f"Failed to fetch albums for artist {artist_id}: {e}")
            return []

    def get_album_tracks(self, album_id):
        try:
            tracks = []
            results = self.sp.album_tracks(album_id)
            tracks.extend(results["items"])
            while results["next"]:
                results = self.sp.next(results)
                tracks.extend(results["items"])
            return tracks
        except Exception as e:
            logging.error(f"Failed to fetch tracks for album {album_id}: {e}")
            return []

    def download_preview(self, url, file_path):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(file_path, "wb") as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
        except Exception as e:
            logging.error(f"Failed to download preview from {url}: {e}")

    def add_artist_to_api(self, artist_name, image_url):
        try:
            url = f"{self.api_url}/artist/add-artist"
            sanitized_artist_name = self.sanitize_filename(artist_name)
            image_path = f"{sanitized_artist_name}.jpg"

            if image_url:
                try:
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    with open(image_path, "wb") as f:
                        response.raw.decode_content = True
                        shutil.copyfileobj(response.raw, f)
                except Exception as e:
                    logging.warning(f"Failed to download image for artist {artist_name}: {e}")

            if not os.path.exists(image_path):
                logging.warning(f"No image found for artist {artist_name}. Skipping image upload.")
                files = None
            else:
                with open(image_path, "rb") as f:
                    file_content = f.read()
                    files = {"FormFile": (os.path.basename(image_path), file_content, "image/jpeg")}

            data = {"Name": artist_name}
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            response = requests.post(url, files=files, data=data, headers=headers)
            response.raise_for_status()

            if os.path.exists(image_path):
                os.remove(image_path)

            return response.json().get("id")
        except Exception as e:
            logging.error(f"Failed to add artist {artist_name} to API: {e}")
            return None

    def add_album_to_api(self, album_name, year, image_url, artist_ids):
        try:
            url = f"{self.api_url}/album/add-album"
            sanitized_album_name = self.sanitize_filename(album_name)
            image_path = f"{sanitized_album_name}.jpg"

            if image_url:
                try:
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    with open(image_path, "wb") as f:
                        response.raw.decode_content = True
                        shutil.copyfileobj(response.raw, f)
                except Exception as e:
                    logging.warning(f"Failed to download image for album {album_name}: {e}")

            if not os.path.exists(image_path):
                logging.warning(f"No image found for album {album_name}. Skipping image upload.")
                files = None
            else:
                with open(image_path, "rb") as f:
                    file_content = f.read()
                    files = {"FormFile": (os.path.basename(image_path), file_content, "image/jpeg")}

            data = {
                "Name": album_name,
                "Year": year,
                "ArtistIds": artist_ids,
            }
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            response = requests.post(url, files=files, data=data, headers=headers)
            response.raise_for_status()

            if os.path.exists(image_path):
                os.remove(image_path)

            return response.json().get("id")
        except Exception as e:
            logging.error(f"Failed to add album {album_name} to API: {e}")
            return None

    def add_song_to_api(self, title, duration, album_id, position, artist_ids):
        try:
            url = f"{self.api_url}/song/add-song"
            data = {
                "Title": title,
                "Duration": duration,
                "AlbumId": album_id,
                "PositionInAlbum": position,
                "ArtistIds": artist_ids,
            }
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Failed to add song {title} to API: {e}")
            return False

    def check_artist_exists(self, artist_name):
        try:
            url = f"{self.api_url}/artist/search"
            params = {
                "SearchTerm": artist_name,
                "PageSize": 10
            }
            response = requests.get(url, params=params)
            response.raise_for_status()

            search_response = response.json()
            if search_response.get("searchResults"):
                for result in search_response["searchResults"]['$values']:
                    if result["type"] == "Artist" and result["name"].lower() == artist_name.lower():
                        return True
            return False
        except Exception as e:
            logging.error(f"Failed to check if artist {artist_name} exists: {e}")
            return False

    def fetch_preview_url(self, track_id):
        try:
            embed_url = f"https://open.spotify.com/embed/track/{track_id}"
            response = requests.get(embed_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            script_tags = soup.find_all("script")
            for script in script_tags:
                script_content = script.string
                if script_content and "audioPreview" in script_content:
                    try:
                        data = json.loads(script_content)
                        if (
                            "props" in data
                            and "pageProps" in data["props"]
                            and "state" in data["props"]["pageProps"]
                            and "data" in data["props"]["pageProps"]["state"]
                            and "entity" in data["props"]["pageProps"]["state"]["data"]
                            and "audioPreview" in data["props"]["pageProps"]["state"]["data"]["entity"]
                        ):
                            return data["props"]["pageProps"]["state"]["data"]["entity"]["audioPreview"]["url"]
                    except json.JSONDecodeError as e:
                        logging.error(f"Error parsing JSON for track {track_id}: {e}")
                        continue
            return None
        except Exception as e:
            logging.error(f"Failed to fetch preview URL for track {track_id}: {e}")
            return None

    def get_artist_id_from_api(self, artist_name):
        try:
            url = f"{self.api_url}/artist/search"
            params = {
                "SearchTerm": artist_name,
                "PageSize": 1
            }
            response = requests.get(url, params=params)
            response.raise_for_status()

            search_response = response.json()
            if search_response.get("searchResults"):
                for result in search_response["searchResults"]['$values']:
                    if result["type"] == "Artist" and result["name"].lower() == artist_name.lower():
                        return result["id"]
            return None
        except Exception as e:
            logging.error(f"Failed to fetch artist ID for {artist_name}: {e}")
            return None

    def generate(self):
        initial_artist = self.get_random_artist()
        if not initial_artist:
            logging.error("Failed to fetch a random artist.")
            return

        artist_queue = deque([initial_artist["id"]])

        while artist_queue:
            artist_id = artist_queue.popleft()

            if artist_id in self.processed_artists:
                continue

            self.generate_artist(artist_id, artist_queue)

    def generate_artist(self, artist_id, artist_queue):
        try:
            artist = self.sp.artist(artist_id)
            if not artist:
                logging.error(f"Failed to fetch artist with ID {artist_id}.")
                return

            artist_name = artist["name"]
            artist_image_url = artist["images"][0]["url"] if artist["images"] else None

            if self.check_artist_exists(artist_name):
                logging.info(f"Artist '{artist_name}' already exists in your API.")
                return

            logging.info(f"Adding artist '{artist_name}' to your API...")
            artist_id_in_api = self.add_artist_to_api(artist_name, artist_image_url)
            if not artist_id_in_api:
                logging.error(f"Failed to add artist '{artist_name}' to your API.")
                return

            self.processed_artists[artist_id] = artist_id_in_api

            albums = self.get_artist_albums(artist_id)
            if not albums:
                logging.info(f"No albums found for artist '{artist_name}'.")
                return

            for album in albums:
                album_name = album["name"]
                album_year = int(album["release_date"].split("-")[0])
                album_image_url = album["images"][0]["url"] if album["images"] else None
                album_id_in_spotify = album["id"]

                logging.info(f"Adding album '{album_name}' to your API...")
                album_id_in_api = self.add_album_to_api(album_name, album_year, album_image_url, [artist_id_in_api])
                if not album_id_in_api:
                    logging.error(f"Failed to add album '{album_name}' to your API.")
                    continue

                tracks = self.get_album_tracks(album_id_in_spotify)
                for track in tracks:
                    track_title = track["name"]
                    track_duration = int(track["duration_ms"] / 1000)
                    track_position = track["track_number"]
                    track_id = track["id"]
                    track_preview_url = self.fetch_preview_url(track_id)

                    collaborating_artist_ids = []
                    for collaborating_artist in track["artists"]:
                        if collaborating_artist["id"] != artist_id:
                            collaborating_artist_ids.append(collaborating_artist["id"])

                    for collaborating_artist_id in collaborating_artist_ids:
                        if collaborating_artist_id not in self.processed_artists:
                            artist_queue.append(collaborating_artist_id)

                    all_artist_ids = [artist_id_in_api] + [
                        self.processed_artists[collab_id] for collab_id in collaborating_artist_ids
                        if collab_id in self.processed_artists
                    ]

                    # Download the preview MP3 (if preview URL is available)
                    # if track_preview_url:
                    #     sanitized_artist_name = self.sanitize_filename(artist_name)
                    #     sanitized_album_name = self.sanitize_filename(album_name)
                    #     folder_path = f"{sanitized_artist_name}/{sanitized_album_name}"
                    #     os.makedirs(folder_path, exist_ok=True)
                    #     sanitized_file_title = self.sanitize_filename(track_title)
                    #     file_path = f"{folder_path}/{sanitized_file_title}.mp3"
                    #
                    #     self.download_preview(track_preview_url, file_path)

                    # Add the song to your API with all artist IDs
                    logging.info(f"Adding song '{track_title}' to your API...")
                    if not self.add_song_to_api(track_title, track_duration, album_id_in_api, track_position, all_artist_ids):
                        logging.error(f"Failed to add song '{track_title}' to your API.")

            logging.info(f"Completed processing artist '{artist_name}'.")
        except Exception as e:
            logging.error(f"Error processing artist {artist_id}: {e}")