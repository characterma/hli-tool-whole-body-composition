Sphinx Documentation
====================

This file describes the process of how to generate the documentation:

1.  Add docstrings on your source code under the src/ folder

2.  Go into the docs/ folder and run the following commands:

-   \$ cd docs/

    \$ make clean

    \$ sphinx-apidoc -o source ../src --maxdepth=2

    \$ make html

    \$ make latexpdf

1.  The documentation will be generated under:

-   \$ \_build/html/index.html

    \$ \_build/latex/bix-tool-hli-tool-whole-body-composition.pdf
