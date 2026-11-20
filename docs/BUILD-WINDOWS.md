# Budowanie wersji Windows

Cel: samodzielny, przenośny `STC-Programmer.exe` (Windows 10/11 x64, PyInstaller **onefile**, bez konsoli),
który zawiera GUI, Qt, Pythona i backend stcgal 1.10. Użytkownik nie instaluje Pythona, pip, PySide6 ani stcgal.

Są **dwie równoważne metody** budowania, oparte na **jednej wspólnej konfiguracji**:

| | Skrypt | Gdzie | Interpreter |
|---|---|---|---|
| A | `scripts/build-windows.sh` | Fedora (przez Wine) | Windows Python 3.13 w izolowanym prefiksie Wine |
| B | `scripts/build-windows.ps1` | natywny Windows 10/11 x64 | izolowany Python 3.13 (NuGet) albo wskazany `-PythonExe` |
| CI | `.github/workflows/build-windows.yml` | GitHub Actions `windows-latest` | wywołuje **ten sam** `build-windows.ps1` |

Wspólne dla A, B i CI: `packaging/requirements-build.txt` (wersje zależności),
`packaging/pyinstaller/{backend.spec,gui.spec,common.py}` oraz `scripts/pyi_build.py` (orkiestracja, weryfikacja,
raport). Skrypty `.sh`/`.ps1` zajmują się tylko przygotowaniem środowiska i raportem.

## Architektura pakietu

```
STC-Programmer.exe              (onefile: GUI, bez konsoli)
  └─ rozpakowanie do %TEMP%\_MEIxxxx\
       stcgal_gui/resources/    ikona, tłumaczenia
       backend/stcgal-backend.exe + _internal/   (stcgal 1.10, program konsolowy, onedir)
```

* Backend jest **osobnym procesem** (jak na Linuksie): GUI uruchamia `stcgal-backend.exe` z `_MEIPASS\backend\`
  bez okna konsoli (`CREATE_NO_WINDOW`), przechwytuje stdout/stderr, stosuje timeout i anulowanie.
* Backend jest zagnieżdżony jako dane w onefile (dwa kroki: `backend.spec` → `gui.spec`), a nie jako drugi onefile -
  unika podwójnego rozpakowania i zachowuje poprawne uchwyty konsoli backendu.
* **Anulowanie:** GUI nie ma konsoli, więc `CTRL_BREAK` nie działa. Backend czyta stdin: polecenie `cancel` (lub EOF
  po zniknięciu GUI) → `KeyboardInterrupt` → stcgal rozłącza się z MCU jak po Ctrl+C. Po 20 s bez zakończenia
  `TerminateProcess` (długi limit, bo odczyt pyserial bywa blokujący, a zabicie w trakcie zapisu jest gorsze).
* Dla procesu-dziecka będącego INNĄ aplikacją PyInstaller ustawiane jest `PYINSTALLER_RESET_ENVIRONMENT=1`.
* Okienkowy exe nie ma `sys.stdout`: `--selftest --report PLIK` i `--smoke-gui KATALOG` zapisują wyniki do plików.
* Wersja backendu: `stcgal-backend -V` (= `stcgal 1.10`), `--backend-info`; GUI: `STC-Programmer.exe --selftest`.

## Metoda A: Fedora + Wine (`scripts/build-windows.sh`)

Wymagania (jednorazowo): `sudo dnf install wine curl unzip python3` (sudo tylko do doinstalowania pakietów; sam build
nie wymaga uprawnień). ~3 GB miejsca w cache.

```bash
./scripts/build-windows.sh              # onefile → dist/windows/STC-Programmer.exe
./scripts/build-windows.sh --clean      # czysty build (cache Pythona/pip zostaje)
./scripts/build-windows.sh --verbose    # pełne wyjście Wine/pip/PyInstaller
./scripts/build-windows.sh --skip-tests # bez testów uruchomieniowych pod Wine
./scripts/build-windows.sh --onedir     # wariant diagnostyczny → dist/windows-onedir/STC-Programmer/
./scripts/build-windows.sh --reset-prefix  # nowy izolowany prefiks Wine
```

Co robi: sprawdza zależności → tworzy **osobny** prefiks (`~/.cache/stcgal-gui-winbuild/prefix`, nie rusza `~/.wine`)
→ pobiera Windows Python 3.13.12 z NuGet (zwykły ZIP, bez instalatora) → `pip install -r requirements.txt` (PySide6,
pyserial, PyInstaller, stcgal==1.10; cache wg skrótu pliku) → buduje backend i GUI → uruchamia wynik pod Wine
(`--selftest`, `--smoke-gui`, w onedir także backend bezpośrednio) → raport (`BUILD-REPORT.txt`: status, rozmiar,
SHA-256, wersje Python/PyInstaller/PySide6/stcgal/Wine). Log: `~/.cache/stcgal-gui-winbuild/logs/`.

Typowe problemy Wine: komunikaty `MESA-EGL`/`pci id` są nieszkodliwe (filtrowane); brak okien - testy używają platformy
`offscreen`; `wineboot` zawiesza się → `--reset-prefix`; `Python w Wine zgłasza…` → usuń `…/prefix/drive_c/py`; błąd
sieci przy pobieraniu → ponów (cache pobrań zachowuje ukończone pliki).
**Wynik pod Wine nie dowodzi działania na prawdziwym Windows.**

## Metoda B: natywny Windows (`scripts/build-windows.ps1`)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1            # onefile
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Clean -Verbose
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Onedir -SkipTests
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Installer  # + Inno Setup (wymaga ISCC.exe)
```

Bez administratora; izolowany Python w `%LOCALAPPDATA%\stcgal-gui-winbuild\py\3.13.12` (NuGet); `-PythonExe python`
używa istniejącego Pythona 3.12/3.13 x64 i instaluje zależności **do niego** (tak robi CI). Wynik:
`dist\windows\STC-Programmer.exe`, `STC-Programmer.sha256`, `BUILD-REPORT.txt`.
Pisany w składni zgodnej z Windows PowerShell 5.1 i PowerShell 7 (argumenty Pythona przekazywane przez pliki pomocnicze `scripts/pyinfo.py`, `scripts/appversion.py`, bez cytowania `-c`). **Nie był uruchomiony na Windows** (tylko przegląd kodu i test na zbudowanych artefaktach) - pierwsze uruchomienie wykona CI.

## Łańcuch dostaw i decyzje bezpieczeństwa

* Pakiet Pythona (NuGet) ma **przypiętą sumę SHA-256** w obu skryptach (weryfikacja po pobraniu; inna wersja wymaga
  `-PythonSha256` / `STC_WIN_PYTHON_SHA256`). Zależności pip: wersje przypięte w `requirements.txt` (bez `--require-hashes`).
* Wersja aplikacji musi być numeryczna `a.b.c` (zasób wersji exe i `VersionInfoVersion` Inno Setup).
* **Anulowanie zapisu na Windows:** `interrupt_main` nie przerywa blokującego odczytu pyserial, więc po poleceniu `cancel`
  GUI czeka do 20 s; potem `TerminateProcess`. Zabicie w trakcie zapisu może zostawić niekompletny firmware (bootloader ISP
  pozostaje dostępny) - komunikat o tym wyświetla się po anulowaniu. Przy awarii/zabiciu GUI backend jest kończony przez
  Job Object (`KILL_ON_JOB_CLOSE`) i EOF na stdin.

## Uruchamianie EXE na Windows

Skopiuj `STC-Programmer.exe` w dowolne miejsce i uruchom (pierwszy start rozpakowuje się kilka sekund do `%TEMP%`;
SmartScreen/antywirus mogą ostrzec przed niepodpisanym plikiem). Sterownik CH340 - standardowy Windows Update
(patrz `docs/WINDOWS.md`). Dziennik aplikacji: `%LOCALAPPDATA%\stcgal-gui\app.log`. Wariant `--onedir` ułatwia
diagnostykę brakujących bibliotek.

## Instalator (opcjonalny, Inno Setup)

`scripts\build-windows.ps1 -Installer` buduje wariant onedir i wywołuje `packaging/windows/installer.iss` →
`dist\STC-Programmer-Setup-x64.exe`: per-user bez administratora, wybór katalogu, skrót w menu Start, opcjonalny skrót na
pulpicie, metadane i wersja, aktualizacja „nad” poprzednią wersją (stały `AppId`). Odinstalowanie pyta o usunięcie
ustawień (rejestr `HKCU\Software\stcgal-gui`), tryb cichy je zachowuje.

## GitHub Actions i pobieranie artefaktów

Workflow `build-windows.yml` (ręcznie: *Actions → build-windows → Run workflow*; automatycznie dla PR zmieniających
kod/budowanie): testy (Windows + Linux), ruff, mypy, a następnie `scripts/build-windows.ps1 -Installer`, smoke testy
EXE i instalatora (instalacja cicha, uruchomienie, odinstalowanie) i artefakt **STC-Programmer-windows-x64**
(*Actions → przebieg → Artifacts*). Nie tworzy wydań.

## Bezpieczeństwo sprzętowe w buildzie

Skrypty i CI **nigdy** nie otwierają portów szeregowych ani nie wołają stcgal z portem; testy dymne używają backendu
symulowanego (`MockBackend`), a weryfikacja backendu to `-V`, `-h` i błędny protokół. Test regresyjny
(`tests/test_safety_eeprom.py`) skanuje skrypty. Szczegóły ochrony EEPROM/opcji: `docs/SAFETY.md`.

## Co zweryfikowano, a co nie

Patrz sekcja „Status” w README (aktualizowana po każdym buildzie).
