import time
from Sources.Generator.Generate import Generate

def generate():
    albums_needed = 1
    while(albums_needed >= 0):
        Generate.generate()
        albums_needed = albums_needed - 1
        time.sleep(2)

if __name__ == "__main__":
    generate()