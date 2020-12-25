#!python3
#
# media-tools
# Copyright (C) 2019-2020 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import re
import os
import shutil
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.utilities as util
import mediatools.options as opt


class AudioFile(media.MediaFile):
    # This class is the abstraction of an audio file (eg MP3)
    def __init__(self, filename):
        self.acodec = None
        self.artist = None
        self.title = None
        self.author = None
        self.album = None
        self.year = None
        self.track = None
        self.genre = None
        self.comment = None
        self.abitrate = None
        self.duration = None
        self.audio_sample_rate = None
        super().__init__(filename)

    def get_audio_specs(self):
        for stream in self.specs['streams']:
            if stream['codec_type'] == 'audio':
                try:
                    self.abitrate = stream['bit_rate']
                    self.duration = stream['duration']
                    self.acodec = stream['codec_name']
                    self.audio_sample_rate = stream['sample_rate']
                except KeyError as e:
                    util.logger.error("Stream %s has no key %s\n%s", str(stream), e.args[0], str(stream))
        return self.specs

    def get_tags(self):
        """Returns all file MP3 tags"""
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

    def get_specs(self):
        #super(AudioFile, self).get_specs()
        self.get_audio_specs()

    def get_audio_properties(self):
        if self.acodec is None:
            self.get_specs()
        return {opt.media.ABITRATE: self.abitrate, opt.media.ACODEC: self.acodec, \
                'audio_sample_rate': self.audio_sample_rate }

    def get_properties(self):
        all_props = self.get_file_properties()
        all_props.update(self.get_audio_properties())
        return all_props

    def encode(self, target_file, profile, **kwargs):
        '''Encodes a file
        - target_file is the name of the output file. Optional
        - Profile is the encoding profile as per the VideoTools.properties config file
        - **kwargs accepts at large panel of other ptional options'''

        util.logger.debug("Encoding %s with profile %s and args %s", self.filename, profile, str(kwargs))
        if target_file is None:
            target_file = media.build_target_file(self.filename, profile)

        media_opts = self.get_properties()
        util.logger.debug("Input file settings = %s", str(media_opts))
        media_opts.update(util.get_ffmpeg_cmdline_params(util.get_conf_property(profile + '.cmdline')))
        media_opts.update({opt.media.FORMAT: util.get_conf_property(profile + '.format')})
        util.logger.debug("After profile settings(%s) = %s", profile, str(media_opts))
        media_opts.update(kwargs)
        util.logger.debug("After cmd line settings(%s) = %s", str(kwargs), str(media_opts))

        ffopts = opt.media2ffmpeg(media_opts)
        util.logger.debug("FFOPTS = %s", str(ffopts))
        util.run_ffmpeg('-i "%s" %s "%s"' % (self.filename, util.dict2str(ffopts), target_file))
        util.logger.info("File %s encoded", target_file)
        return target_file

def encode_album_art(source_file, album_art_file, **kwargs):
    """Encodes album art image in an audio file after optionally resizing"""
    # profile = 'album_art' - # For the future, we'll use the cmd line associated to the profile in the config file

    album_art_std_settings = '-metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)"'
    target_file = util.add_postfix(source_file, 'album_art')

    if kwargs['scale'] is not None:
        w, h = re.split("x", kwargs['scale'])
        album_art_file = image.rescale(album_art_file, int(w), int(h))

    # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover"
    # -metadata:s:v comment="Cover (Front)" %1.mp3
    util.run_ffmpeg('-i "%s" -i "%s"  -map 0:0 -map 1:0 -c copy -id3v2_version 3 %s "%s"' % \
        (source_file, album_art_file, album_art_std_settings, target_file))
    shutil.copy(target_file, source_file)
    os.remove(target_file)
    if kwargs['scale'] is not None:
        os.remove(album_art_file)
