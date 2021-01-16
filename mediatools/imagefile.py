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

import math
import re
import random
import shutil
import exifread

import mediatools.utilities as util
import mediatools.resolution as res
import mediatools.exceptions as ex
import mediatools.mediafile as media
import mediatools.filters as filters

INPUT_FILE_FMT = ' -i "%s"'
STEP_FMT = "[step%d]; "
OVERLAY_0_FMT = "[%d][pip0]overlay=0:0" + STEP_FMT
OVERLAY_N_FMT = "[step%d][pip%d]overlay=%d:%d"

MAX_INT = 2000000000


class ImageFile(media.MediaFile):

    SUPPORTED_IMG_CODECS = ('mjpeg', 'png', 'gif')

    def __init__(self, filename):
        if not util.is_image_file(filename):
            raise ex.FileTypeError(file=filename, expected_type='image')
        self.resolution = None
        self.dar = None
        self.width = None
        self.height = None
        self.pixels = None
        self.ratio = None
        self.orientation = 'landscape'
        super().__init__(filename)
        self.probe()

    def __str__(self):
        d = vars(self)
        d['resolution'] = str(d.resolution)
        return str(d)

    def get_properties(self):
        '''Returns file media properties as a dict'''
        all_props = self.get_file_properties()
        all_props.update(self.get_image_properties())
        all_props.pop('resolution')
        util.logger.debug("Returning image props %s", str(all_props))
        return all_props

    def probe(self):
        if self.specs is not None:
            return
        super().probe()
        stream = self.__get_stream_by_codec__('codec_name', ImageFile.SUPPORTED_IMG_CODECS)
        self.format = stream['codec_name']
        self.width = int(util.find_key(stream, ('width', 'codec_width', 'coded_width')))
        self.height = int(util.find_key(stream, ('height', 'codec_height', 'coded_height')))
        self.dar = util.find_key(stream, ['display_aspect_ratio'])
        self.resolution = res.Resolution(width=self.width, height=self.height)
        self.pixels = self.width * self.height
        self.ratio = self.width / self.height
        self.exif_read()
        util.logger.debug("Image = %s", str(vars(self)))

    def exif_read(self):
        f = open(self.filename, 'rb')
        tags = exifread.process_file(f)
        # for tag in tags:
        #     if not re.search("thumbnail", tag, re.IGNORECASE):
        #         util.logger.debug('Tag "%s" = "%s"', tag, tags[tag])
        if re.search('Rotated 90', str(tags.get('Image Orientation', ''))):
            # self.width, self.height = self.height, self.width
            # self.resolution = res.Resolution(width=self.width, height=self.height)
            self.orientation = 'portrait'
            util.logger.debug('Portrait orientation: %s', str(self.resolution))

        return tags

    def dimensions(self, ignore_orientation=False):
        if not ignore_orientation and self.orientation == 'portrait':
            return (self.height, self.width)
        return (self.width, self.height)

    def get_ratio(self):
        return self.width / self.height

    def get_image_properties(self):
        return {'format': self.format, 'width': self.width, 'height': self.height, 'pixels': self.pixels}

    def crop(self, out_file=None, **kwargs):
        width, height = kwargs.pop('width'), kwargs.pop('height')
        (w, h) = self.resolution.calc_resolution(width, height, orientation=self.orientation)
        (top, left, pos) = self.__get_top_left__(w, h, **kwargs)
        out_file = util.automatic_output_file_name(out_file, self.filename, "crop_{0}x{1}-{2}".format(w, h, pos))

        util.run_ffmpeg('-y -i "{}" -vf "{}" "{}"'.format(self.filename, filters.crop(w, h, left, top), out_file))
        return out_file

    def scale(self, w=-1, h=-1, out_file=None):
        out_file = util.automatic_output_file_name(out_file, self.filename, "scale-{}x{}".format(w, h))
        if w == -1 and h == -1:
            shutil.copy(self.filename, out_file)
            return out_file
        util.logger.debug("Rescaling %s to %d x %d into %s", self.filename, w, h, out_file)
        util.run_ffmpeg('-i "{}" -vf "{}" "{}"'.format(self.filename, filters.scale(w, h), out_file))
        return out_file

    def slice_vertical(self, nbr_slices, round_to=16):
        filter_list = []
        w, h = self.dimensions()
        slice_w = max(w // nbr_slices, round_to)
        nbr_slices = min(nbr_slices, (w // slice_w) + 1)
        for i in range(nbr_slices):
            filter_list.append(filters.crop(slice_w, h, i * slice_w, 0))
        return filter_list

    def slice_horizontal(self, nbr_slices, round_to=16):
        filter_list = []
        w, h = self.dimensions()
        slice_h = max(h // nbr_slices, round_to)
        nbr_slices = min(nbr_slices, (h // slice_h) + 1)
        for i in range(nbr_slices):
            filter_list.append(filters.crop(w, slice_h, 0, i * slice_h))
        return filter_list

    def get_crop_filters(self, nbr_slices, direction='vertical', round_to=16):
        if direction == 'horizontal':
            return self.slice_horizontal(nbr_slices, round_to)
        else:
            return self.slice_vertical(nbr_slices, round_to)

    def crop_any(self, width_height_ratio="1.5", align="center", out_file=None):
        if re.match(r"^\d+:\d+$", width_height_ratio):
            a, b = [float(x) for x in width_height_ratio.split(':')]
            ratio = a / b
        else:
            ratio = float(width_height_ratio)

        w, h = self.dimensions()
        current_ratio = w / h
        crop_w = w
        crop_h = h
        if current_ratio > ratio:
            crop_w = h * ratio
        else:
            crop_h = w // ratio

        x = 0
        y = 0
        if align == 'right':
            if ratio > current_ratio:
                y = h - crop_h
            else:
                x = w - crop_w
        elif align == 'center':
            if ratio > current_ratio:
                y = (h - crop_h) // 2
            else:
                x = (w - crop_w) // 2

        self.crop(crop_w, crop_h, x, y, out_file)

    def blindify(self, out_file=None, **kwargs):
        nbr_slices = int(kwargs.pop('blinds', 10))
        files = [ImageFile(__get_background__(kwargs.pop('background_color', 'black'))), self]
        fcomp = filters.Complex(*files)
        direction = kwargs.pop('direction', 'vertical')
        w, h = self.dimensions()
        w_gap = int(util.percent_or_absolute(kwargs.pop('blinds_size', "3%"), self.width))
        h_gap = int(util.percent_or_absolute(kwargs.pop('blinds_size', "3%"), self.height))

        if direction == 'horizontal':
            scale_f = filters.scale(w, (h // nbr_slices * nbr_slices) + h_gap * (nbr_slices - 1))
        else:
            scale_f = filters.scale((w // nbr_slices * nbr_slices) + w_gap * (nbr_slices - 1), h)
        ovl = fcomp.add_filtergraph([0], scale_f)
        crop_filters = self.get_crop_filters(nbr_slices, direction)
        out_slices = []
        for f in crop_filters:
            out_slices.append(fcomp.add_filtergraph(1, f))

        for i in range(len(crop_filters)):
            if direction == 'horizontal':
                overlay_filter = filters.overlay(0, i * (h // nbr_slices + h_gap))
            else:
                overlay_filter = filters.overlay(i * (w // nbr_slices + w_gap), 0)
            ovl = fcomp.add_filtergraph([ovl, out_slices[i]], overlay_filter)

        out_file = util.automatic_output_file_name(out_file, self.filename, "blind")
        util.run_ffmpeg('{} {} -map "[{}]" "{}"'.format(fcomp.format_inputs(), str(fcomp), ovl, out_file))
        return out_file

    def shake_vertical(self, nbr_slices=10, shake_pct=3, background_color="black", out_file=None):
        w, h = self.dimensions()
        h_jitter = h * shake_pct // 100
        slice_width = max(w // nbr_slices, 16)
        slices = self.slice_vertical(nbr_slices)
        tmpbg = get_rectangle(background_color, slice_width * len(slices), h + h_jitter)
        filelist = filters.inputs_str(slices) + " " + filters.inputs_str([tmpbg])
        cmplx = util.build_ffmpeg_complex_prep(slices)

        step = 0
        n_slices = len(slices)
        cmplx = cmplx + OVERLAY_0_FMT % (n_slices, step)
        first_slice = slices.pop(0)

        for j in range(n_slices):
            x = (j + 1) * slice_width
            y = random.randint(1, h_jitter)
            cmplx = cmplx + OVERLAY_N_FMT % (j, j + 1, x, y)
            if j < n_slices - 1:
                cmplx = cmplx + STEP_FMT % (j + 1)
            j += 1
        out_file = util.automatic_output_file_name(out_file, self.filename, "shake")
        util.run_ffmpeg(' %s -filter_complex "%s" "%s"' % (filelist, cmplx, out_file))
        util.delete_files(*slices, first_slice, tmpbg)
        return out_file

    def shake_horizontal(self, nbr_slices=10, shake_pct=3, background_color="black", out_file=None):
        w, h = self.dimensions()
        w_jitter = w * shake_pct // 100
        slice_height = max(h // nbr_slices, 16)
        slices = self.slice_horizontal(nbr_slices)
        tmpbg = get_rectangle(background_color, w + w_jitter, slice_height * len(slices))
        filelist = filters.inputs_str(slices) + " " + filters.inputs_str([tmpbg])
        cmplx = util.build_ffmpeg_complex_prep(slices)

        step = 0
        n_slices = len(slices)
        cmplx = cmplx + OVERLAY_0_FMT % (n_slices, step)
        first_slice = slices.pop(0)

        for j in range(n_slices):
            x = random.randint(1, w_jitter)
            y = (j + 1) * slice_height
            cmplx = cmplx + OVERLAY_N_FMT % (j, j + 1, x, y)
            if j < n_slices - 1:
                cmplx = cmplx + STEP_FMT % (j + 1)
            j += 1

        out_file = util.automatic_output_file_name(out_file, self.filename, "shake")
        util.run_ffmpeg(' %s -filter_complex "%s" %s' % (filelist, cmplx, out_file))
        util.delete_files(*slices, first_slice, tmpbg)
        return out_file

    def shake(self, nbr_slices=10, shake_pct=3, background_color="black", direction='vertical', out_file=None):
        if direction == 'horizontal':
            return self.shake_horizontal(nbr_slices, shake_pct, background_color, out_file)
        else:
            return self.shake_vertical(nbr_slices, shake_pct, background_color, out_file)

    def zoom(self, **kwargs):
        '''
        Converts an image in a video with a zoom effect
        Allowed inputs:
        - zstart, zstop: Start/stop for the zoom (as percentage or float), proportion of original image
        - duration in seconds
        - All video usual parameters (resolution, fps etc...)
        '''
        (zstart, zstop) = [max(x, 100) for x in kwargs.get('effect', (100, 130))]
        fps = int(kwargs.get('framerate', 50))
        duration = float(kwargs.get('duration', 5))
        resolution = kwargs.get('resolution', res.Resolution.DEFAULT_VIDEO)
        out_file = kwargs.get('out_file', None)
        util.logger.debug("zoom video of image %s", self.filename)
        out_file = util.automatic_output_file_name(out_file, self.filename,
            'zoom-{}-{}'.format(zstart, zstop), extension="mp4")
        util.logger.debug("zoom(%d,%d) of image %s", zstart, zstop, self.filename)

        vfilters = []
        if self.get_ratio() > (16 / 9):
            vfilters.append(filters.scale(-1, 3240))
        else:
            vfilters.append(filters.scale(5760, -1))
        vfilters.append(filters.crop(5760, 3240))

        step = abs(zstop - zstart) / 100 / duration / fps
        if zstop < zstart:
            zformula = "if(lte(zoom,1.0),{},max({}+0.001,zoom-{}))".format(zstart / 100, zstop / 100, step)
        else:
            zformula = "min(zoom+{},{})".format(step, zstop / 100)
        vfilters.append(
            filters.zoompan("iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", zformula, d=int(duration * fps), fps=fps))
        vfilters.append(filters.trim(duration=duration))
        cmd = '-i "{}" -framerate {} -filter_complex "[0:v]{}[v]" -map "[v]" -s {} "{}"'.format(
            self.filename, fps, ','.join(vfilters), resolution, out_file)
        util.run_ffmpeg(cmd)
        return out_file

    def __compute_total_frame__(self, needed_width, needed_height):
        if needed_width > self.resolution.width:
            if needed_height > self.resolution.height * needed_width / self.resolution.width:
                scale_filter = filters.scale(-1, needed_height)
                total_height = needed_height
                total_width = total_height * self.resolution.ratio
            else:
                scale_filter = filters.scale(needed_width, -1)
                total_width = needed_width
                total_height = total_width / self.resolution.ratio
        elif needed_height > self.resolution.height:
            scale_filter = filters.scale(-1, needed_height)
            total_height = needed_height
            total_width = total_height * self.resolution.ratio
        else:
            total_height = self.resolution.height
            total_width = self.resolution.width
            scale_filter = filters.scale(total_width, total_height)
        return (scale_filter, total_width, total_height)

    def __get_panorama_params__(self, **kwargs):
        if ((kwargs.get('effect', None) is None and kwargs.get('duration', None) is None) or
           (kwargs.get('effect', None) is None and kwargs.get('speed', None) is None) or
           (kwargs.get('duration', None) is None and kwargs.get('speed', None) is None)):
            raise ex.InputError("2 arguments out of 3 mandatory in effect, duration or speed", "panorama")
        if kwargs.get('effect', None) is None:
            util.logger.info("Computing bounds from duration and speed")
            duration = float(kwargs['duration'])
            if duration <= 0:
                raise ex.InputError("duration must be a strictly positive number", "panorama")
            speed = util.percent_or_absolute(kwargs['speed'])
        elif kwargs.get('duration', None) is None:
            util.logger.info("Computing duration from speed and bounds")
            speed = util.percent_or_absolute(kwargs['speed'])
            (xstart, xstop, _, _) = [float(x) for x in kwargs['effect']]
            if xstop < xstart and speed > 0:
                speed = - speed
            duration = abs((xstop - xstart) / speed)
        elif kwargs.get('speed', None) is None:
            util.logger.info("Computing speed from duration and bounds")
            duration = float(kwargs['duration'])
            (xstart, xstop, _, _) = [float(x) for x in kwargs['effect']]
            speed = (xstop - xstart) / duration
        return (speed, duration)

    def panorama(self, **kwargs):
        '''
        Creates a panorama video of an image. Accepted inputs
        - framerate
        - effect: Defines bounds of the panorama as a 4-tuple
        - Duration in seconds
        - Speed: % of the image traveled in 1 sec (0.1 or 10%)
        '''
        util.logger.debug("panorama(%s)", str(kwargs))
        framerate = kwargs.get('framerate', 50)

        v_res = res.Resolution(resolution=kwargs.get('resolution', res.Resolution.DEFAULT_VIDEO))
        # Filters used for panorama are incompatible with hw acceleration

        (speed, duration) = self.__get_panorama_params__(**kwargs)
        ystart, ystop = 0.5, 0.5

        vspeed = 0
        if kwargs.get('effect', None) is None:
            util.logger.info("Computing ystart/ystop from duration and speed")
            vspeed = util.percent_or_absolute(kwargs.get('vspeed', 0))
        else:
            (_, _, ystart, ystop) = [float(x) for x in kwargs['effect']]
            if self.resolution.ratio < 16 / 9:
                vspeed = (ystop - ystart) / self.resolution.ratio * 16 / 9 / duration

        needed_width = int(res.RES_VIDEO_4K.width * (1 + abs(speed) * duration))
        needed_height = int(res.RES_VIDEO_4K.height * (1 + abs(vspeed) * duration))

        (scale, total_width, total_height) = self.__compute_total_frame__(needed_width, needed_height)
        vfilters = [scale]

        util.logger.debug("Image WxH = %d, %d - Needed WxH %d, %d - Total WxH %d, %d",
            self.width, self.height, needed_width, needed_height, int(total_width), int(total_height))
        util.logger.debug("Duration = %s, Speed = %s", str(duration), str(speed))

        vfilters.append(filters.crop(needed_width, needed_height))
        if speed < 0:
            x_formula = "'(iw-ow)-(ow*{0}*t)'".format(round(-speed, 5))
        else:
            x_formula = "'ow*{0}*t'".format(round(speed, 5))
        if vspeed < 0:
            y_formula = "'(ih-oh)-(oh*{0}*t)'".format(round(-vspeed, 5))
        else:
            y_formula = "'oh*{0}*t'".format(round(vspeed, 5))

        vfilters.append(filters.crop(res.RES_VIDEO_4K.width, res.RES_VIDEO_4K.height, x_formula, y_formula))

        out_file = util.automatic_output_file_name(kwargs.get('out_file', None), self.filename, 'pan', extension="mp4")

        cmd = '-framerate {} -loop 1 -i "{}" -filter_complex "[0:v]{}" -t {} -s {} "{}"'.format(
            framerate, self.filename, ','.join(vfilters), duration, str(v_res), out_file)
        util.run_ffmpeg(cmd)
        return out_file

    def to_video(self, with_effect=True, **kwargs):
        '''
        Converts an image to a video.
        Allowed inputs:
        - with_effect: Slight panorama or zoom effect will be generated
        - All typical video parameters (resolution, hw_accel, fps, ...)
        '''
        util.logger.info("Converting %s to video", self.filename)
        if not with_effect:
            return self.panorama(effect=(0.5, 0.5, 0.5, 0.5), **kwargs)

        (w, h) = self.dimensions()
        if self.resolution.ratio <= (3 / 4 + 0.00001):
            return self.panorama(duration=8, effect=(0.5, 0.5, 0.2, 0.8), **kwargs)
        elif self.resolution.ratio >= (16 / 9 + 0.00001):
            r = random.randint(0, 10)
            # Allow up to 20% crop if image ratio < 9 / 16
            offset = 0.2 if w / h <= (9 / 16 + 0.00001) else 0
            r = r + offset if r == 0 else r - offset
            # Allow up to 10% vertical drift
            speed = 0.08 * random.randrange(-1, 3, 2)
            x = random.randint(0, 1)
            drift = random.randint(0, 10) / 200 * random.randrange(-1, 3, 2)
            return self.panorama(effect=(x, 1 - x, 0.5 + drift, 0.5 - drift), speed=speed, **kwargs)
        elif random.randint(0, 1) == 0:
            speed = 0.08 * random.randrange(-1, 3, 2)
            drift = random.randint(0, 10) / 200 * random.randrange(-1, 3, 2)
            x = random.randint(0, 1)
            return self.panorama(effect=(x, 1 - x, 0.5 + drift, 0.5 - drift), speed=speed, **kwargs)
        else:
            return self.zoom(effect=__get_random_zoom__(), **kwargs)


def get_rectangle(color, w, h):
    return ImageFile(__get_background__(color)).scale(w, h, out_file="bg.tmp.jpg")


def __get_background__(color):
    bgfile = "white.jpg" if color == "white" else "black.jpg"
    return str(util.package_home() / bgfile)


def get_widths(files):
    # [ImageFile(file).width for file in files]
    return [ImageFile(file).width for file in files]


def get_heights(files):
    # [ImageFile(file).height for file in files]
    return [ImageFile(file).height for file in files]


def avg_height(files):
    values = get_heights(files)
    return sum(values) // len(values)


def avg_width(files):
    values = get_widths(files)
    return sum(values) // len(values)


def __get_layout__(nb_files, **kwargs):
    if 'rows' in kwargs and 'columns' in kwargs:
        return (int(kwargs['rows']), int(kwargs['columns']))
    if 'disposition' in kwargs:
        return [int(s) for s in kwargs['layout'].split('x')]
    rows = math.ceil(math.sqrt(nb_files))
    cols = (nb_files + rows - 1) // rows
    return (rows, cols)


def __downsize__(full_w, full_h, max_w, max_h, gap):
    full_pix = (full_w * 8 + 1024) * (full_h + 128)
    util.logger.debug("Before reduction Max W x H + G = %d x %d + %d, Total poster pixels = %d",
        max_w, max_h, gap, full_pix)

    reduction_factor = 1
    if full_pix > MAX_INT:
        util.logger.debug("Target image too big by %6.2f%%, reducing", full_pix / MAX_INT)
        reduction_factor = math.sqrt(MAX_INT / full_pix)
        if max_h != -1:
            max_h = int(reduction_factor * max_h)
        if max_w != -1:
            max_w = int(reduction_factor * max_w)
        gap = int(reduction_factor * gap)
        full_w = int(reduction_factor * full_w)
        full_h = int(reduction_factor * full_h)
    util.logger.debug("After reduction of %4.2f Max W x H + G = %d x %d + %d", reduction_factor, max_w, max_h, gap)
    return (full_w, full_h, max_w, max_h, gap, reduction_factor)


def posterize(*file_list, out_file=None, **kwargs):
    ''' Creates a poster image. Allowed parameters:
    - columns / rows
    - layout (of images eg 4x3 4 rows 3 columns)
    - background_color
    - margin (% of widest image or nb_of_pixels)
    - stretch: stretch images to be all the same width and height
    '''
    util.logger.debug("posterize(%s, %s)", str(file_list), str(kwargs))
    files = [ImageFile(f) for f in util.file_list(*file_list, file_type=util.MediaType.IMAGE_FILE)]
    fcomplex = filters.Complex(*files)

    max_w = max([f.width for f in files])
    max_h = max([f.height for f in files])

    gap = int(util.percent_or_absolute(kwargs['margin'], max_w))
    rows, cols = __get_layout__(len(fcomplex.inputs), **kwargs)

    # Max image size = ((Width * 8) + 1024)*(Height + 128) < INT_MAX
    full_w = (cols * max_w) + (cols + 1) * gap
    full_h = (rows * max_h) + (rows + 1) * gap
    if cols == 1:
        full_h = sum([f.height * max_w / f.width for f in files]) + (len(files) + 1) * gap
        max_h = -1
    if rows == 1:
        full_w = sum([f.width * max_h / f.height for f in files]) + (len(files) + 1) * gap
        max_w = -1
    util.logger.debug("Max W x H = %d x %d, gap = %d, row = %d, cols = %d", max_w, max_h, gap, rows, cols)

    (full_w, full_h, max_w, max_h, gap, red) = __downsize__(full_w, full_h, max_w, max_h, gap)

    fcomplex.insert_input(0, ImageFile(__get_background__(kwargs['background_color'])))

    img_outs = [i for i in range(len(fcomplex.inputs))]
    img_outs[0] = fcomplex.add_filtergraph([0], filters.scale(full_w, full_h))
    if kwargs.get('stretch', True):
        for i in range(1, len(fcomplex.inputs)):
            img_outs[i] = fcomplex.add_filtergraph([i], filters.scale(-1, max_h))

    y = gap
    x = gap
    out_stream = img_outs[0]
    for i in range(1, len(fcomplex.inputs)):
        if (i - 1) % cols == 0:
            x = gap
        util.logger.debug("File %d, %s - overlay(%d, %d)", i, fcomplex.inputs[i].filename, x, y)
        out_stream = fcomplex.add_filtergraph([out_stream, img_outs[i]], filters.overlay(x, y))
        if rows == 1:
            x += gap + int(fcomplex.inputs[i].width / fcomplex.inputs[i].height * max_h)
        else:
            x += gap + max_w
        if cols == 1:
            y += gap + int(fcomplex.inputs[i].height / fcomplex.inputs[i].width * max_w)
        elif i % cols == 0:
            y += gap + max_h

    out_file = util.automatic_output_file_name(out_file, files[0].filename, "poster")
    util.run_ffmpeg('{} {} -map "[{}]" "{}"'.format(fcomplex.format_inputs(), str(fcomplex), out_stream, out_file))
    return out_file


def stack(*files, out_file=None, **kwargs):
    util.logger.debug("stack(%s, %s)", str(files), str(kwargs))
    out_file = util.automatic_output_file_name(out_file, files[0], "stack")
    files_to_stack = util.file_list(*files, file_type=util.MediaType.IMAGE_FILE)
    rows, cols = 1, 1
    if kwargs['direction'] == 'vertical':
        rows = len(files_to_stack)
    else:
        cols = len(files_to_stack)
    return posterize(*files_to_stack, out_file=out_file, rows=rows, columns=cols, **kwargs)


def __get_random_panorama__():
    xstart = 0
    xstop = 0
    r = random.randint(0, 4)
    if r == 0:
        (ystart, ystop) = (0.1, 0.9)
    elif r == 1:
        (ystart, ystop) = (0.9, 0.1)
    else:
        (ystart, ystop) = (0.5, 0.5)
    r = random.randint(0, 4)
    if r == 0 and ystart != 0.5:
        (xstart, xstop) = (0.5, 0.5)
    elif r in (1, 2):
        (xstart, xstop) = (0.9, 0.1)
    else:
        (xstart, xstop) = (0.1, 0.9)

    return (xstart, xstop, ystart, ystop)


def __get_random_zoom__(zmin=100, zmax=150):
    rmin = zmin + 10 * random.randint(0, 2)
    rmax = zmax - 10 * random.randint(0, 2)
    if rmax - rmin < 20:
        rmin -= 10
        rmax += 10

    if random.randint(0, 1) == 0:
        return (rmin, rmax)
    return (rmax, rmin)


def __panorama_bounds__(img_x, img_y, video_x, video_y, duration):
    bound = 0
    if (img_x / img_y) > 1.2 * (video_x / video_y):
        bound = (1 - (video_x * (1 + duration * 0.02)) / img_x) / 2
    return bound


def __find_tag__(stream, taglist):
    for tag in stream:
        if tag not in taglist:
            continue
        return stream[tag]
    return None
