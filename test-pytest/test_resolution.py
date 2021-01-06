
import mediatools.resolution as res


def test_canonical_1():
    assert res.canonical('720p') == '1280x720'


def test_canonical_2():
    assert res.canonical('1080p') == '1920x1080'


def test_canonical_3():
    assert res.canonical('4k') == '3840x2160'


def test_canonical_4():
    assert res.canonical('4k') == '3840x2160'
