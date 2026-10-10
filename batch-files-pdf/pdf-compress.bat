:: Compress PDF to 150ppp /ebook
:: Compress PDF to 150ppp /printer

setlocal enabledelayedexpansion
for %%F in (%*) do (
    gswin64c -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -dNOPAUSE -dBATCH -sOutputFile="%%~F_compressed.pdf" "%%~F"
)
