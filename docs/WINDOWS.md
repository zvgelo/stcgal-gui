# STC Programmer GUI na Windows 10/11 (x64)

> **Status weryfikacji:** kod platformowy i logika COM są testowane automatycznie (gałęzie Windows
> symulowane na Linuksie), a pakiet `onedir` został zbudowany i sprawdzony **na Linuksie**.
> **Build, instalator i działanie na prawdziwym Windows nie zostały jeszcze uruchomione** - pierwszą
> weryfikację wykona workflow `.github/workflows/build-windows.yml` (patrz `docs/BUILD-WINDOWS.md`).

## Instalacja

0. Najprościej: skopiuj przenośny `STC-Programmer.exe` (onefile) i uruchom - instalacja niepotrzebna.
1. Albo pobierz `STC-Programmer-Setup-x64.exe` (artefakt workflow lub od autora) i uruchom.
2. Domyślnie instalacja jest **per-user** (bez administratora) w `%LOCALAPPDATA%\Programs\STC Programmer`;
   w kreatorze możesz zmienić katalog, a okno uprawnień pozwala wybrać instalację dla wszystkich.
3. Skrót w menu Start; skrót na pulpicie jest opcjonalny (zadanie w kreatorze).
4. Nie jest potrzebny Python ani `stcgal` - backend (`stcgal-backend.exe`, stcgal 1.10) jest w pakiecie (w onefile zagnieżdżony).


## Aktualizacja

Uruchom nowszy instalator - ma ten sam identyfikator aplikacji, więc podmieni pliki w miejscu
(zamknie działającą aplikację). Ustawienia zostają. ZIP: rozpakuj nową wersję do nowego katalogu.

## Odinstalowanie

*Ustawienia → Aplikacje* lub `unins000.exe`. Instalator **pyta**, czy usunąć ustawienia
(rejestr `HKCU\Software\stcgal-gui`); tryb cichy (`/VERYSILENT`) zawsze je zachowuje.

## Sterownik i porty COM

* Aplikacja **nie instaluje sterowników**. CH340/CH341 działa ze standardowym sterownikiem
  Windows Update (VID_1A86 & PID_7523, „USB-SERIAL CH340 (COMx)”); producent oferuje też
  CH341SER. CP210x i FT232 - sterowniki producentów/Windows Update.
* Lista portów pochodzi z `pyserial` (COM1…COMn, również > COM9): nazwa COM, opis urządzenia,
  VID:PID, numer seryjny (jeśli adapter go ma - wiele CH340 nie ma), lokalizacja USB.
* Porty bez adaptera USB (wbudowane COM, Bluetooth) są domyślnie ukryte
  (*Parametry zaawansowane → „Pokaż porty bez adaptera USB”*).
* Numer COM może się zmienić po podłączeniu do innego gniazda USB - odśwież listę (F5);
  aplikacja sama wykrywa podłączenie/odłączenie adaptera i czyści dane MCU po zniknięciu portu.
* `/dev/serial/by-id` nie istnieje w Windows i nie jest używane.

## Diagnostyka CH340 na Windows

1. **Menedżer urządzeń → Porty (COM i LPT):** powinien być „USB-SERIAL CH340 (COMx)”.
   Wpis z żółtym wykrzyknikiem lub w „Inne urządzenia” = brak sterownika (Windows Update / CH341SER).
2. Właściwości → Szczegóły → Identyfikatory sprzętu: `USB\VID_1A86&PID_7523`.
3. „Access is denied” przy wykrywaniu = port zajęty przez inny program (terminal szeregowy,
   inny programator, druga kopia aplikacji). Zamknij go.
4. „Cannot find the file specified” = numer COM zniknął/zmienił się; odśwież listę.
5. „A device attached to the system is not functioning” w trakcie operacji = utrata adaptera
   (kabel, hub, zasilanie). Podłącz ponownie, odśwież, powtórz operację.
6. Pozostałe kroki (zasilanie MCU, TX↔RX, GND, poziomy 3,3 V/5 V) - jak w `docs/CH340.md`.

Zakładka **Diagnostyka** → „Informacje o środowisku” zbiera wersję aplikacji, backendu i listę portów.

## Różnice Linux / Windows

| Obszar | Linux (Fedora) | Windows 10/11 |
|---|---|---|
| Backend | zewnętrzny `stcgal` (PATH/pipx) lub dołączony | **dołączony** `stcgal-backend.exe` (ten sam stcgal 1.10) |
| Nazwy portów | `/dev/ttyUSB0`, stabilne `/dev/serial/by-id/…` | `COM3`, `COM10`…; brak by-id |
| Uprawnienia | grupa `dialout` | brak grup; „Access is denied” = port zajęty |
| Port zajęty | `Device or resource busy` | `Access is denied` |
| Okno konsoli | n/d | brak (`CREATE_NO_WINDOW`) |
| Anulowanie | SIGINT → SIGTERM → SIGKILL | polecenie `cancel` na stdin → `TerminateProcess` |
| Ustawienia | `~/.config/stcgal-gui` | rejestr `HKCU\Software\stcgal-gui` |
| Instalacja | `scripts/install.sh` (venv) | instalator Inno Setup / ZIP |
| Wygląd | styl Breeze (RPM PySide6) lub Fusion | styl Windows 11/Fusion; motyw jasny/ciemny z palety aplikacji |
| USB-ISP (`usb15`) | bez gwarancji | **nieobsługiwany** w pakiecie (brak libusb) |

Semantyka operacji jest identyczna: wykrywanie nigdy nie dostaje pliku, `-e`, `-o`, `-t`; zapis
wymaga potwierdzenia; brak odczytu firmware i brak weryfikacji po zapisie.
