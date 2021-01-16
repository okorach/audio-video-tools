import os
import mediatools.imagefile as image
import mediatools.videofile as video
import mediatools.exceptions as ex

TMP_VID = "/tmp/vid.mp4"
large_img = None


def get_large_img(w, h):
    global large_img
    if large_img is not None:
        return large_img

    small_img = image.__get_background__('black')
    large_file = image.ImageFile(small_img).scale(w, h, out_file="/tmp/large.jpg")
    large_img = image.ImageFile(large_file)
    return large_img


def del_large_img():
    global large_img
    os.remove(large_img.filename)
    large_img = None


def test_scale_1():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    assert large_img.resolution.width == w
    assert large_img.resolution.height == h


def tes_needed_frame_1():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    (_, tot_w, tot_h) = large_img.__compute_total_frame__(6000, 3500)
    assert tot_w == 6000
    assert tot_h == 4500


def test_needed_frame_2():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    (_, tot_w, tot_h) = large_img.__compute_total_frame__(5000, 4500)
    assert tot_w == 6000
    assert tot_h == 4500


def test_needed_frame_3():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    (_, tot_w, tot_h) = large_img.__compute_total_frame__(3000, 3600)
    assert tot_w == 4800
    assert tot_h == 3600


def test_pan_input_1():
    large_img = get_large_img(4000, 3000)
    try:
        _ = large_img.panorama(effect=(0, 1, 0.5, 0.5), out_file=TMP_VID)
    except ex.InputError as e:
        assert e.message == "panorama: 2 arguments out of 3 mandatory in effect, duration or speed"


def test_pan_input_2():
    large_img = get_large_img(4000, 3000)
    try:
        _ = large_img.panorama(speed="10%", out_file=TMP_VID)
    except ex.InputError as e:
        assert e.message == "panorama: 2 arguments out of 3 mandatory in effect, duration or speed"


def test_pan_input_3():
    large_img = get_large_img(4000, 3000)
    try:
        _ = large_img.panorama(duration=5, out_file=TMP_VID)
    except ex.InputError as e:
        assert e.message == "panorama: 2 arguments out of 3 mandatory in effect, duration or speed"


def test_pan_input_4():
    large_img = get_large_img(4000, 3000)
    try:
        _ = large_img.panorama(duration=-5, speed=0.1, out_file=TMP_VID)
    except ex.InputError as e:
        assert e.message == "panorama: duration must be a strictly positive number"


def test_pan_input_5():
    large_img = get_large_img(4000, 3000)
    try:
        _ = large_img.panorama(duration=0, speed=0.1, out_file=TMP_VID)
    except ex.InputError as e:
        assert e.message == "panorama: duration must be a strictly positive number"


def test_pan_1():
    large_img = get_large_img(4000, 3000)
    vid = large_img.panorama(duration=5, speed="10%", resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)


def test_pan_2():
    large_img = get_large_img(4000, 3000)
    vid = large_img.panorama(effect=(0, 1, 0.5, 0.5), speed="10%", resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 10
    os.remove(vid)


def test_pan_3():
    large_img = get_large_img(4000, 3000)
    vid = large_img.panorama(effect=(0, 1, 0.5, 0.5), duration=5, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)


def test_pan_4():
    large_img = get_large_img(4000, 3000)
    vid = large_img.panorama(effect=(1, 0, 0.5, 0.5), speed=0.2, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)


def test_pan_5():
    large_img = get_large_img(4000, 3000)
    vid = large_img.to_video(with_effect=False, duration=3, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)


def test_pan_6():
    large_img = get_large_img(4000, 3000)
    vid = large_img.panorama(duration=3, speed=0.2, vspeed=0.1, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
