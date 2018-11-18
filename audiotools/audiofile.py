
#!python3

import sys

class AudioFile:
    def __init__(self, filename):
        self.filename = filename
        self.stream = ffmpeg.input(filename)

    def get_album_art(self):
        # TODO

    def set_album_art(self, albumart_file, resize = True):
        # TODO

    def encode(self, target_file, profile):

    def get_metadata(self):

    def set_artist(self, artist):

    def get_artist(self):

    def set_title(self, title):

    def get_title(self):

    def set_year(self, year):

    def get_year(self):

    def set_genre(self, genre):

    def get_genre(self):

    def get_track_number(self):

    def set_track_number(self, number):

    def set_album_art(self, album_art_file):

class AudioDirectory:
    __init__(self, dirname):
    self.dirname = dirname

    def encode(self, profile):




