# Architektura i analiza techniczna

## 1. Analiza stcgal 1.10 (źródła zainstalowane przez pipx)

| Zagadnienie | Ustalenie |
|---|---|
| Interfejs | Brak stabilnego API bibliotecznego; stabilny jest CLI (`stcgal -p -P -b -l -o -t -D -a -A -e`). GUI wywołuje CLI jako podproces. |
| Handshake | `StcBaseProtocol.connect()` otwiera port (handshake 2400 baud), w pętli wysyła bajt `0x7F` co 30 ms i czeka na pakiet statusu. Bootloader STC odpowiada tylko krótko po starcie, więc **zasilanie MCU trzeba wyłączyć i włączyć** (lub użyć `-a` z DTR/RTS sterującym zasilaniem). Bez tego stcgal czeka bez końca - GUI narzuca własny timeout. |
| Identyfikacja | Z pakietu statusu: `magic` (2 B) → wpis w `models.py` (nazwa, flash, EEPROM, IAP). Wypisuje: model, magic, flash, EEPROM, częstotliwość, wersję BSL, zegar wybudzania, Vref, datę produkcji, bieżące bajty opcji. |
| Tryby pracy | `frontend.run()`: **bez pliku i bez `-e`** → tylko `connect` + `initialize` + `disconnect` (nic nie kasuje ani nie programuje, `handshake()`/kalibracja nie są wywoływane). Z plikiem → `handshake`, `erase_flash`, `program_flash`, `program_options`. Z `-e` → kasowanie. Opcje `-o` są przetwarzane **tylko** podczas zapisu. |
| Zapis | Kasowanie obejmuje cały obraz, zapis blokami z paskiem `tqdm` (stderr, „Writing flash: NN%\|…\| x/y”) - to jedyny rzeczywisty postęp. `program_options` zawsze zapisuje bajty opcji (bieżące z układu + zmiany `-o`). |
| Weryfikacja | **Brak** weryfikacji zawartości po zapisie w protokołach STC8 (tylko sumy w wybranych protokołach STC89/12). GUI nigdy nie pokazuje „weryfikacja poprawna”. |
| Odczyt firmware | **Brak.** Protokół ISP nie ma komendy odczytu flash; stcgal nie ma opcji dump. |
| Wybór HEX/BIN | Wyłącznie po rozszerzeniu (`.hex/.ihx/.ihex` → Intel HEX, wszystko inne → surowy BIN). Plik HEX o złym rozszerzeniu zostałby zapisany jako tekst - GUI to blokuje. |
| Błędy | Na stderr: `Protocol error:`, `Serial port error:` (pyserial: Errno 13 uprawnienia, 16 port zajęty, 2 brak portu), `Option error:`, `Unexpected error:`; kod wyjścia 1, `interrupted` → 2. |
| Enumeracja portów | stcgal nie enumeruje portów (`-p`, domyślnie `/dev/ttyUSB0`). GUI robi to przez `serial.tools.list_ports` + `/dev/serial/by-id`. |

## 2. STC8H8K64U

* `models.py`: `STC8H8K64U`, magic `0xF784`, flash 65536 B łącznie, **kod 65024 B**, **EEPROM 512 B**, IAP = tak, kalibracja = tak.
* Autodetekcja (`StcAutoProtocol`) mapuje `STC8H…` na **`stc8d`** (jedynie `STC8H1Kxx` i `STC8G*` → `stc8g`). Różnica ma znaczenie: `Stc8gProtocol` inaczej liczy cel kalibracji (`baud_handshake` zamiast `baud_handshake/2`).
* **Wniosek:** wybór `stc8g` dla STC8H8K64U nie jest zalecany; zalecane `auto` (rozstrzyga `stc8d`) lub jawnie `stc8d`. GUI ostrzega o niezgodności protokołu po wykryciu modelu.
* Wsparcie w stcgal wynika ze źródeł (wpis w bazie + protokół stc8d). **Testy na fizycznym układzie nie zostały wykonane** (patrz README, „Status”).
* Podział flash/EEPROM: opcja `program_eeprom_split` (bajty). Przy domyślnym 0 i IAP=tak stcgal przyjmuje kod = 65024 B.
* STC8H8K64U ma też natywny USB-ISP (`usb15`) - to inny tryb (USB, nie UART); GUI jest nastawione na UART/CH340.

## 3. Warstwy

```
stcgal_gui/
  models/    dataclasses (PortInfo, McuInfo, ConnectionParams, ProgramParams, OperationResult…) - bez Qt
  devices/   ports.py (enumeracja, CH340, by-id), mcu_db.py (oczekiwany protokół wg stcgal)
  backends/  base.py (Backend ABC, Capabilities, WriteConfirmation), process.py (Popen+timeout+cancel),
             stcgal.py (budowa komend, parser wyjścia, klasyfikacja błędów), mock.py
  core/      controller.py (QThread, jedna operacja naraz), firmware.py (walidacja), redact.py,
             settings.py (QSettings), i18n.py
  gui/       main_window.py, context.py, tabs/{connection,mcu,program,backup,diagnostics,settings}.py
```

* GUI zna tylko `Backend` (ABC) i `OperationController`. Nowy backend (np. `stc-isp`, `stm32flash`) = nowa klasa implementująca `Backend`; zmiana jednej linii w `__main__.py`.
* `Capabilities` deklaruje prawdziwy zakres (`verify=False`, `read_firmware=False` dla stcgal); zakładka „Odczyt i kopia” renderuje się z tych danych.
* Operacje sprzętowe działają w `QThread`; zdarzenia (log/stan/postęp/wynik) wracają sygnałami Qt.

## 4. Gwarancje bezpieczeństwa (egzekwowane w kodzie i testach)

1. `build_identify_command` nie przyjmuje pliku, `-e`, `-o`, `-t` (assert + testy argv).
2. `Backend.program()` rzuca `SafetyError` bez `WriteConfirmation` pasującego do portu i pliku; GUI tworzy je dopiero po kliknięciu „Kasuj i programuj” w oknie dialogowym (domyślny przycisk: Anuluj).
3. Brak funkcji samodzielnego `--erase` w GUI. Opcje `-o` walidowane regexem `klucz=wartość`; ścieżki plików bezwzględne; `shell=False`.
4. Jedna operacja naraz (kontroler + blokada w backendzie) → brak równoległych operacji na porcie.
5. Timeout: faza oczekiwania na MCU (domyślnie 60 s) i limit ciszy 90 s po połączeniu. Anulowanie: SIGINT (stcgal sam się rozłącza) → SIGTERM → SIGKILL. Anulowanie w trakcie zapisu ostrzega o możliwym niekompletnym firmware.
6. `OperationResult.verified` jest `False`, o ile backend nie zweryfikował; UI pisze „NIE wykonano”.
7. Aplikacja nie przełącza napięcia, nie modyfikuje reguł udev.

## 5. Warstwa platformowa (Linux / Windows)

* `platform_support.py` - jedyne miejsce z logiką zależną od systemu: nazwy portów
  (`normalize_port`), porty wbudowane, by-id, dostęp do portu, lokalizacja zasobów i dołączonego
  backendu, `init_process` (AppUserModelID). Funkcje przyjmują `windows=`, więc gałęzie Windows
  testuje się na Linuksie.
* `backends/procctl.py` - tworzenie podprocesu i anulowanie (Linux: SIGINT→SIGTERM→SIGKILL;
  Windows: `CREATE_NO_WINDOW`, polecenie `cancel` na stdin → `TerminateProcess`).
* `core/diagnosis.py` - komunikaty/wskazówki błędów zależne od systemu.
* `backend_entry.py` - `stcgal-backend` (stcgal 1.10 bez zmian semantyki).
* GUI nie sprawdza `sys.platform`; pyta moduły powyżej.
