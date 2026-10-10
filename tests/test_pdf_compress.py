#!python3
#
# media-tools
# Copyright (C) 2019-2025 Olivier Korach
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
import subprocess

import pytest

from mediatools import pdf_compress, pdf_split


def test_original_file():
    assert pdf_compress.original_file("foo.pdf") == "foo_original.pdf"
    assert pdf_compress.original_file(os.path.join("a.b", "foo.bar.pdf")) == os.path.join("a.b", "foo.bar_original.pdf")


def _make_pdf(path):
    gs = pdf_split.find_ghostscript()
    ps_code = "/Helvetica findfont 20 scalefont setfont 1 1 3 {pop 50 50 moveto (x) show showpage} for"
    subprocess.run([gs, "-q", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", f"-sOutputFile={path}", "-c", ps_code], check=True)


@pytest.mark.skipif(pdf_split.find_ghostscript() is None, reason="Ghostscript not installed")
@pytest.mark.parametrize("ppp", [150, 300, 600])
def test_compress(tmp_path, ppp):
    src = str(tmp_path / "foo.pdf")
    _make_pdf(src)
    orig_size = os.path.getsize(src)
    assert pdf_compress.compress(src, ppp=ppp) == src
    assert os.path.getsize(src) > 0
    assert os.path.getsize(str(tmp_path / "foo_original.pdf")) == orig_size
    assert sorted(os.listdir(tmp_path)) == ["foo.pdf", "foo_original.pdf"]


@pytest.mark.skipif(pdf_split.find_ghostscript() is None, reason="Ghostscript not installed")
def test_compress_explicit_output(tmp_path):
    src = str(tmp_path / "foo.pdf")
    out = str(tmp_path / "small.pdf")
    _make_pdf(src)
    assert pdf_compress.compress(src, out) == out
    assert sorted(os.listdir(tmp_path)) == ["foo.pdf", "small.pdf"]


@pytest.mark.skipif(pdf_split.find_ghostscript() is None, reason="Ghostscript not installed")
def test_compress_does_not_overwrite_original(tmp_path):
    src = tmp_path / "foo.pdf"
    _make_pdf(str(src))
    backup = tmp_path / "foo_original.pdf"
    backup.write_bytes(b"precious")
    with pytest.raises(RuntimeError):
        pdf_compress.compress(str(src))
    assert backup.read_bytes() == b"precious"
    assert sorted(os.listdir(tmp_path)) == ["foo.pdf", "foo_original.pdf"]
