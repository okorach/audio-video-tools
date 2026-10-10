:: Merge all the PDF files passed as argument into a single merged.pdf (in the folder of the first file)
:: Pages are in the lexicographic order of the file names

pdf-merge -i %*
pause
