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

"""Merges several PDF files into a single PDF file, using Ghostscript.

The input files are merged in lexicographic order of their names, whatever the order in which they are given:
pdf-merge -i b.pdf a.pdf -o merged.pdf puts the pages of a.pdf first
If no output file is specified, the merged file is <dir of first input>/merged.pdf
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

from mediatools import log
from mediatools.pdf_split import find_ghostscript, GS_BINARIES

DEFAULT_OUTPUT = "merged.pdf"


def default_output(pdf_files: list) -> str:
    """Returns the default output file: merged.pdf in the directory of the first input file"""
    return str(Path(pdf_files[0]).parent / DEFAULT_OUTPUT)


def merge(pdf_files: list, out_file: Optional[str] = None) -> str:
    """Merges PDF files, in lexicographic order, into out_file. Returns the output file name"""
    if len(pdf_files) < 1:
        raise ValueError("At least 1 input file is required")
    pdf_files = sorted(pdf_files)
    out_file = out_file or default_output(pdf_files)
    resolved_out = Path(out_file).resolve()
    if any(Path(f).resolve() == resolved_out for f in pdf_files):
        raise ValueError(f"Output file {out_file} is also an input file")
    for f in pdf_files:
        if not Path(f).is_file():
            raise FileNotFoundError(f"File {f} not found")
    gs = find_ghostscript()
    if gs is None:
        raise RuntimeError("Ghostscript not found on PATH (looked for " + ", ".join(GS_BINARIES) + ")")
    cmd = [gs, "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-dQUIET", f"-sOutputFile={out_file}", *pdf_files]
    subprocess.run(cmd, check=True)  # noqa: S603
    return out_file


def main() -> None:
    """Entry point of the pdf-merge command"""
    parser = argparse.ArgumentParser(description="Merges several PDF files into 1 PDF file (requires Ghostscript)")
    parser.add_argument("-i", "--inputfiles", required=True, nargs="+", help="Input PDF files (merged in lexicographic order)")
    parser.add_argument("-o", "--outputfile", required=False, default=None, help=f"Output PDF file (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()
    try:
        out = merge(args.inputfiles, args.outputfile)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as e:
        log.logger.error("%s", e)
        sys.exit(1)
    log.logger.info("Merged %d files into %s", len(args.inputfiles), out)


if __name__ == "__main__":
    main()
