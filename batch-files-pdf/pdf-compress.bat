:: Compress each PDF file passed as argument (foo.pdf is compressed in place, the original is kept as foo_original.pdf)
:: Asks for the quality in ppp: 150 (/ebook, default), 300 (/printer) or 600 (/prepress)

setlocal enabledelayedexpansion
set ppp=150
set /p ppp=Quality in ppp [150, 300, 600] (default 150) ?
for %%F in (%*) do (
    pdf-compress -i "%%~F" --ppp !ppp!
)
