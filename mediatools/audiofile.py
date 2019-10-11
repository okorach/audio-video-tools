#!/usr/local/bin/python3

import re
import os
import shutil
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.utilities as util

class AudioFile(media.MediaFile):
    def __init__(self, filename):
        self.audio_codec = None
        self.artist = None
        self.title = None
        self.author = None
        self.album = None
        self.year = None
        self.track = None
        self.genre = None
        self.comment = None
        self.audio_bitrate = None
        self.duration = None
        self.audio_sample_rate = None
        super(AudioFile, self).__init__(filename)

    def get_audio_specs(self):
        for stream in self.specs['streams']:
            if stream['codec_type'] == 'audio':
                try:
                    self.audio_bitrate = stream['bit_rate']
                    self.duration = stream['duration']
                    self.audio_codec = stream['codec_name']
                    self.audio_sample_rate = stream['sample_rate']
                except KeyError as e:
                    util.logger.error("Stream %s has no key %s\n%s", str(stream), e.args[0], str(stream))
        return self.specs

    def get_tags(self):
        from mp3_tagger import MP3File
        if util.get_file_extension(self.filename).lower() != 'mp3':
            raise media.FileTypeError('File %s is not an mp3 file')
            # Create MP3File instance.
        mp3 = MP3File(self.filename)
        self.artist = mp3.artist
        self.title = mp3.song
        self.album = mp3.album
        self.year = mp3.year
        self.track = mp3.track
        self.genre = mp3.genre
        self.comment = mp3.comment

    def get_title(self):
        if self.title is None:
            self.get_tags()
        return self.title

    def get_album(self):
        if self.album is None:
            self.get_tags()
        return self.album

    def get_author(self):
        if self.author is None:
            self.get_tags()
        return self.author

    def get_track(self):
        if self.track is None:
            self.get_tags()
        return self.track

    def get_year(self):
        if self.year is None:
            self.get_tags()
        return self.year

    def get_genre(self):
        if self.genre is None:
            self.get_tags()
        return self.genre

    def get_properties(self):
        if self.audio_codec is None:
            self.get_specs()
        all_specs = self.get_file_properties()
        all_specs.update({'file_size':self.size, 'file_format':self.format, \
            'audio_bitrate': self.audio_bitrate, 'audio_codec': self.audio_codec, \
            'audio_sample_rate':self.audio_sample_rate, 'author': self.author, 'year': self.year, \
            'title':self.title, 'track':self.track, 'genre':self.genre, 'album':self.album })
        return  all_specs

    def get_specs(self):
        super(AudioFile, self).get_specs()
        self.get_audio_specs()


def encode_album_art(source_file, album_art_file, **kwargs):
    """Encodes album art image in an audio file after optionally resizing"""
    # profile = 'album_art' - # For the future, we'll use the cmd line associated to the profile in the config file

    album_art_std_settings = '-metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)"'
    target_file = util.add_postfix(source_file, 'album_art')

    if kwargs['scale'] is not None:
        w, h = re.split("x",kwargs['scale'])
        album_art_file = image.rescale(album_art_file, int(w), int(h))
        delete_aa_file = True

    # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover"
    # -metadata:s:v comment="Cover (Front)" %1.mp3
    util.run_ffmpeg('-i "%s" -i "%s"  -map 0:0 -map 1:0 -c copy -id3v2_version 3 %s "%s"' % \
        (source_file, album_art_file, album_art_std_settings, target_file))
    shutil.copy(target_file, source_file)
    os.remove(target_file)
    if delete_aa_file:
        os.remove(album_art_file)
