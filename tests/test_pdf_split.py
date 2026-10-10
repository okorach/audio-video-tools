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
import sys
import subprocess

from pathlib import Path
from unittest import mock

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


def _gs_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> mock.Mock:
    return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)


def test_find_ghostscript() -> None:
    """The first Ghostscript binary found on the PATH is returned"""
    with mock.patch("shutil.which", side_effect=lambda b: "/bin/gs" if b == "gs" else None):
        assert pdf_split.find_ghostscript() == "/bin/gs"
    with mock.patch("shutil.which", return_value=None):
        assert pdf_split.find_ghostscript() is None


def test_page_count_mocked() -> None:
    """The page count is read from the Ghostscript output, with the path escaped in PostScript"""
    with mock.patch("subprocess.run", return_value=_gs_result(stdout="12\n")) as run:
        assert pdf_split.page_count("gs", "C:\\dir\\fo(o).pdf") == 12  # noqa: PLR2004
    assert "(C:/dir/fo\\(o\\).pdf)" in run.call_args[0][0][-1]


def test_page_count_error() -> None:
    """A Ghostscript failure is reported"""
    with mock.patch("subprocess.run", return_value=_gs_result(returncode=1, stderr="boom")), pytest.raises(RuntimeError, match="boom"):
        pdf_split.page_count("gs", "foo.pdf")


def test_split_mocked() -> None:
    """The split command uses the page count to size the page numbers and the ppp to select the preset"""
    with (
        mock.patch("mediatools.pdf_split.find_ghostscript", return_value="gs"),
        mock.patch("mediatools.pdf_split.page_count", return_value=120),
        mock.patch("subprocess.run") as run,
    ):
        assert pdf_split.split("foo.pdf", 300) == 120  # noqa: PLR2004
    cmd = run.call_args[0][0]
    assert "-dPDFSETTINGS=/printer" in cmd
    assert "-sOutputFile=foo.page_%03d.pdf" in cmd
    assert cmd[-1] == "foo.pdf"


def test_split_no_ghostscript() -> None:
    """A missing Ghostscript is reported"""
    with mock.patch("mediatools.pdf_split.find_ghostscript", return_value=None), pytest.raises(RuntimeError, match="Ghostscript not found"):
        pdf_split.split("foo.pdf")


def test_main_mocked(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """main() splits the file with the requested ppp"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"x")
    with (
        mock.patch.object(sys, "argv", ["pdf-split", "-i", str(src), "--ppp", "600"]),
        mock.patch("mediatools.pdf_split.split", return_value=3) as split,
    ):
        pdf_split.main()
    split.assert_called_once_with(str(src), 600)
    assert "3 files" in capsys.readouterr().out


def test_main_missing_file(tmp_path: Path) -> None:
    """main() exits with 1 if the input file does not exist"""
    with mock.patch.object(sys, "argv", ["pdf-split", "-i", str(tmp_path / "nope.pdf")]), pytest.raises(SystemExit) as e:
        pdf_split.main()
    assert e.value.code == 1


def test_main_error(tmp_path: Path) -> None:
    """main() exits with 1 if the split fails"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"x")
    with (
        mock.patch.object(sys, "argv", ["pdf-split", "-i", str(src)]),
        mock.patch("mediatools.pdf_split.split", side_effect=RuntimeError("boom")),
        pytest.raises(SystemExit) as e,
    ):
        pdf_split.main()
    assert e.value.code == 1
