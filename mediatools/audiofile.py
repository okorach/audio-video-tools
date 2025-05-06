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
from datetime import datetime
import json
from mp3_tagger import MP3File
import music_tag
from mediatools import log
import mediatools.exceptions as ex
import utilities.file as fil
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.utilities as util
import mediatools.options as opt

_CSV_KEYS = ("filename", "artist", "title", "album", "year", "duration", "acodec", "abitrate", "audio_sample_rate", "genre", "has_album_art")


class AudioFile(media.MediaFile):
    # This class is the abstraction of an audio file (eg MP3)
    def __init__(self, filename):
        if not fil.is_audio_file(filename):
            raise ex.FileTypeError(file=filename, expected_type="audio")
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
        self._hash = None

        super().__init__(filename)
        # self.get_specs()

    def csv_values(self):
        d = vars(self)
        log.logger.debug("FIle = %s", json.dumps(d, separators=(",", ": "), indent=3))
        arr = []
        for k in _CSV_KEYS:
            v = ""
            if k in d and d[k] is not None:
                v = str(d[k])
            arr.append(v)
        return arr

    def get_specs(self):
        if self.specs is None:
            self.probe()
        for stream in self.specs["streams"]:
            if stream["codec_type"] == "audio":
                try:
                    self.abitrate = stream["bit_rate"]
                    self.duration = float(stream["duration"])
                    self.acodec = stream["codec_name"]
                    self.audio_sample_rate = stream["sample_rate"]
                except KeyError as e:
                    log.logger.error("Stream %s has no key %s\n%s", str(stream), e.args[0], str(stream))
            elif stream["codec_name"] in ("mjpeg", "png") and "coded_width" in stream and "coded_height" in stream:
                self.has_album_art = True
                self.album_art_size = f"{stream['coded_width']}x{stream['coded_height']}"
        self.get_tags()
        return self.specs

    def hash(self, algo="audio", force=False):
        if algo != "audio":
            return super().hash(algo=algo, force=force)
        if self._hash is None or force:
            self.get_specs()
            self.get_tags()
            self._hash = "{}-{}-{}-{}-{}-{}-{}".format(self.artist, self.title, self.album, self.year, self.track, self.duration, self.acodec)
            log.logger.debug("Audio Hash(%s) = %s", self.filename, self._hash)
        return self._hash

    def get_tags_by_version(self, version=None):
        """Returns all file MP3 tags"""
        if self.extension().lower() != "mp3":
            raise ex.FileTypeError(self.filename, expected_type="mp3")
            # Create MP3File instance.
        if self.title is None:
            mp3 = MP3File(self.filename)
            tags = mp3.get_tags()
            tags_v1 = tags["ID3TagV1"]
            tags_v2 = tags["ID3TagV2"]
            if version is None or version not in (1, 2):
                tags = {**tags_v1, **tags_v2}
            elif version == 1:
                tags = tags_v1
            elif version == 2:
                tags = tags_v2
            for k in tags.keys():
                if isinstance(tags[k], str):
                    tags[k] = tags[k].rstrip("\u0000")
            self.artist = tags.get("artist", None)
            self.title = tags.get("song", None)
            self.album = tags.get("album", None)
            self.year = tags.get("year", None)
            self.track = tags.get("track", None)
            self.genre = tags.get("genre", None)
            self.comment = tags.get("comment", None)
        return vars(self)

    def get_tags(self, version=None):
        log.logger.debug("Getting tags of %s", self.filename)
        self.probe()
        try:
            tags = self.specs["format"]["tags"]
        except KeyError:
            log.logger.warning("Can't get tags for %s", self.filename)
            return None
        log.logger.debug("Tags = %s", util.json_fmt(tags))
        self.title = tags.get("title", None)
        self.artist = tags.get("artist", None)
        self.year = tags.get("date", None)
        if self.year is not None:
            self.year = int(self.year.split("-")[0])
        self.track = tags.get("track", None)
        self.album = tags.get("album", None)
        self.genre = tags.get("genre", None)
        # self.comment = tags.get('comment', None)
        log.logger.debug("self.title = %s", str(self.title))
        return tags

    def get_title(self):
        log.logger.debug("get_title(%s)", str(self.title))
        if self.title is None:
            self.get_tags()
        return self.title

    def get_album(self):
        if self.album is None:
            self.get_tags()
        return self.album

    def get_author(self):
        return self.get_artist()

    def get_artist(self):
        if self.artist is None:
            self.get_tags()
        return self.artist

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
        return {opt.Option.ABITRATE: self.abitrate, opt.Option.ACODEC: self.acodec, "audio_sample_rate": self.audio_sample_rate}

    def get_properties(self):
        all_props = self.get_file_properties()
        all_props.update(self.get_audio_properties())
        return all_props

    def encode(self, target_file=None, profile=None, **kwargs):
        """Encodes a file
        - target_file is the name of the output file. Optional
        - Profile is the encoding profile as per the VideoTools.properties config file
        - **kwargs accepts at large panel of other ptional options"""
        kwargs = util.get_all_options(fil.FileType.AUDIO_FILE, **kwargs)
        log.logger.debug("Audio encoding %s with profile %s and args %s", self.filename, profile, str(kwargs))
        if target_file is None:
            target_file = media.build_target_file(self.filename, profile)

        input_settings = media.get_input_settings(**kwargs)
        prefilter_settings = media.get_prefilter_settings(**kwargs)
        audio_filters = media.get_audio_filters(**kwargs)
        raw_settings = util.get_profile_params(profile)
        output_settings = media.get_output_settings(fil.FileType.AUDIO_FILE, **kwargs)
        ext = target_file.split(".")[-1].lower()
        log.logger.debug("Output file extension = %s", ext)
        if ext == "mp3" and output_settings[opt.OptionFfmpeg.ACODEC] != "copy":
            output_settings[opt.OptionFfmpeg.ACODEC] = "libmp3lame"
            log.logger.info("Patching codec for MP3 audio output")
        elif ext in ("m3a", "aac") and output_settings[opt.OptionFfmpeg.ACODEC] != "copy":
            output_settings[opt.OptionFfmpeg.ACODEC] = "aac"
            log.logger.info("Patching codec for AAC audio output")
        output_str = media.build_ffmpeg_options({**raw_settings, **output_settings})

        log.logger.info("Encoding mp3 %s", target_file)
        cmd = f'{" ".join(input_settings)} -i "{self.filename}" {" ".join(prefilter_settings)}'
        cmd += f' {str(audio_filters)} {output_str} "{target_file}"'
        util.run_ffmpeg(cmd, self.duration)
        log.logger.info("File %s encoded", target_file)
        return target_file

    def encode_album_art(self, album_art_file):
        """Encodes album art image in an audio file after optionally resizing"""
        album_art_std_settings = '-metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)"'
        target_file = util.add_postfix(self.filename, "album_art")

        # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover"
        # -metadata:s:v comment="Cover (Front)" %1.mp3
        util.run_ffmpeg(
            '-i "{}" -i "{}"  -map 0:0 -map 1:0 -c copy -id3v2_version 3 {} "{}"'.format(
                self.filename, album_art_file, album_art_std_settings, target_file
            )
        )
        shutil.copy(target_file, self.filename)
        os.remove(target_file)

    def set_tag(self, tag, value):
        f = music_tag.load_file(self.filename)
        # dict access returns a MetadataItem
        log.logger.info("Setting tag %s of %s to %s", tag, self.filename, value)
        f[tag] = value
        f.save()

    def get_a_tag(self, tag):
        try:
            f = music_tag.load_file(self.filename)
        except:
            return ""
        # dict access returns a MetadataItem
        return f.get(tag, "")


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


def get_hash_list(filelist, algo="audio", old_hash=None):
    log.logger.info("Getting audio hashes of %d files", len(filelist))
    hashes = {}
    i = 0
    if algo != "audio":
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


def update_hash_list(master_dir, hash_file_name=None):
    log.logger.info("Updating file hash")
    filelist = fil.dir_list(master_dir, recurse=True)
    if hash_file_name is None:
        hash_file_name = f"{master_dir}.json"
    _hash = read_hash_list(hash_file_name)
    log.logger.info("Getting audio hashes of %d files", len(filelist))
    last_date = datetime.strptime(_hash["datetime"], "%Y-%m-%d %H:%M:%S")
    hashes = _hash["hashes"]
    files = _hash.get("files", {})
    log.logger.info("Already %d files in hash", len(files))
    i, j, k = 0, 0, 0
    _hash["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for f in filelist:
        try:
            file_o = AudioFile(f)
            if file_o.filename not in files or datetime(*(file_o.modification_date())[:6]) > last_date:
                log.logger.debug("File %s already in hash", f)
                file_o.probe()
                file_o.get_specs()
                h = file_o.hash("audio")
                files[f] = h
                if h in hashes:
                    hashes[h].append(f)
                else:
                    hashes[h] = [f]
                k += 1
            else:
                log.logger.debug("File %s already in hash", f)
            j += 1
        except ex.FileTypeError:
            pass
        i += 1
        if (i % 100) == 0:
            log.logger.info("%d files / %d audio hashes computed / %d updated", i, j, k)
    log.logger.info("%d files / %d audio hashes computed / %d updated", i, j, k)
    _hash["root_directory"] = master_dir
    _hash["hashes"] = hashes
    _hash["files"] = files
    with open(hash_file_name, "w", encoding="utf-8") as fh:
        print(json.dumps(_hash, indent=2, sort_keys=False, separators=(",", ": ")), file=fh)
    return hashes


def save_hash_list(h_file, hash_data):
    """Saves hash data in a file"""
    with open(h_file, "w", encoding="utf-8") as fh:
        print(json.dumps(hash_data, indent=2, sort_keys=False, separators=(",", ": ")), file=fh)


def read_hash_list(file):
    try:
        with open(file, "r", encoding="utf-8") as fh:
            data = json.loads(fh.read())
    except FileNotFoundError:
        data = {"datetime": "1970-01-01 00:00:00", "hashes": {}, "files": {}, "root_directory": ""}
    return data


def csv_headers():
    arr = []
    for k in _CSV_KEYS:
        arr.append(k)
    return arr
