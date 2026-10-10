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

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import pdf_merge, pdf_split

HAS_GS = pdf_split.find_ghostscript() is not None


def _make_pdf(path: Path, nb_pages: int) -> None:
    ps_code = f"/Helvetica findfont 20 scalefont setfont 1 1 {nb_pages} {{pop 50 50 moveto (x) show showpage}} for"
    subprocess.run(
        [pdf_split.find_ghostscript(), "-q", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", f"-sOutputFile={path}", "-c", ps_code], check=True
    )


def test_default_output():
    assert pdf_merge.default_output([str(Path("a") / "x.pdf"), "y.pdf"]) == str(Path("a") / "merged.pdf")


def test_no_input():
    with pytest.raises(ValueError):
        pdf_merge.merge([])


def test_output_is_input(tmp_path):
    src = tmp_path / "a.pdf"
    src.write_bytes(b"x")
    with pytest.raises(ValueError):
        pdf_merge.merge([str(src)], str(src))


def test_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        pdf_merge.merge([str(tmp_path / "nope.pdf")], str(tmp_path / "out.pdf"))


def test_no_ghostscript(tmp_path):
    src = tmp_path / "a.pdf"
    src.write_bytes(b"x")
    with mock.patch("mediatools.pdf_merge.find_ghostscript", return_value=None):
        with pytest.raises(RuntimeError):
            pdf_merge.merge([str(src)], str(tmp_path / "out.pdf"))


def test_merge_command(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    with mock.patch("mediatools.pdf_merge.find_ghostscript", return_value="gs"), mock.patch("subprocess.run") as run:
        out = pdf_merge.merge([str(a), str(b)])
    assert out == str(tmp_path / "merged.pdf")
    cmd = run.call_args[0][0]
    assert cmd[0] == "gs"
    assert f"-sOutputFile={out}" in cmd
    assert cmd[-2:] == [str(a), str(b)]


def test_merge_sorts_inputs(tmp_path):
    files = [tmp_path / n for n in ("c.pdf", "a.pdf", "10.pdf", "b.pdf", "2.pdf")]
    for f in files:
        f.write_bytes(b"x")
    with mock.patch("mediatools.pdf_merge.find_ghostscript", return_value="gs"), mock.patch("subprocess.run") as run:
        pdf_merge.merge([str(f) for f in files], str(tmp_path / "out.pdf"))
    merged_order = [Path(f).name for f in run.call_args[0][0][-5:]]
    assert merged_order == ["10.pdf", "2.pdf", "a.pdf", "b.pdf", "c.pdf"]


def test_main_error(tmp_path, capsys):
    with mock.patch.object(sys, "argv", ["pdf-merge", "-i", str(tmp_path / "nope.pdf")]):
        with pytest.raises(SystemExit) as e:
            pdf_merge.main()
    assert e.value.code == 1
    assert "not found" in capsys.readouterr().out


def test_main(tmp_path, capsys):
    a = tmp_path / "a.pdf"
    a.write_bytes(b"x")
    out = tmp_path / "out.pdf"
    with mock.patch.object(sys, "argv", ["pdf-merge", "-i", str(a), "-o", str(out)]), mock.patch("mediatools.pdf_merge.merge", return_value=str(out)):
        pdf_merge.main()
    assert "Merged 1 files" in capsys.readouterr().out


@pytest.mark.skipif(not HAS_GS, reason="Ghostscript not installed")
def test_merge(tmp_path):
    a, b, c = tmp_path / "a.pdf", tmp_path / "b.pdf", tmp_path / "c.pdf"
    _make_pdf(a, 2)
    _make_pdf(b, 3)
    _make_pdf(c, 1)
    out = tmp_path / "all.pdf"
    # Unsorted input: the merge sorts them
    assert pdf_merge.merge([str(c), str(a), str(b)], str(out)) == str(out)
    assert pdf_split.page_count(pdf_split.find_ghostscript(), str(out)) == 6
