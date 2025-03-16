import time
import sys
from Sources.Generator import Generate
from Sources.Generator.WholeArtist.WholeArtistGenerator import WholeArtistGenerator

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 Start.py <artist_name> <album_types>")
        sys.exit(1)

    artist_name = sys.argv[1]
    album_types = sys.argv[2]

    generator = WholeArtistGenerator(artist_name, album_types)
    generator.generate()