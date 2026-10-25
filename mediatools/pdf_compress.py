#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
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

"""Compresses a PDF file using Ghostscript.

By default the compressed file replaces the original, which is kept with an "_original" postfix:
foo.pdf is compressed into foo.pdf and the original file is renamed foo_original.pdf
If an output file is specified, the original file is left untouched.
"""

import os
from pathlib import Path
import subprocess
import sys
import argparse

from mediatools import metacopy
import mediatools.utilities as util
from mediatools.pdf_split import find_ghostscript, GS_BINARIES, PPP_PRESETS, DEFAULT_PPP, PDF_EXTENSIONS


def original_file(pdf_file):
    """Returns the name under which the original file is kept: foo.pdf -> foo_original.pdf"""
    root, ext = os.path.splitext(pdf_file)
    return f"{root}_original{ext}"


def _run_gs(pdf_file, out_file, ppp):
    gs = find_ghostscript()
    if gs is None:
        raise RuntimeError("Ghostscript not found on PATH (looked for " + ", ".join(GS_BINARIES) + ")")
    cmd = [
        gs,
        "-sDEVICE=pdfwrite",
        f"-dPDFSETTINGS=/{PPP_PRESETS[ppp]}",
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",
        f"-sOutputFile={out_file}",
        pdf_file,
    ]
    subprocess.run(cmd, check=True)


def compress(pdf_file, out_file=None, ppp=DEFAULT_PPP):
    """Compresses a PDF file. Returns the output file name
    Without out_file, the compressed file takes the name of the original, which is renamed with an _original postfix"""
    if out_file:
        _run_gs(pdf_file, out_file, ppp)
        metacopy.copy_date_and_geotag(pdf_file, out_file)
        return out_file
    backup = original_file(pdf_file)
    if os.path.exists(backup):
        raise RuntimeError(f"{backup} already exists, not overwriting it")
    # Compress to a temporary file first so that the original is untouched if compression fails
    tmp_file = f"{os.path.splitext(pdf_file)[0]}.compressing.pdf"
    try:
        _run_gs(pdf_file, tmp_file, ppp)
        metacopy.copy_date_and_geotag(pdf_file, tmp_file)
        Path(pdf_file).replace(backup)
        Path(tmp_file).replace(pdf_file)
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
    return pdf_file


def main():
    parser = argparse.ArgumentParser(description="Compresses PDF files (requires Ghostscript)")
    util.add_input_args(parser, "Input PDF files and/or directories (all the PDF files they contain are processed)")
    util.add_output_args(parser, "Output PDF file (default: replaces the input file, which is renamed with an _original postfix)")
    parser.add_argument(
        "--ppp",
        required=False,
        type=int,
        default=DEFAULT_PPP,
        choices=sorted(PPP_PRESETS),
        help="Compression level in pixels per inch: 150 (/ebook, default), 300 (/printer) or 600 (/prepress)",
    )
    args = parser.parse_args()
    input_files = util.expand_input_files(vars(args)[util.INPUT_FILES], extensions=PDF_EXTENSIONS)
    if len(input_files) > 1 and vars(args)[util.OUTPUT_FILE]:
        print("ERROR: -o can't be used with several input files")
        sys.exit(2)
    failed = 0
    progress = util.GlobalProgress(len(input_files))
    for input_file in input_files:
        try:
            if not os.path.isfile(input_file):
                print(f"File {input_file} not found")
                failed += 1
                continue
            try:
                out = compress(input_file, vars(args)[util.OUTPUT_FILE], args.ppp)
            except (RuntimeError, subprocess.CalledProcessError) as e:
                print(f"ERROR: {e}")
                failed += 1
                continue
            print(f"Compressed {input_file} into {out}")
        finally:
            progress.done()
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
