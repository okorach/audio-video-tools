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

"""Splits a PDF file into one PDF file per page, using Ghostscript.

foo.pdf is split into foo.page_1.pdf, foo.page_2.pdf, ...
Page numbers are zero padded to the number of digits of the page count (foo.page_01.pdf for 10 to 99 pages, etc...)
"""

import os
import re
import shutil
import subprocess
import sys
import argparse
import mediatools.utilities as util

GS_BINARIES = ("gswin64c", "gswin32c", "gs")

# Extensions of the PDF files found in the input directories
PDF_EXTENSIONS = ("pdf",)

# Resolution in pixels per inch -> Ghostscript PDFSETTINGS preset
PPP_PRESETS = {150: "ebook", 300: "printer", 600: "prepress"}
DEFAULT_PPP = 150


def find_ghostscript():
    """Returns the path of the Ghostscript executable, or None if not found"""
    for binary in GS_BINARIES:
        path = shutil.which(binary)
        if path:
            return path
    return None


def page_count(gs, pdf_file):
    """Returns the number of pages of a PDF file"""
    # PostScript string: backslashes and parentheses must be escaped
    ps_path = pdf_file.replace("\\", "/").replace("(", r"\(").replace(")", r"\)")
    ps_code = f"({ps_path}) (r) file runpdfbegin pdfpagecount = quit"
    cmd = [gs, "-q", "-dNODISPLAY", "-dNOSAFER", "-dBATCH", "-dNOPAUSE", "-c", ps_code]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    match = re.search(r"\d+", result.stdout)
    if result.returncode != 0 or not match:
        raise RuntimeError(f"Could not get page count of {pdf_file}: {result.stderr.strip() or result.stdout.strip()}")
    return int(match.group())


def output_pattern(pdf_file, nb_pages):
    """Returns the Ghostscript output file pattern, with page number zero padded to the width of nb_pages"""
    width = len(str(nb_pages))
    base = os.path.splitext(pdf_file)[0]
    return f"{base}.page_%0{width}d.pdf"


def split(pdf_file, ppp=DEFAULT_PPP):
    """Splits a PDF in 1 PDF per page. Returns the number of pages"""
    gs = find_ghostscript()
    if gs is None:
        raise RuntimeError("Ghostscript not found on PATH (looked for " + ", ".join(GS_BINARIES) + ")")
    nb_pages = page_count(gs, pdf_file)
    cmd = [
        gs,
        "-sDEVICE=pdfwrite",
        f"-dPDFSETTINGS=/{PPP_PRESETS[ppp]}",
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",
        f"-sOutputFile={output_pattern(pdf_file, nb_pages)}",
        pdf_file,
    ]
    subprocess.run(cmd, check=True)
    return nb_pages


def main():
    parser = argparse.ArgumentParser(description="Splits PDF files into 1 PDF file per page (requires Ghostscript)")
    parser.add_argument(
        "-i", "--inputfiles", required=True, nargs="+", help="Input PDF files and/or directories (all the PDF files they contain are processed)"
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
    failed = 0
    input_files = util.expand_input_files(args.inputfiles, extensions=PDF_EXTENSIONS)
    progress = util.GlobalProgress(len(input_files))
    for input_file in input_files:
        try:
            if not os.path.isfile(input_file):
                print(f"File {input_file} not found")
                failed += 1
                continue
            try:
                nb_pages = split(input_file, args.ppp)
            except (RuntimeError, subprocess.CalledProcessError) as e:
                print(f"ERROR: {e}")
                failed += 1
                continue
            print(f"Split {input_file} into {nb_pages} files")
        finally:
            progress.done()
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
