:: Split each PDF file passed as argument into 1 PDF per page (foo.pdf -> foo.page_1.pdf, foo.page_2.pdf, ...)
:: Asks for the quality in ppp: 150 (/ebook, default), 300 (/printer) or 600 (/prepress)

setlocal enabledelayedexpansion
set ppp=150
set /p ppp=Quality in ppp [150, 300, 600] (default 150) ?
for %%F in (%*) do (
    pdf-split -i "%%~F" --ppp !ppp!
)
pause
