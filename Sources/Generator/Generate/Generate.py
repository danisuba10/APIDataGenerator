import json
from Sources.Generator.AlbumGenerator.AlbumMetadataGenerator import JSONAlbumMetadaGenerator
import requests

from Sources.Generator.WholeArtist.WholeArtistGenerator import WholeArtistGenerator


def generate():
    generator = WholeArtistGenerator()
    generator.generate()
