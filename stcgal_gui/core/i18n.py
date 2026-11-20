"""Internacjonalizacja: teksty źródłowe są po polsku, angielski ładowany z pliku .qm.

Język jest wybierany przy starcie (ustawienie „system / pl / en”); zmiana w Ustawieniach
działa po ponownym uruchomieniu aplikacji.
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

from stcgal_gui import platform_support as ps

TRANSLATIONS_DIR = ps.resource_dir() / "translations"
LANGUAGES = ("system", "pl", "en")
SOURCE_LANGUAGE = "pl"

_installed: list[QTranslator] = []


def tr(context: str, text: str, disambiguation: str | None = None, n: int = -1) -> str:
    """Tłumaczy tekst spoza klas Qt (moduły core/backends); ``context`` jak w pliku .ts."""
    return QCoreApplication.translate(context, text, disambiguation, n)


def tx(context: str, text: object) -> str:
    """Tłumaczy tekst oznaczony ``QT_TRANSLATE_NOOP`` (wartość znana dopiero w czasie działania)."""
    return QCoreApplication.translate(context, str(text))


def fmt(text: str, *args: object) -> str:
    """Podstawia %1, %2, ... (kolejność może się różnić w tłumaczeniu)."""
    for i in range(len(args), 0, -1):
        text = text.replace(f"%{i}", str(args[i - 1]))
    return text


def effective_language(setting: str = "system", locale: QLocale | None = None) -> str:
    """Zwraca ``pl`` albo ``en``: wprost z ustawienia, a dla „system” z języka systemu."""
    if setting in ("pl", "en"):
        return setting
    loc = locale or QLocale.system()
    return "pl" if loc.language() == QLocale.Language.Polish else "en"


def remove_translators(app: QCoreApplication) -> None:
    """Usuwa zainstalowane tłumaczenia (wraca tekst źródłowy, czyli polski)."""
    for old in _installed:
        app.removeTranslator(old)
    _installed.clear()


def install_translators(
    app: QCoreApplication, language: str = "system", locale: QLocale | None = None
) -> str:
    """Instaluje tłumaczenia dla wybranego języka i zwraca faktycznie użyty (``pl``/``en``).

    Poprzednio zainstalowane tłumaczenia są usuwane, więc można wołać wielokrotnie (testy).
    """
    remove_translators(app)
    lang = effective_language(language, locale)
    loc = QLocale(lang)
    QLocale.setDefault(loc)
    qt_tr = QTranslator(app)
    if qt_tr.load(loc, "qtbase", "_", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(qt_tr)
        _installed.append(qt_tr)
    if lang != SOURCE_LANGUAGE:
        app_tr = QTranslator(app)
        if app_tr.load(f"stcgal_gui_{lang}", str(TRANSLATIONS_DIR)):
            app.installTranslator(app_tr)
            _installed.append(app_tr)
    return lang
