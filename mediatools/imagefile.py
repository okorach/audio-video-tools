#!/usr/local/bin/python3

import os
import math
import re
import random

import mediatools.utilities as util
import mediatools.mediafile as media

INPUT_FILE_FMT =  ' -i "%s"'
STEP_FMT = "[step%d]; "
OVERLAY_0_FMT = "[%d][pip0]overlay=0:0" + STEP_FMT
OVERLAY_N_FMT = "[step%d][pip%d]overlay=%d:%d"

# ET blah blah blah et bla bla bli
class ImageFile(media.MediaFile):
    def __init__(self, filename):
        self.width = None
        self.height = None
        self.pixels = None
        self.title = None
        self.author = None
        self.year = None
        self.date_created = None
        self.date_modified = None
        self.comment = None
        super(ImageFile, self).__init__(filename)

    def get_properties(self):
        '''Returns file media properties as a dict'''
        self.get_specs()
        # NOSONAR self.specs = media.get_file_specs(self.filename)
        all_props = self.get_file_properties()
        all_props.update(self.get_image_properties())
        util.logger.debug("Returning image props %s\nObject %s", str(all_props), str(vars(self)))
        return all_props

# ET blah blah blah et bla bla bli

    def get_specs(self):
        '''Reads file media properties. Probes file if not yet probed'''
        if self.specs is None:
            self.probe()
            self.get_image_specs()
        return self.specs

# ET blah blah blah et bla bla bli

    def find_width_from_stream(self, stream):
        if self.width is None:
            for tag in [ 'width', 'codec_width', 'coded_width']:
                if tag in stream:
                    util.logger.debug('Tag %s found', tag)
                    self.width = stream[tag]
                    break
        util.logger.debug('Returning image width %d', self.width)
        return self.width

    def find_height_from_stream(self, stream):
        if self.height is None:
            for tag in [ 'height', 'codec_height', 'coded_height']:
                if tag in stream:
                    util.logger.debug('Tag %s found', tag)
                    self.height = stream[tag]
                    break
        util.logger.debug('Returning image height %d', self.height)
        return self.height

# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli


    def get_dimensions(self):
        self.get_specs()
        if self.width is None or self.height is None:
            stream = self.__get_stream_by_codec__('codec_name', 'mjpeg')
            self.width = self.find_width_from_stream(stream)
            self.height = self.find_height_from_stream(stream)
        if self.width is not None and self.height is not None:
            self.pixels = self.width * self.height
        util.logger.debug("Returning dimensions %d x %d" , self.width, self.height)
        return [self.width, self.height]

# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli

    def get_width(self):
        if self.width is None:
            _, _ = self.get_dimensions()
        util.logger.debug("Returning image Width = %d", self.width)
        return self.width

# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli

    def get_height(self):
        if self.height is None:
            _, _ = self.get_dimensions()
        return self.height

# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli

    def get_image_specs(self):
        util.logger.debug("Getting image specs")
        _, _ = self.get_dimensions()
        for stream in self.specs['streams']:
            if stream['codec_name'] == 'mjpeg':
                try:
                    util.logger.debug("Found stream %s", str(stream))
                    self.format = stream['codec_name']
                except KeyError as e:
                    util.logger.error("Stream %s has no key %s\n%s", str(stream), e.args[0], str(stream))

# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli
# ET blah blah blah et bla bla bli

    def get_image_properties(self):
        self.get_image_specs()
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

    def zoom_in(self, out_file=None, initial_zoom=1, final_zoom=1.3, duration=5, framerate=50, resolution="3840x2160"):
        out_file = util.automatic_output_file_name(out_file, self.filename, 'zoom_in', extension="mp4")
        (iw, ih) = self.get_dimensions()
        #if (iw / ih) < (16 / 9):
        #    h = (iw *  9) // 16
        #    w = iw
        #else:
        #    w = (ih * 16 // 9)
        #    h = ih
        (width, height) = resolution.split("x")
        scaling = "[0:v]scale=7680:-1,crop=7680:4320" # .format(width, width, height)
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
        cmd = "-i \"{}\" -framerate {} -filter_complex \"{},zoompan=z='min(zoom+0.0015,{})':x='{}':y='{}':d=125,trim=duration={}[v]\" -map \"[v]\" -s {} \"{}\"".format(
            self.filename, framerate, scaling, final_zoom, x, y, duration, resolution, out_file)
        util.run_ffmpeg(cmd)
        return out_file

    def panorama(self, out_file=None, direction="left-to-right", duration=5, framerate=50, resolution="3840x2160"):

         # .format(width, width, height)
        scaling = "[0:v]scale=4992:-1"

        out_file = util.automatic_output_file_name(out_file, self.filename, 'pan-' + direction, extension="mp4")
        if direction in ('top-to-bottom', 'bottom-to-top'):
            x_formula = "iw-ow/2"
        elif direction in ('right-to-left', 'top-right-to-bottom-left','bottom-right-to-top-left'):
            x_formula = "'max((iw-out_w)*({0}-t)/{0},0)'".format(duration)
        else:
            x_formula = "'min((iw-ow)*t/{},iw-ow)'".format(duration)

        if direction in ('left-to-right', 'right-to-left'):
            y_formula = "ih-oh/2"
        elif direction in ('bottom-to-top', 'bottom-left-to-top-right', 'bottom-right-to-top-left'):
            y_formula = "'max((ih-oh)*({0}-t)/{0},0)'".format(duration)
        else:
            y_formula = "'min((ih-oh)*t/{},ih-oh)'".format(duration)


        cmd = "-framerate {} -loop 1 -i \"{}\" -filter_complex \"{},crop=3840:2160:{}:{}\" -t {} -s {} \"{}\"".format(
            framerate, self.filename, scaling, x_formula, y_formula, duration, resolution, out_file)
        util.run_ffmpeg(cmd)
        return out_file


def rescale(image_file, width, height, out_file = None):
    util.logger.debug("Rescaling %s to %d x %d into %s", image_file, width, height, out_file)
    # ffmpeg -i input.jpg -vf scale=320:240 output_320x240.png
    out_file = util.automatic_output_file_name(out_file, image_file, "scale-%dx%d" % (width, height))
    util.run_ffmpeg((INPUT_FILE_FMT + ' -vf scale=%d:%d "%s"') % (image_file, width, height, out_file))
    return out_file

def get_rectangle(color, w, h):
    bgfile = "white-square.jpg" if color == "white" else "black-square.jpg"
    tmpbg = "bg.tmp.jpg"
    rescale(bgfile, w, h, tmpbg)
    return tmpbg

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
            tmpfile2 = rescale(file2, new_w2, h1)
        elif h2 > h1:
            new_w1 = w1 * h2 // h1
            tmpfile1 = rescale(file1, new_w1, h2)
    else:
        filter_name = 'vstack'
        if w1 > w2:
            new_h2 = h2 * w1 // w2
            tmpfile2 = rescale(file2, w1, new_h2)
        elif w2 > w1:
            new_h1 = h1 * w2 // w1
            tmpfile1 = rescale(file1, w2, new_h1)

    # ffmpeg -i a.jpg -i b.jpg -filter_complex hstack output

    util.run_ffmpeg((INPUT_FILE_FMT + INPUT_FILE_FMT + '-filter_complex %s "%s"') % (tmpfile1, tmpfile2, filter_name, out_file))
    if tmpfile1 is not file1:
        util.delete_files(tmpfile1)
    if tmpfile2 is not file2:
        util.delete_files(tmpfile2)
    return out_file

def get_widths(files):
    values = []
    for file in files:
        values.append(ImageFile(file).get_width())
    return values

def get_heights(files):
    values = []
    for file in files:
        values.append(ImageFile(file).get_height())
    return values

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
    rescale(bgfile, full_w, full_h, tmpbg)

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
