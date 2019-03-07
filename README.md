# BlackCAT
Computer-assisted translation tool made in Python &amp; Qt5.
## General information
Current version: 1.0 (beta)
Current supported files:
* .odt
* .txt
* .sgml
* .po

Import translation memory from:
* .tmx
* .po

## Dependencies
### Windows
Get Python 3 and install dependencies using pip:
````
pip install PyQt5 nltk polib pycountry bs4 fuzzywuzzy yandex.translate mstranslator chardet lxml pyenchant
````

You also need the punkt tokenizer for nltk:
````
python -m nltk.downloader punkt
````
##### Recommended
Install the Levenshtein library for more accurate translation memory coincidence handling:
````
pip install python-Levenshtein
````
For this you will most probably need to install the Visual C++ Build Tools, you can get them from https://go.microsoft.com/fwlink/?LinkId=691126

You can download dictionaries for spell checking from:
https://cgit.freedesktop.org/libreoffice/dictionaries/tree/ and put them in the Python installation directory under "Lib\site-packages\enchant\share\enchant\myspell".

### Linux
Get Python 3, pip (python3-pip or equivalent) and Qt5 (python3-qt5 or equivalent). Easiest way to do this is using your distro package manager. Then install the rest of the dependencies using pip:
````
pip3 install nltk polib pycountry bs4 fuzzywuzzy yandex.translate mstranslator chardet lxml python-Levenshtein pyenchant
````
And the punkt tokenizer:
````
python3 -m nltk.downloader punkt
````
You can install aditional dictionaries for spell checking from your package manager.

## Instalation
You don't need to install BlackCAT if you have all the dependencies. Just run:
````
python3 BlackCAT.py
````
or
````
python BlackCAT.py
````
We may work on an installer in the future.
## Contact
Carlos Chapi
carloswaldo@babelruins.org
