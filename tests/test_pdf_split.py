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

from mediatools import pdf_split


def test_output_pattern_width():
    assert pdf_split.output_pattern("foo.pdf", 1) == "foo.page_%01d.pdf"
    assert pdf_split.output_pattern("foo.pdf", 9) == "foo.page_%01d.pdf"
    assert pdf_split.output_pattern("foo.pdf", 10) == "foo.page_%02d.pdf"
    assert pdf_split.output_pattern("foo.pdf", 99) == "foo.page_%02d.pdf"
    assert pdf_split.output_pattern("foo.pdf", 100) == "foo.page_%03d.pdf"
    assert pdf_split.output_pattern(os.path.join("a.b", "foo.bar.pdf"), 12) == os.path.join("a.b", "foo.bar.page_%02d.pdf")


@pytest.mark.skipif(pdf_split.find_ghostscript() is None, reason="Ghostscript not installed")
def test_split(tmp_path):
    gs = pdf_split.find_ghostscript()
    src = str(tmp_path / "foo.pdf")
    # Generate a 12 pages PDF
    ps_code = "/Helvetica findfont 20 scalefont setfont 1 1 12 {pop 50 50 moveto (x) show showpage} for"
    subprocess.run([gs, "-q", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", f"-sOutputFile={src}", "-c", ps_code], check=True)
    assert pdf_split.split(src) == 12
    expected = sorted(f"foo.page_{i:02d}.pdf" for i in range(1, 13))
    assert sorted(f for f in os.listdir(tmp_path) if ".page_" in f) == expected


@pytest.mark.skipif(pdf_split.find_ghostscript() is None, reason="Ghostscript not installed")
@pytest.mark.parametrize("ppp", [150, 300, 600])
def test_split_ppp(tmp_path, ppp):
    gs = pdf_split.find_ghostscript()
    src = str(tmp_path / "bar.pdf")
    ps_code = "/Helvetica findfont 20 scalefont setfont 1 1 2 {pop 50 50 moveto (x) show showpage} for"
    subprocess.run([gs, "-q", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", f"-sOutputFile={src}", "-c", ps_code], check=True)
    assert pdf_split.split(src, ppp) == 2
    assert os.path.isfile(str(tmp_path / "bar.page_1.pdf"))


def test_ppp_presets():
    assert pdf_split.PPP_PRESETS == {150: "ebook", 300: "printer", 600: "prepress"}
    assert pdf_split.DEFAULT_PPP == 150
