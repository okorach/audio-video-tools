:: Merge all the PDF files passed as argument into a single PDF named after the first file (foo1.pdf foo2.pdf -> foo1_merged.pdf)
:: Pages are in the lexicographic order of the file names

pdftool merge -i %*
