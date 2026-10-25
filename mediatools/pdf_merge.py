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
If no output file is specified, the merged file is named after the first input file with a "_merged" postfix:
foo1.pdf foo2.pdf foo3.pdf are merged into foo1_merged.pdf
"""

import argparse
import subprocess
import sys
from pathlib import Path

from mediatools import log
import mediatools.utilities as util
from mediatools.pdf_split import find_ghostscript, GS_BINARIES, PDF_EXTENSIONS

MERGED_POSTFIX = "_merged"


def default_output(pdf_files: list) -> str:
    """Returns the default output file: the first input file with a _merged postfix (foo1.pdf -> foo1_merged.pdf)"""
    first = Path(pdf_files[0])
    return str(first.with_name(f"{first.stem}{MERGED_POSTFIX}{first.suffix}"))


def merge(pdf_files: list, out_file: str | None = None) -> str:
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
    subprocess.run(cmd, check=True)
    return out_file


def main() -> None:
    """Entry point of the pdf-merge command"""
    parser = argparse.ArgumentParser(description="Merges several PDF files into 1 PDF file (requires Ghostscript)")
    util.add_input_args(parser, "Input PDF files and/or directories, the PDF files they contain being included (merged in lexicographic order)")
    util.add_output_args(parser, "Output PDF file (default: first input file with a _merged postfix)")
    args = parser.parse_args()
    try:
        input_files = util.expand_input_files(args.inputfiles, extensions=PDF_EXTENSIONS)
        out = merge(input_files, args.outputfile)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as e:
        log.logger.error("%s", e)
        sys.exit(1)
    log.logger.info("Merged %d files into %s", len(input_files), out)


if __name__ == "__main__":
    main()
