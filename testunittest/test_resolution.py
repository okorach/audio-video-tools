import unittest
import mediatools.resolution as res


class TestResolution(unittest.TestCase):

    def test_720p(self):
        self.assertEqual(res.canonical('720p'), '1280x720')

    def test_1080p(self):
        self.assertEqual(res.canonical('1080p'), '1920x1080')

    def test_4K(self):
        self.assertEqual(res.canonical('4k'), '3840x2160')


if __name__ == '__main__':
    import xmlrunner

    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output='test-reports'),
        failfast=False,
        buffer=False,
        catchbreak=False)
