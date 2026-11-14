# LeakLens paper, IEEE conference format

Generated from `paper/leaklens_paper.tex` (the single source of the text); edit that file, then rebuild.

| File | What it is |
|---|---|
| `leaklens_ieee.tex`, `references.bib`, `IEEEtran.bst`, `*_table.tex` | IEEEtran conference version (US letter, two columns), BibTeX with IEEE's `IEEEtran.bst` |
| `leaklens_ieee.pdf` | compiled LaTeX version (6 pages) |
| `leaklens_ieee.docx` | the same paper on IEEE's Word conference template (`conference-template-letter.docx`), using the template's own styles |

Build (needs [tectonic](https://tectonic-typesetting.github.io)):

    TECTONIC=/path/to/tectonic paper_ieee/build.sh
    TECTONIC=/path/to/tectonic uv run --with lxml --with pypdfium2 --with pillow \
        python paper_ieee/make_docx.py /path/to/conference-template-letter.docx

`make_ieee.py` copies the abstract, keywords and body verbatim from the article version; only the class, title
block and bibliography mechanism change. `make_docx.py` converts the same source into the Word template (Strict
OOXML) and renders Fig. 1 from the LaTeX figure. The Word template's first-page footer keeps IEEE's copyright
placeholder (`XXX-X-XXXX-XXXX-X/XX/$XX.00 ©20XX IEEE`), to be replaced by the code the conference supplies.
