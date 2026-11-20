# Komponenty zewnętrzne

Aplikacja (kod w tym repozytorium) jest na licencji MIT (`LICENSE`). Pakiet Windows (`STC-Programmer.exe`)
oraz buildy zawierają dodatkowo:

| Komponent | Licencja | Uwagi |
|---|---|---|
| [stcgal](https://github.com/grigorig/stcgal) 1.10 | MIT | backend ISP, uruchamiany jako osobny proces |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) (Qt 6) | LGPL-3.0 | łączone dynamicznie; biblioteki Qt można podmienić (onedir: katalog `_internal`) |
| [pyserial](https://github.com/pyserial/pyserial) | BSD-3-Clause | obsługa portów szeregowych/COM |
| [PyInstaller](https://pyinstaller.org) (bootloader) | GPL-2.0 z wyjątkiem dla programów pakowanych | tylko narzędzie budowania |
| [tqdm](https://github.com/tqdm/tqdm), pyusb | MPL-2.0/MIT, Apache-2.0 | zależności stcgal |
| Python | PSF License | interpreter w pakiecie |

Przed dystrybucją binarną sprawdź pełne teksty licencji dołączonych pakietów (LGPL wymaga
udostępnienia treści licencji i możliwości podmiany bibliotek Qt).
