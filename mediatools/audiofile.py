#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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
from mp3_tagger import MP3File
import mediatools.log as log
import mediatools.exceptions as ex
import mediatools.file as fil
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.utilities as util
import mediatools.options as opt


class AudioFile(media.MediaFile):
    # This class is the abstraction of an audio file (eg MP3)
    def __init__(self, filename):
        if not fil.is_audio_file(filename):
            raise ex.FileTypeError(file=filename, expected_type='audio')
        self.abitrate = None
        self.duration = None
        self.acodec = None
        self.audio_sample_rate = None

        self.has_album_art = False
        self.album_art_size = None

        self.artist = None
        self.title = None
        self.author = None
        self.album = None
        self.year = None
        self.track = None
        self.genre = None
        self.comment = None

        super().__init__(filename)

    def get_specs(self):
        for stream in self.specs['streams']:
            if stream['codec_type'] == 'audio':
                try:
                    self.abitrate = stream['bit_rate']
                    self.duration = stream['duration']
                    self.acodec = stream['codec_name']
                    self.audio_sample_rate = stream['sample_rate']
                except KeyError as e:
                    log.logger.error("Stream %s has no key %s\n%s", str(stream), e.args[0], str(stream))
            elif stream['codec_type'] in ('mjpeg', 'png') and 'coded_width' in stream and 'coded_height' in stream:
                self.has_album_art = True
                self.album_art_size = '{}x{}'.format(stream['coded_width'], stream['coded_height'])
        self.get_tags()
        return self.specs

    def hash(self, algo='audio', force=False):
        if algo != 'audio':
            return super().hash(algo=algo, force=force)
        if self._hash is None or force:
            self.get_tags()
            self._hash = "{}-{}-{}-{}-{}-{}-{}".format(self.artist, self.title, self.album,
                self.year, self.track, self.duration, self.acodec)
            log.logger.debug("Audio Hash(%s) = %s", self.filename, self._hash)
        return self._hash

    def get_tags_by_version(self, version=None):
        """Returns all file MP3 tags"""
        if self.extension().lower() != 'mp3':
            raise ex.FileTypeError(self.filename, expected_type='mp3')
            # Create MP3File instance.
        if self.title is None:
            mp3 = MP3File(self.filename)
            tags = mp3.get_tags()
            tags_v1 = tags['ID3TagV1']
            tags_v2 = tags['ID3TagV2']
            if version is None or version not in (1, 2):
                tags = {**tags_v1, **tags_v2}
            elif version == 1:
                tags = tags_v1
            elif version == 2:
                tags = tags_v2
            for k in tags.keys():
                if isinstance(tags[k], str):
                    tags[k] = tags[k].rstrip('\u0000')
            self.artist = tags.get('artist', None)
            self.title = tags.get('song', None)
            self.album = tags.get('album', None)
            self.year = tags.get('year', None)
            self.track = tags.get('track', None)
            self.genre = tags.get('genre', None)
            self.comment = tags.get('comment', None)
        return vars(self)

    def get_tags(self, version=None):
        try:
            tags = self.specs['format']['tags']
        except KeyError:
            return
        self.title = tags.get('title', None)
        self.artist = tags.get('artist', None)
        self.year = int(tags.get('date', None))
        self.track = tags.get('track', None)
        self.album = tags.get('album', None)
        self.genre = tags.get('genre', None)
        # self.comment = tags.get('comment', None)
        return vars(self)

    def get_title(self):
        if self.title is None:
            self.get_tags()
        return self.title

    def get_album(self):
        if self.album is None:
            self.get_tags()
        return self.album
        self.year = None

    def get_author(self):
        if self.author is None:
            self.get_tags()
        return self.author
        self.year = "Merge bug"

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

    def get_audio_properties(self):
        if self.acodec is None:
            self.get_specs()
        return {opt.Option.ABITRATE: self.abitrate, opt.Option.ACODEC: self.acodec,
                'audio_sample_rate': self.audio_sample_rate}

    def get_properties(self):
        all_props = self.get_file_properties()
        all_props.update(self.get_audio_properties())
        return all_props

    def encode(self, target_file, profile, **kwargs):
        '''Encodes a file
        - target_file is the name of the output file. Optional
        - Profile is the encoding profile as per the VideoTools.properties config file
        - **kwargs accepts at large panel of other ptional options'''

        log.logger.debug("Encoding %s with profile %s and args %s", self.filename, profile, str(kwargs))
        if target_file is None:
            target_file = media.build_target_file(self.filename, profile)

        media_opts = self.get_properties()
        log.logger.debug("Input file settings = %s", str(media_opts))
        media_opts.update(util.get_ffmpeg_cmdline_params(util.get_conf_property(profile + '.cmdline')))
        media_opts.update({opt.Option.FORMAT: util.get_conf_property(profile + '.format')})
        log.logger.debug("After profile settings(%s) = %s", profile, str(media_opts))
        media_opts.update(kwargs)
        log.logger.debug("After cmd line settings(%s) = %s", str(kwargs), str(media_opts))

        ffopts = opt.media2ffmpeg(media_opts)
        log.logger.debug("FFOPTS = %s", str(ffopts))
        util.run_ffmpeg('-i "%s" %s "%s"' % (self.filename, util.dict2str(ffopts), target_file))
        log.logger.info("File %s encoded", target_file)
        return target_file

    def encode_album_art(self, album_art_file):
        """Encodes album art image in an audio file after optionally resizing"""
        album_art_std_settings = '-metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)"'
        target_file = util.add_postfix(self.filename, 'album_art')

        # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover"
        # -metadata:s:v comment="Cover (Front)" %1.mp3
        util.run_ffmpeg('-i "{}" -i "{}"  -map 0:0 -map 1:0 -c copy -id3v2_version 3 {} "{}"'.format(
            self.filename, album_art_file, album_art_std_settings, target_file))
        shutil.copy(target_file, self.filename)
        os.remove(target_file)


def album_art(*file_list, scale=None):
    log.logger.debug("Album art(%s)", str(file_list))
    album_cover = fil.file_list(*file_list, file_type=fil.FileType.IMAGE_FILE)
    if len(album_cover) != 1:
        log.logger.critical("Zero or too many image files in selection")
        return False

    if scale is not None:
        (w, h) = [int(x) for x in re.split("x", scale)]
        cover_file = image.ImageFile(album_cover[0]).scale(w, h)
    else:
        cover_file = album_cover[0]

    for f in [AudioFile(f) for f in fil.file_list(*file_list, file_type=fil.FileType.AUDIO_FILE)]:
        f.encode_album_art(cover_file)

    if scale is not None:
        os.remove(cover_file)
    return True


def get_hash_list(filelist, algo='audio'):
    log.logger.info("Getting audio hashes of %d files", len(filelist))
    hashes = {}
    i = 0
    if algo != 'audio':
        return fil.get_hash_list(filelist, algo)
    for f in filelist:
        try:
            obj = AudioFile(f)
            obj.get_specs()
            h = obj.hash(algo)
        except ex.FileTypeError:
            continue
        if h in hashes:
            hashes[h].append(f)
        else:
            hashes[h] = [f]
        i += 1
        if (i % 100) == 0:
            log.logger.info("%d audio hashes computed", i)
    return hashes
