#!/usr/local/bin/python3

import ffmpeg
import mediatools.utilities as util
import mediatools.mediafile as media

class ImageFile(media.MediaFile):
    def __init__(self, filename):
        self.width = None
        self.height = None
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
        super(ImageFile, self).get_specs()
        self.get_image_specs()
        return self.specs

    def get_image_specs(self):
        util.debug(2, "Getting image specs")
        for stream in self.specs['streams']:
            if stream['codec_name'] == 'mjpeg':
                try:
                    util.debug(2, "Found stream %s" % str(stream))
                    self.width = stream['codec_width']
                    self.height = stream['codec_duration']
                    self.format = stream['codec_name']
                except KeyError as e:
                    util.debug(1, "Stream %s has no key %s\n%s" % (str(stream), e.args[0], str(stream)))

    def get_image_properties(self):
        self.get_image_specs()
        return { 'format':self.format, 'width':self.width, 'height': self.height }

def rescale(image_file, width, height, out_file = None):
    if out_file is None:
        out_file = util.add_postfix(image_file, "%dx%d" % (width, height))
    stream = ffmpeg.input(image_file)
    stream = ffmpeg.filter_(stream, 'scale', size= "%d:%d" % (width, height))
    stream = ffmpeg.output(stream, out_file)
    ffmpeg.run(stream, cmd=util.get_ffmpeg(), capture_stdout=True, capture_stderr=True)
    return out_file
