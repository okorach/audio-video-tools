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

import os
import math
import re
import random

import mediatools.utilities as util
import mediatools.mediafile as media
import mediatools.filters as filters

INPUT_FILE_FMT =  ' -i "%s"'
STEP_FMT = "[step%d]; "
OVERLAY_0_FMT = "[%d][pip0]overlay=0:0" + STEP_FMT
OVERLAY_N_FMT = "[step%d][pip%d]overlay=%d:%d"

# ET blah blah blah et bla bla bli
class ImageFile(media.MediaFile):

    SUPPORTED_IMG_CODECS = ('mjpeg', 'png', 'gif')

    def __init__(self, filename):
        self.width = None
        self.height = None
        self.pixels = None
        self.ratio = None

        super(ImageFile, self).__init__(filename)
        self.probe()

    def get_properties(self):
        '''Returns file media properties as a dict'''
        all_props = self.get_file_properties()
        all_props.update(self.get_image_properties())
        util.logger.debug("Returning image props %s\nObject %s", str(all_props), str(vars(self)))
        return all_props

# ET blah blah blah et bla bla bli

    def probe(self):
        if self.specs is not None:
            return
        super(ImageFile, self).probe()
        stream = self.__get_stream_by_codec__('codec_name', ImageFile.SUPPORTED_IMG_CODECS)
        self.format = stream['codec_name']
        self.width = int(util.find_key(stream, ('width', 'codec_width', 'coded_width')))
        self.height = int(util.find_key(stream, ('height', 'codec_height', 'coded_height')))
        self.pixels = self.width * self.height
        self.ratio = self.width / self.height
        util.logger.debug("Image = %s", str(vars(self)))

    def get_dimensions(self):
        return (self.width, self.height)

    def get_ratio(self):
        return self.width / self.height


# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli

    def get_image_properties(self):
        return { 'format':self.format, 'width':self.width, 'height': self.height, 'pixels': self.pixels  }

# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli

    def crop(self, w, h, x, y, out_file = None):
        util.logger.debug("%s(->%s, %d, %d, %d, %d)", 'crop', self.filename, w, h, x, y)
        out_file = util.automatic_output_file_name(out_file, self.filename, "crop.%dx%d" % (w, h))
        # ffmpeg -i input.png -vf  "crop=w:h:x:y" input_crop.png
        util.run_ffmpeg(('-y ' + INPUT_FILE_FMT + ' -vf crop=%d:%d:%d:%d "%s"') % (self.filename, w, h, x, y, out_file))

# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli

    def resize(self, width = None, height = None, out_file = None):
        '''Resizes an image file
        If one of width or height is None, then it is calculated to
        preserve the image aspect ratio'''
        if width is None and height is None:
            util.logger.error("Resize requested with neither width not height")
            return None
        if isinstance(width, str):
            width = int(width)
        if isinstance(height, str):
            height = int(height)
        if width is None:
            w, h = self.get_dimensions()
            width = w * height // h
        elif height is None:
            w, h = self.get_dimensions()
            height = h * width // w
        util.logger.debug("Resizing %s to %d x %d into %s", self.filename, width, height, out_file)
        out_file = util.automatic_output_file_name(out_file, self.filename, "resized-%dx%d" % (width, height))
        util.run_ffmpeg((INPUT_FILE_FMT+ ' -vf scale=%d:%d "%s"') % (self.filename, width, height, out_file))
        return out_file

    def slice_vertical(self, nbr_slices, round_to = 16, slice_pattern = 'slice'):
        w, h = self.get_dimensions()
        slice_w = max(w // nbr_slices, round_to)
        slices = []
        nbr_slices = min(nbr_slices, (w // slice_w)+1)
        for i in range(nbr_slices):
            slicefile = util.add_postfix(self.filename, "%s.%d" % (slice_pattern, i))
            self.crop(slice_w, h, i*slice_w, 0, slicefile)
            slices.append(slicefile)
        return slices

    def slice_horizontal(self, nbr_slices, round_to = 16, slice_pattern = 'slice'):
        w, h = self.get_dimensions()
        slice_h = max(h // nbr_slices, round_to)
        slices = []
        nbr_slices = min(nbr_slices, (h // slice_h)+1)
        for i in range(nbr_slices):
            slicefile = util.add_postfix(self.filename, "%s.%d" % (slice_pattern, i))
            self.crop(w, slice_h, 0, i * slice_h, slicefile)
            slices.append(slicefile)
        return slices

    def slice(self, nbr_slices, direction = 'vertical', round_to = 16, slice_pattern = 'slice'):
        if direction == 'horizontal':
            return self.slice_horizontal(nbr_slices, round_to, slice_pattern)
        else:
            return self.slice_vertical(nbr_slices, round_to, slice_pattern)

    def crop_any(self, width_height_ratio = "1.5", align = "center", out_file = None):
        if re.match(r"^\d+:\d+$", width_height_ratio):
            a, b = re.split(r':', width_height_ratio)
            ratio = float(a)/float(b)
        else:
            ratio = float(width_height_ratio)

        w, h = self.get_dimensions()
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
                y = h-crop_h
            else:
                x = w-crop_w
        elif align == 'center':
            if ratio > current_ratio:
                y = (h-crop_h)//2
            else:
                x = (w-crop_w)//2

        self.crop(crop_w, crop_h, x, y, out_file)

    def blindify(self, out_file = None, **kwargs):
        nbr_slices = int(kwargs.pop('blinds', 10))
        blinds_size_pct = int(kwargs.pop('blinds_ratio', 3))
        background_color = kwargs.pop('background_color', 'black')
        direction = kwargs.pop('direction', 'vertical')
        w, h = self.get_dimensions()

        w_gap = w * blinds_size_pct // 100
        h_gap = h * blinds_size_pct // 100

        if direction == 'horizontal':
            tmpbg = get_rectangle(background_color, w, (h//nbr_slices*nbr_slices) + h_gap*(nbr_slices-1))
        else:
            tmpbg = get_rectangle(background_color, (w//nbr_slices*nbr_slices) + w_gap*(nbr_slices-1), h)

        # ffmpeg -i file1.jpg -i file2.jpg -i bg.tmp.jpg \
        # -filter_complex "[0]scale=iw:-1:flags=lanczos[pip0]; \
        # [1]scale=iw:-1:flags=lanczos[pip1]; \
        # [8]scale=iw:-1:flags=lanczos[pip8]; \
        # [9][pip0]overlay=204:204[step0] ; \
        # [step0][pip1]overlay=2456:204[step1]; \
        # [step7][pip8]overlay=4708:3374" outfile.jpg

        slices = self.slice(nbr_slices, direction)
        filelist = util.build_ffmpeg_file_list(slices)
        filelist = filelist + INPUT_FILE_FMT % tmpbg
        cmplx = util.build_ffmpeg_complex_prep(slices)

        #i = 0
        #cmplx = ''
        #for slicefile in slices:
        #    cmplx = cmplx + "[%d]scale=iw:-1:flags=lanczos[pip%d]; " % (i, i)
        #    i = i + 1

        step = 0
        cmplx = cmplx + OVERLAY_0_FMT % (len(slices), step)
        first_slice = slices.pop(0)
        j = 0
        x = 0
        y = 0
        for slicefile in slices:
            if direction == 'horizontal':
                y = (j+1) * (h // nbr_slices + h_gap)
            else:
                x = (j+1) * (w // nbr_slices + w_gap)
            cmplx = cmplx + OVERLAY_N_FMT % (j, j+1, x, y)
            if slicefile != slices[len(slices)-1]:
                cmplx = cmplx + STEP_FMT % (j+1)
            j = j+1

        out_file = util.automatic_output_file_name(out_file, self.filename, "blind")
        util.run_ffmpeg('%s -filter_complex "%s" %s' % (filelist, cmplx, out_file))
        util.delete_files(*slices, first_slice, tmpbg)

    def shake_vertical(self, nbr_slices = 10 , shake_pct = 3, background_color = "black", out_file = None):
        w, h = self.get_dimensions()
        h_jitter = h * shake_pct // 100
        slice_width = max(w // nbr_slices, 16)
        slices = self.slice_vertical(nbr_slices)
        tmpbg = get_rectangle(background_color, slice_width * len(slices), h + h_jitter)
        filelist = util.build_ffmpeg_file_list(slices) + INPUT_FILE_FMT % tmpbg
        cmplx = util.build_ffmpeg_complex_prep(slices)

        step = 0
        n_slices = len(slices)
        cmplx = cmplx + OVERLAY_0_FMT % (n_slices, step)
        first_slice = slices.pop(0)

        for j in range(n_slices):
            x = (j+1) * slice_width
            y = random.randint(1, h_jitter)
            cmplx = cmplx + OVERLAY_N_FMT % (j, j+1, x, y)
            if j < n_slices-1:
                cmplx = cmplx + STEP_FMT % (j+1)
            j = j+1
        out_file = util.automatic_output_file_name(out_file, self.filename, "shake")
        util.run_ffmpeg(' %s -filter_complex "%s" "%s"' % (filelist, cmplx, out_file))
        util.delete_files(*slices, first_slice, tmpbg)
        return out_file

    def shake_horizontal(self, nbr_slices = 10 , shake_pct = 3, background_color = "black", out_file = None):
        w, h = self.get_dimensions()
        w_jitter = w * shake_pct // 100
        slice_height = max(h // nbr_slices, 16)
        slices = self.slice_horizontal(nbr_slices)
        tmpbg = get_rectangle(background_color, w + w_jitter, slice_height * len(slices))
        filelist = util.build_ffmpeg_file_list(slices) + INPUT_FILE_FMT % tmpbg
        cmplx = util.build_ffmpeg_complex_prep(slices)

        step = 0
        n_slices = len(slices)
        cmplx = cmplx + OVERLAY_0_FMT % (n_slices, step)
        first_slice = slices.pop(0)

        for j in range(n_slices):
            x = random.randint(1, w_jitter)
            y = (j+1) * slice_height
            cmplx = cmplx + OVERLAY_N_FMT % (j, j+1, x, y)
            if j < n_slices-1:
                cmplx = cmplx + STEP_FMT % (j+1)
            j = j+1

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
        (zstart, zstop) = list(map(lambda x: max(x, 100), kwargs.get('effect', (100, 130))))
        fps = int(kwargs.get('framerate', 50))
        duration = float(kwargs.get('duration', 5))
        resolution = kwargs.get('resolution', media.Resolution.DEFAULT_VIDEO)
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
            zformula = "if(lte(zoom,1.0),{},max({}+0.001,zoom-{}))".format(zstart/100, zstop/100, step)
        else:
            zformula = "min(zoom+{},{})".format(step, zstop/100)
        vfilters.append(
            filters.zoompan("iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", zformula, d=int(duration * fps), fps=fps))
        vfilters.append(filters.trim(duration=duration))
        cmd = "-i \"{}\" -framerate {} -filter_complex \"[0:v]{}[v]\" -map \"[v]\" -s {} \"{}\"".format(
            self.filename, fps, ','.join(vfilters), resolution, out_file)
        util.run_ffmpeg(cmd)
        return out_file

    def __compute_upscaling_for_video__(self, video_res):
        u_res = media.Resolution(resolution=media.Resolution.RES_4K)
        if self.ratio >= video_res.ratio * 1.2:
            u_res.width = int(u_res.height * self.ratio)
        elif self.ratio >= video_res.ratio:
            u_res.height = int(u_res.height, 1.3)
            u_res.width = int(u_res.height * self.ratio)
        elif self.ratio >= video_res.ratio / 1.3:
            u_res.width = int(u_res.width * 1.5)
            u_res.height = int(u_res.width  / self.ratio)
        else:
            u_res.height = int(u_res.width / self.ratio)
        return u_res

    def panorama(self, **kwargs):
        out_file = kwargs.get('out_file', None)
        (xstart, xstop, ystart, ystop) = kwargs.get('effect', (0, 1, 0.5, 0.5))
        framerate = kwargs.get('framerate', 50)
        duration = kwargs.get('duration', 5)
        v_res = media.Resolution(resolution=kwargs.get('resolution', media.Resolution.DEFAULT_VIDEO))
        # Filters used for panorama are incompatible with hw acceleration
        # hw_accel = kwargs.get('hw_accel', False)
        hw_accel = False

        util.logger.debug("panorama(%5.2f,%5.2f,%5.2f,%5.2f) of image %s", xstart, xstop, ystart, ystop, self.filename)
        vfilters = []
        u_res = self.__compute_upscaling_for_video__(v_res)
        vfilters.append(filters.scale(u_res.width, u_res.height))

        if self.ratio >= v_res.ratio * 1.2:
            # if img ratio > video ratio + 20%, no vertical drift
            (ystart, ystop) = (0.5, 0.5)
            # Compute left/right bound to allow video to move only +/-2% per second of video
            bound = max(0, (u_res.width - media.RES_VIDEO_4K.width * (1 + duration * 0.02)) / 2 / u_res.width)
            if xstart < xstop:
                (xstart, xstop) = (bound, 1 - bound)
            else:
                (xstart, xstop) = (1 - bound, bound)
        elif self.ratio < v_res.ratio / 1.3:
            # if img ratio > video ratio - 30%, no horizontal drift
            (xstart, xstop) = (0.5, 0.5)
            # Compute left/right bound to allow video to move only +/-2% per second of video
            bound = max(0, (u_res.height - media.RES_VIDEO_4K.height * (1 + duration * 0.04)) / 2 / u_res.height)
            if ystart < ystop:
                (ystart, ystop) = (bound, 1 - bound)
            else:
                (ystart, ystop) = (1 - bound, bound)
        x_formula = "'(iw-ow)*({0}+{1}*t/{2})'".format(xstart, xstop - xstart, duration)
        y_formula = "'(ih-oh)*({0}+{1}*t/{2})'".format(ystart, ystop - ystart, duration)
        vfilters.append(filters.crop(media.RES_VIDEO_4K.width, media.RES_VIDEO_4K.height, x_formula, y_formula))

        out_file = util.automatic_output_file_name(out_file, self.filename, 'pan', extension="mp4")

        inputs = ''
        vcodec = ''
        if hw_accel:
            inputs += ' -hwaccel cuvid -c:v h264_cuvid'
            vcodec = '-c:v h264_nvenc'

        cmd = "-framerate {} -loop 1 {} -i \"{}\" -filter_complex \"[0:v]{}\" -t {} {} -s {} \"{}\"".format(
            framerate, inputs, self.filename, ','.join(vfilters), duration, vcodec, str(v_res), out_file)
        util.run_ffmpeg(cmd)
        return out_file

    def to_video(self, with_effect=True, resolution=media.Resolution.RES_4K, hw_accel=True):
        util.logger.info("Converting %s to video", self.filename)
        if not with_effect:
            return self.panorama(effect=(0.5, 0.5, 0.5, 0.5), resolution=resolution)

        (w, h) = self.get_dimensions()
        if w / h <= (3 / 4 + 0.00001):
            r = random.randint(0, 1)
            offset = 0.2 if w / h <= (9 / 16 + 0.00001) else 0
            r = r + offset if r == 0 else r - offset
            return self.panorama(effect=(0.5, 0.5, r, 1 - r), resolution=resolution, hw_accel=hw_accel)
        elif w / h >= (16 / 9 + 0.00001):
            r = random.randint(0, 1)
            # Allow up to 20% crop if image ratio < 9 / 16
            offset = 0.2 if w / h <= (9 / 16 + 0.00001) else 0
            r = r + offset if r == 0 else r - offset
            # Allow up to 10% vertical drift
            drift = random.randint(0, 10) / 200 * random.randrange(-1, 3, 2)
            return self.panorama(effect=(r, 1 - r, 0.5 + drift, 0.5 - drift), resolution=resolution, hw_accel=hw_accel)
        elif random.randint(0, 2) >= 2:
            return self.panorama(effect=__get_random_panorama__(), resolution=resolution, hw_accel=hw_accel)
        else:
            return self.zoom(effect=__get_random_zoom__(), resolution=resolution, hw_accel=hw_accel)

    def scale(self, w, h, scale_method="keepratio", out_file=None):
        final_ratio = w / h
        (iw, ih) = self.get_dimensions()
        x = w
        y = h
        if scale_method == 'stretch':
            pass
        elif iw / ih > final_ratio:
            y = -1
            h = ih * iw / w
        else:
            x = -1
            w = iw * ih / h

        out_file = util.automatic_output_file_name(out_file, self.filename, "scale-{}x{}".format(w, h))
        util.logger.debug("Rescaling %s to %d x %d into %s", self.filename, w, h, out_file)

        util.run_ffmpeg((INPUT_FILE_FMT + ' -vf scale=%d:%d "%s"') % (self.filename, x, y, out_file))
        return out_file


def get_rectangle(color, w, h):
    bgfile = "white-square.jpg" if color == "white" else "black-square.jpg"
    return ImageFile(bgfile).scale(w, h, out_file="bg.tmp.jpg")

def stack(file1, file2, direction, out_file = None):
    util.logger.debug("stack(%s, %s, %s, _)", file1, file2, direction)
    if not util.is_image_file(file1):
        raise media.FileTypeError('File %s is not an image file' % file1)
    if not util.is_image_file(file2):
        raise media.FileTypeError('File %s is not an image file' % file2)
    out_file = util.automatic_output_file_name(out_file, file1, "stacked")
    w1, h1 = ImageFile(file1).get_dimensions()
    w2, h2 = ImageFile(file2).get_dimensions()
    tmpfile1 = file1
    tmpfile2 = file2
    util.logger.debug("Images dimensions: %d x %d and %d x %d", w1, h1, w2, h2)
    if direction == 'horizontal':
        filter_name = 'hstack'
        if h1 > h2:
            new_w2 = w2 * h1 // h2
            tmpfile2 = ImageFile(file2).scale(new_w2, h1)
        elif h2 > h1:
            new_w1 = w1 * h2 // h1
            tmpfile1 = ImageFile(file1).scale(new_w1, h2)
    else:
        filter_name = 'vstack'
        if w1 > w2:
            new_h2 = h2 * w1 // w2
            tmpfile2 = ImageFile(file2).scale(w1, new_h2)
        elif w2 > w1:
            new_h1 = h1 * w2 // w1
            tmpfile1 = ImageFile(file1).scale(w2, new_h1)

    # ffmpeg -i a.jpg -i b.jpg -filter_complex hstack output

    util.run_ffmpeg((INPUT_FILE_FMT + INPUT_FILE_FMT + '-filter_complex %s "%s"') % (tmpfile1, tmpfile2, filter_name, out_file))
    if tmpfile1 is not file1:
        util.delete_files(tmpfile1)
    if tmpfile2 is not file2:
        util.delete_files(tmpfile2)
    return out_file

def get_widths(files):
    # [ImageFile(file).width for file in files]
    return list(map(lambda file: ImageFile(file).width, files))

def get_heights(files):
    # [ImageFile(file).height for file in files]
    return list(map(lambda file: ImageFile(file).height, files))

def min_height(files):
    return min(get_heights(files))

def min_width(files):
    return min(get_widths(files))

def max_height(files):
    return max(get_heights(files))

def max_width(files):
    return max(get_widths(files))

def avg_height(files):
    values = get_heights(files)
    return sum(values)//len(values)

def avg_width(files):
    values = get_widths(files)
    return sum(values)//len(values)

def posterize(files, posterfile=None, background_color="black", margin=5):
    min_h = max_height(files)
    min_w = max_width(files)
    util.logger.debug("Max W x H = %d x %d", min_w, min_h)
    gap = (min_w * margin) // 100

    nb_files = len(files)
    root = math.sqrt(nb_files)
    rows = int(round(root))
    if rows < root:
        rows += 1
    cols = (nb_files + rows-1) // rows

    full_w = (cols*min_w) + (cols+1)*gap
    full_h = (rows*min_h) + (rows+1)*gap

    util.logger.debug("W x H = %d x %d / Gap = %d / c,r = %d, %d => Full W x H = %d x %d",
                      min_w, min_h, gap, cols, rows, full_w, full_h)
    bgfile = "white-square.jpg" if background_color == "white" else "black-square.jpg"
    tmpbg = "bg.tmp.jpg"
    ImageFile(bgfile).scale(full_w, full_h, tmpbg)

    file_list = util.build_ffmpeg_file_list(files)

    cmplx = util.build_ffmpeg_complex_prep(files)
    cmplx = cmplx + __build_poster_fcomplex(rows, cols, gap, min_w, min_h, len(files))

    posterfile = util.automatic_output_file_name(posterfile, files[0], "poster")
    util.run_ffmpeg((INPUT_FILE_FMT + ' %s -filter_complex "%s" "%s"') % (tmpbg, file_list, cmplx, posterfile))
    util.logger.info("Generated %s", posterfile)
    util.delete_files(tmpbg)
    return posterfile

def __build_poster_fcomplex(rows, cols, gap, img_w, img_h, max_images = 10000):
    i_photo = 1
    cmplx = "[pip0][pip1]overlay=%d:%d[step1] " % (gap, gap)
    for irow in range(rows):
        for icol in range(cols):
            if irow == 0 and icol == 0:
                continue
            if i_photo >= max_images:
                continue
            i_photo += 1
            x = gap+icol*(img_w+gap)
            y = gap+irow*(img_h+gap)
            cmplx += "; [step%d][pip%d]overlay=%d:%d" % (i_photo-1, i_photo, x, y)
            if i_photo < max_images:
                cmplx += "[step%d]" % i_photo

    return cmplx


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

def __get_random_zoom__(zmin = 100, zmax = 150):
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