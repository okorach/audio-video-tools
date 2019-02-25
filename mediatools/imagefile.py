#!/usr/local/bin/python3

import os
import ffmpeg
import mediatools.utilities as util
import mediatools.mediafile as media

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
        self.get_specs()
        # self.specs = media.get_file_specs(self.filename)
        all_props = self.get_file_properties()
        all_props.update(self.get_image_properties())
        util.debug(1, "Returning image props %s" % str(all_props))
        util.debug(1, "Obj %s" % str(vars(self)))
        return all_props

    def get_specs(self):
        if self.specs is None:
            self.probe()
            self.get_image_specs()
        return self.specs

    def get_dimensions(self):
        self.get_specs()
        if self.width is None or self.height is None:
            stream = self.get_stream_by_codec('codec_name', 'mjpeg')
        if self.width is None:
            for tag in [ 'width', 'codec_width', 'coded_width']:
                if tag in stream:
                    util.debug(5, 'Tag %s found' % tag)
                    self.width = stream[tag]
                    break
        if self.height is None:
            for tag in [ 'height', 'codec_height', 'coded_height']:
                if tag in stream:
                    util.debug(5, 'Tag %s found' % tag)
                    self.height = stream[tag]
                    break
        if self.width is not None and self.height is not None:
            self.pixels = self.width * self.height
        util.debug(5, "Returning %d x %d" % (self.width, self.height))
        return [self.width, self.height]

    def get_width(self):
        if self.width is None:
            _, _ = self.get_dimensions()
        return self.width

    def get_height(self):
        if self.height is None:
            _, _ = self.get_dimensions()
        return self.height

    def get_image_specs(self):
        util.debug(2, "Getting image specs")
        _, _ = self.get_dimensions()
        for stream in self.specs['streams']:
            if stream['codec_name'] == 'mjpeg':
                try:
                    util.debug(2, "Found stream %s" % str(stream))
                    self.format = stream['codec_name']
                except KeyError as e:
                    util.debug(1, "Stream %s has no key %s\n%s" % (str(stream), e.args[0], str(stream)))

    def get_image_properties(self):
        self.get_image_specs()
        return { 'format':self.format, 'width':self.width, 'height': self.height, 'pixels': self.pixels  }

def rescale(image_file, width, height, out_file = None):
    util.debug(5, "Rescaling %s to %d x %d" % (image_file, width, height))
    if out_file is None:
        out_file = util.add_postfix(image_file, "%dx%d" % (width, height))
    stream = ffmpeg.input(image_file)
    stream = ffmpeg.filter_(stream, 'scale', size= "%d:%d" % (width, height))
    stream = ffmpeg.output(stream, out_file)
    ffmpeg.run(stream, cmd=util.get_ffmpeg(), capture_stdout=True, capture_stderr=True)
    return out_file

def stack(file1, file2, direction, out_file = None):
    util.debug(1, "stack(%s, %s, %s, _)" % (file1, file2, direction))
    if not util.is_image_file(file1):
        raise media.FileTypeError('File %s is not an image file' % file1)
    if not util.is_image_file(file2):
        raise media.FileTypeError('File %s is not an image file' % file2) 
    if out_file is None:
        out_file = util.add_postfix(file1, "stacked")
    o_file1 = ImageFile(file1)
    o_file2 = ImageFile(file2)
    w1, h1 = o_file1.get_dimensions()
    w2, h2 = o_file2.get_dimensions()
    tmpfile1 = file1
    tmpfile2 = file2
    util.debug(5, "Images dimensions: %d x %d and %d x %d" % (w1, h1, w2, h2))
    if direction == 'horizontal':
        filter = 'hstack'
        if h1 > h2:
            new_w2 = w2 * h1 // h2
            tmpfile2 = rescale(file2, new_w2, h1, )
        elif h2 > h1:
            new_w1 = w1 * h2 // h1
            tmpfile1 = rescale(file1, new_w1, h2)
    else:
        filter = 'vstack'
        if w1 > w2:
            new_h2 = h2 * w1 // w2
            tmpfile2 = rescale(file2, w1, new_h2)
        elif w2 > w1:
            new_h1 = h1 * w2 // w1
            tmpfile1 = rescale(file1, w2, new_h1)

    # ffmpeg -i a.jpg -i b.jpg -filter_complex hstack output

    cmd = '%s -i "%s" -i "%s" -filter_complex %s "%s"' % (util.get_ffmpeg(), tmpfile1, tmpfile2, filter, out_file)
    util.run_os_cmd(cmd)
    if tmpfile1 is not file1:
        os.remove(tmpfile1)
    if tmpfile2 is not file2:
        os.remove(tmpfile2)
    return out_file