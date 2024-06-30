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
import setuptools
import mediatools.version as version


with open("README.md", "r") as fh:
    long_description = fh.read()
setuptools.setup(
    name='audio-video-tools',
    version=version.MEDIA_TOOLS_VERSION,
    scripts=['audio-video-tools'],
    author="Olivier Korach",
    author_email="olivier.korach@gmail.com",
    description="A collection of utility scripts to manipulate media files (audio, video, image)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/okorach/audio-video-tools",
    project_urls={
        "Bug Tracker": "https://github.com/okorach/audio-video-tools/issues",
        "Documentation": "https://github.com/okorach/audio-video-tools/README.md",
        "Source Code": "https://github.com/okorach/audio-video-tools",
    },
    packages=setuptools.find_packages(),
    package_data={
        "mediatools": ["LICENSE", "media-tools.properties", "black.jpg", "white.jpg", "video-720p.mp4"]
    },
    install_requires=[
        'argparse',
        'datetime',
        'mp3_tagger',
        'ffmpeg-python',
        'ExifRead',
        'pyexiftool',
        'jprops'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'video-encode = mediatools.encode:main',
            'media-specs = mediatools.filespecs:main',
            'video-speed = mediatools.speed:main',
            'image-poster = mediatools.poster:main',
            'image-blinds = mediatools.blindify:main',
            'image-shake = mediatools.shake:main',
            'image-scale = mediatools.rescale:main',
            'image-stack = mediatools.stack:main',
            'video-mux = mediatools.mux:main',
            'video-concat = mediatools.concat:main',
            'media-crop = mediatools.crop:main',
            'media-volume = mediatools.volume:main',
            'media-cut = mediatools.cut:main',
            'video-stabilize = mediatools.deshake:main',
            'audio-album-art = mediatools.album_art:main',
            'image-to-video = mediatools.image2video:main',
            'video-slideshow = mediatools.slideshow:main',
            'video-reverse = mediatools.reverse:main',
            'video-metadata = mediatools.metadata:main',
            'audio-lib = mediatools.audio_lib:main',
            'audio-list = mediatools.audio_list:main',
            'linker = mediatools.linker:main',
            'renamer = mediatools.renamer:main',
            'datefixer = mediatools.datefixer:main',
            'encode = mediatools.encodeauto:main'
        ]
    },
    python_requires='>=3.6',
)
