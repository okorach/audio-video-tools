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


def test_compress_mocked(tmp_path: Path) -> None:
    """The compressed file replaces the original, which is kept with an _original postfix"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"original")

    def fake_gs(cmd: list, check: bool) -> None:  # noqa: ARG001
        out = next(a for a in cmd if a.startswith("-sOutputFile=")).split("=", 1)[1]
        Path(out).write_bytes(b"small")

    with mock.patch("mediatools.pdf_compress.find_ghostscript", return_value="gs"), mock.patch("subprocess.run", side_effect=fake_gs) as run:
        assert pdf_compress.compress(str(src), ppp=300) == str(src)
    assert "-dPDFSETTINGS=/printer" in run.call_args[0][0]
    assert src.read_bytes() == b"small"
    assert (tmp_path / "foo_original.pdf").read_bytes() == b"original"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["foo.pdf", "foo_original.pdf"]


def test_compress_failure_keeps_original(tmp_path: Path) -> None:
    """If Ghostscript fails the original is untouched and no temporary file is left"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"original")
    with (
        mock.patch("mediatools.pdf_compress.find_ghostscript", return_value="gs"),
        mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "gs")),
        pytest.raises(subprocess.CalledProcessError),
    ):
        pdf_compress.compress(str(src))
    assert [p.name for p in tmp_path.iterdir()] == ["foo.pdf"]
    assert src.read_bytes() == b"original"


def test_compress_no_ghostscript(tmp_path: Path) -> None:
    """A missing Ghostscript is reported"""
    with mock.patch("mediatools.pdf_compress.find_ghostscript", return_value=None), pytest.raises(RuntimeError, match="Ghostscript not found"):
        pdf_compress.compress(str(tmp_path / "foo.pdf"), str(tmp_path / "out.pdf"))


def test_compress_explicit_output_mocked(tmp_path: Path) -> None:
    """With an output file the original is left alone"""
    with mock.patch("mediatools.pdf_compress.find_ghostscript", return_value="gs"), mock.patch("subprocess.run") as run:
        assert pdf_compress.compress("foo.pdf", "small.pdf") == "small.pdf"
    assert "-sOutputFile=small.pdf" in run.call_args[0][0]
    assert not (tmp_path / "foo_original.pdf").exists()


def test_main_mocked(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """main() compresses the file with the requested ppp"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"x")
    argv = ["pdf-compress", "-i", str(src), "-o", "out.pdf", "--ppp", "600"]
    with mock.patch.object(sys, "argv", argv), mock.patch("mediatools.pdf_compress.compress", return_value="out.pdf") as compress:
        pdf_compress.main()
    compress.assert_called_once_with(str(src), "out.pdf", 600)
    assert "into out.pdf" in capsys.readouterr().out


def test_main_missing_file(tmp_path: Path) -> None:
    """main() exits with 1 if the input file does not exist"""
    with mock.patch.object(sys, "argv", ["pdf-compress", "-i", str(tmp_path / "nope.pdf")]), pytest.raises(SystemExit) as e:
        pdf_compress.main()
    assert e.value.code == 1


def test_main_error(tmp_path: Path) -> None:
    """main() exits with 1 if the compression fails"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"x")
    with (
        mock.patch.object(sys, "argv", ["pdf-compress", "-i", str(src)]),
        mock.patch("mediatools.pdf_compress.compress", side_effect=RuntimeError("boom")),
        pytest.raises(SystemExit) as e,
    ):
        pdf_compress.main()
    assert e.value.code == 1


def test_compress_does_not_overwrite_original_mocked(tmp_path: Path) -> None:
    """An existing _original file is never overwritten"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"new")
    backup = tmp_path / "foo_original.pdf"
    backup.write_bytes(b"precious")
    with mock.patch("mediatools.pdf_compress.find_ghostscript", return_value="gs"), pytest.raises(RuntimeError, match="already exists"):
        pdf_compress.compress(str(src))
    assert backup.read_bytes() == b"precious"
    assert src.read_bytes() == b"new"


def test_compress_failure_removes_temporary_file(tmp_path: Path) -> None:
    """A partial temporary file left by a failing Ghostscript is removed"""
    src = tmp_path / "foo.pdf"
    src.write_bytes(b"original")

    def failing_gs(cmd: list, check: bool) -> None:  # noqa: ARG001
        out = next(a for a in cmd if a.startswith("-sOutputFile=")).split("=", 1)[1]
        Path(out).write_bytes(b"partial")
        raise subprocess.CalledProcessError(1, "gs")

    with (
        mock.patch("mediatools.pdf_compress.find_ghostscript", return_value="gs"),
        mock.patch("subprocess.run", side_effect=failing_gs),
        pytest.raises(subprocess.CalledProcessError),
    ):
        pdf_compress.compress(str(src))
    assert [p.name for p in tmp_path.iterdir()] == ["foo.pdf"]
    assert src.read_bytes() == b"original"
