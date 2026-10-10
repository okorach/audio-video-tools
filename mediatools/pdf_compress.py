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

"""Compresses a PDF file using Ghostscript.

By default the compressed file replaces the original, which is kept with an "_original" postfix:
foo.pdf is compressed into foo.pdf and the original file is renamed foo_original.pdf
If an output file is specified, the original file is left untouched.
"""

import os
import subprocess
import sys
import argparse

from mediatools.pdf_split import find_ghostscript, GS_BINARIES, PPP_PRESETS, DEFAULT_PPP


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
        return out_file
    backup = original_file(pdf_file)
    if os.path.exists(backup):
        raise RuntimeError(f"{backup} already exists, not overwriting it")
    # Compress to a temporary file first so that the original is untouched if compression fails
    tmp_file = f"{os.path.splitext(pdf_file)[0]}.compressing.pdf"
    try:
        _run_gs(pdf_file, tmp_file, ppp)
        os.replace(pdf_file, backup)
        os.replace(tmp_file, pdf_file)
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
    return pdf_file


def main():
    parser = argparse.ArgumentParser(description="Compresses a PDF file (requires Ghostscript)")
    parser.add_argument("-i", "--inputfile", required=True, help="Input PDF file")
    parser.add_argument(
        "-o",
        "--outputfile",
        required=False,
        default=None,
        help="Output PDF file (default: replaces the input file, which is renamed with an _original postfix)",
    )
    parser.add_argument(
        "--ppp",
        required=False,
        type=int,
        default=DEFAULT_PPP,
        choices=sorted(PPP_PRESETS),
        help="Compression level in pixels per inch: 150 (/ebook, default), 300 (/printer) or 600 (/prepress)",
    )
    args = parser.parse_args()
    if not os.path.isfile(args.inputfile):
        print(f"File {args.inputfile} not found")
        sys.exit(1)
    try:
        out = compress(args.inputfile, args.outputfile, args.ppp)
    except (RuntimeError, subprocess.CalledProcessError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    print(f"Compressed {args.inputfile} into {out}")


if __name__ == "__main__":
    main()
