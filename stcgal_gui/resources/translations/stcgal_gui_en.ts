<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="en_US" sourcelanguage="pl">
    <context>
        <name>AppContext</name>
        <message>
            <source>Oczekiwanie na zasilenie MCU</source>
            <translation>Waiting for MCU power</translation>
        </message>
        <message>
            <source>po operacji zapisu - wykryj mikrokontroler ponownie</source>
            <translation>after a write, detect the microcontroller again</translation>
        </message>
        <message>
            <source>Dane MCU wyczyszczone: %1</source>
            <translation>MCU data cleared: %1</translation>
        </message>
        <message>
            <source>zmieniono port</source>
            <translation>port changed</translation>
        </message>
        <message>
            <source>port zniknął (odłączono adapter?)</source>
            <translation>port disappeared (adapter unplugged?)</translation>
        </message>
    </context>
    <context>
        <name>Backend</name>
        <message>
            <source>Backend nie obsługuje samego kasowania</source>
            <translation>The backend does not support erase only</translation>
        </message>
    </context>
    <context>
        <name>BackupTab</name>
        <message>
            <source>Odczyt firmware nie jest obsługiwany przez wybrany backend i protokół ISP</source>
            <translation>Reading firmware is not supported by the selected backend and ISP protocol</translation>
        </message>
        <message>
            <source>Obsługiwane</source>
            <translation>Supported</translation>
        </message>
        <message>
            <source>Nieobsługiwane</source>
            <translation>Not supported</translation>
        </message>
        <message>
            <source>Identyfikator MCU</source>
            <translation>MCU identifier</translation>
        </message>
        <message>
            <source>Widok Połączenie → „Wykryj mikrokontroler”</source>
            <translation>Connection view → “Detect microcontroller”</translation>
        </message>
        <message>
            <source>Opcje konfiguracyjne</source>
            <translation>Configuration options</translation>
        </message>
        <message>
            <source>Odczyt bajtów opcji z bootloadera - tylko podgląd</source>
            <translation>Option bytes read from the bootloader, view only</translation>
        </message>
        <message>
            <source>Dane pamięci (Flash/EEPROM)</source>
            <translation>Memory contents (Flash/EEPROM)</translation>
        </message>
        <message>
            <source>Protokół ISP STC nie udostępnia odczytu zawartości pamięci</source>
            <translation>The STC ISP protocol cannot read memory contents</translation>
        </message>
        <message>
            <source>Firmware aplikacji</source>
            <translation>Application firmware</translation>
        </message>
        <message>
            <source>Bootloader STC nie umożliwia odczytu kodu użytkownika</source>
            <translation>The STC bootloader cannot read user code</translation>
        </message>
        <message>
            <source>Zakres możliwości odczytu</source>
            <translation>What can be read</translation>
        </message>
        <message>
            <source>Zapisz informacje o MCU (JSON)…</source>
            <translation>Save MCU info (JSON)…</translation>
        </message>
        <message>
            <source>Kopia informacji o układzie</source>
            <translation>Chip information export</translation>
        </message>
        <message>
            <source>Plik JSON zawiera wyłącznie dane faktycznie zwrócone przez stcgal (identyfikator, parametry, opcje). To NIE jest kopia firmware.</source>
            <translation>The JSON file contains only data actually returned by stcgal (identifier, parameters, options). It is NOT a firmware backup.</translation>
        </message>
        <message>
            <source>Zapisz informacje o MCU</source>
            <translation>Save MCU info</translation>
        </message>
        <message>
            <source>JSON (*.json)</source>
            <translation>JSON (*.json)</translation>
        </message>
        <message>
            <source>Zapisano informacje o MCU: %1</source>
            <translation>MCU info saved: %1</translation>
        </message>
    </context>
    <context>
        <name>ConnectionTab</name>
        <message>
            <source>Dodaj użytkownika do grupy dialout i zaloguj się ponownie (docs/CH340.md).</source>
            <translation>Add your user to the dialout group and log in again (docs/CH340.md).</translation>
        </message>
        <message>
            <source>Brak dostępu do portu COM - zamknij programy używające tego portu.</source>
            <translation>No access to the COM port. Close programs that use it.</translation>
        </message>
        <message>
            <source>Wyłącz i ponownie włącz zasilanie mikrokontrolera. Nie odłączaj adaptera CH340 od portu USB.</source>
            <translation>Turn the microcontroller power off and on again. Do not unplug the CH340 adapter from USB.</translation>
        </message>
        <message>
            <source>Port szeregowy programatora (F5 - odśwież listę)</source>
            <translation>Programmer serial port (F5 refreshes the list)</translation>
        </message>
        <message>
            <source>Odśwież</source>
            <translation>Refresh</translation>
        </message>
        <message>
            <source>Odśwież listę portów (F5)</source>
            <translation>Refresh the port list (F5)</translation>
        </message>
        <message>
            <source>„auto” - stcgal rozpoznaje rodzinę; dla STC8H8K64U wybiera stc8d.</source>
            <translation>“auto”: stcgal detects the family and picks stc8d for the STC8H8K64U.</translation>
        </message>
        <message>
            <source>Adapter i port</source>
            <translation>Adapter and port</translation>
        </message>
        <message>
            <source>Wykrycie adaptera (np. CH340) nie oznacza wykrycia mikrokontrolera. Sprawdź zgodność napięcia zasilania i poziomów logicznych (3,3 V / 5 V); aplikacja nie przełącza napięcia. Wykrywanie niczego nie kasuje ani nie programuje.</source>
            <translation>Finding an adapter (e.g. CH340) does not mean the microcontroller was found. Check that the supply voltage and logic levels match (3.3 V / 5 V); the app does not switch voltage. Detection never erases or programs anything.</translation>
        </message>
        <message>
            <source>Port:</source>
            <translation>Port:</translation>
        </message>
        <message>
            <source>Protokół:</source>
            <translation>Protocol:</translation>
        </message>
        <message>
            <source>Wykryj mikrokontroler</source>
            <translation>Detect microcontroller</translation>
        </message>
        <message>
            <source>Niedestrukcyjna identyfikacja (Ctrl+D). Nie kasuje i nie programuje pamięci.</source>
            <translation>Non-destructive identification (Ctrl+D). Does not erase or program memory.</translation>
        </message>
        <message>
            <source>Anuluj</source>
            <translation>Cancel</translation>
        </message>
        <message>
            <source>Przerwij bieżącą operację (Esc)</source>
            <translation>Stop the current operation (Esc)</translation>
        </message>
        <message>
            <source>Stan</source>
            <translation>Status</translation>
        </message>
        <message>
            <source> s</source>
            <translation> s</translation>
        </message>
        <message>
            <source>Reset sygnałem DTR</source>
            <translation>Reset via DTR</translation>
        </message>
        <message>
            <source>Wymaga układu, w którym DTR zasila/resetuje MCU. Zwykle zostaw wyłączone.</source>
            <translation>Needs a board where DTR powers or resets the MCU. Usually leave it off.</translation>
        </message>
        <message>
            <source>Pokaż porty bez adaptera USB</source>
            <translation>Show ports without a USB adapter</translation>
        </message>
        <message>
            <source>Wbudowane (ttyS*/COM płyty głównej) i Bluetooth - zwykle nieużywane</source>
            <translation>Built-in (motherboard ttyS*/COM) and Bluetooth ports, usually unused</translation>
        </message>
        <message>
            <source>Parametry zaawansowane</source>
            <translation>Advanced parameters</translation>
        </message>
        <message>
            <source>Transfer (baud):</source>
            <translation>Transfer (baud):</translation>
        </message>
        <message>
            <source>Handshake (baud):</source>
            <translation>Handshake (baud):</translation>
        </message>
        <message>
            <source>Limit czasu:</source>
            <translation>Timeout:</translation>
        </message>
        <message numerus="yes">
            <source>Wykryte porty: %n</source>
            <translation>
                <numerusform>Ports found: %n</numerusform>
                <numerusform>Ports found: %n</numerusform>
            </translation>
        </message>
        <message>
            <source>Nie wykryto adaptera USB-UART</source>
            <translation>No USB-UART adapter found</translation>
        </message>
        <message>
            <source>Podłącz programator USB i odśwież listę portów (F5).</source>
            <translation>Plug in the USB programmer and refresh the port list (F5).</translation>
        </message>
        <message>
            <source>Adapter: %1</source>
            <translation>Adapter: %1</translation>
        </message>
        <message>
            <source>Adapter %1 - brak uprawnień do portu</source>
            <translation>Adapter %1: no permission for the port</translation>
        </message>
        <message>
            <source>Stabilna ścieżka: %1</source>
            <translation>Stable path: %1</translation>
        </message>
        <message>
            <source>Lokalizacja USB: %1</source>
            <translation>USB location: %1</translation>
        </message>
        <message>
            <source>Numer seryjny: %1</source>
            <translation>Serial number: %1</translation>
        </message>
        <message>
            <source>ponowne wykrywanie</source>
            <translation>detecting again</translation>
        </message>
        <message>
            <source>Rozpoczęto wykrywanie (tryb niedestrukcyjny) na %1</source>
            <translation>Detection started (non-destructive) on %1</translation>
        </message>
        <message>
            <source>szczegóły w widoku „Mikrokontroler”</source>
            <translation>details in the “Microcontroller” view</translation>
        </message>
        <message>
            <source>Upłynęło %1 s · limit za %2 s</source>
            <translation>Elapsed %1 s · timeout in %2 s</translation>
        </message>
        <message>
            <source>Upłynęło %1 s</source>
            <translation>Elapsed %1 s</translation>
        </message>
    </context>
    <context>
        <name>Controller</name>
        <message>
            <source>Błąd wewnętrzny: %1</source>
            <translation>Internal error: %1</translation>
        </message>
        <message>
            <source>Nie można zmienić backendu w trakcie operacji</source>
            <translation>Cannot change the backend during an operation</translation>
        </message>
        <message>
            <source>Zapis wymaga potwierdzenia użytkownika</source>
            <translation>Writing requires user confirmation</translation>
        </message>
        <message>
            <source>Kasowanie wymaga potwierdzenia użytkownika</source>
            <translation>Erasing requires user confirmation</translation>
        </message>
    </context>
    <context>
        <name>Diagnosis</name>
        <message>
            <source>Brak uprawnień do portu. Dodaj użytkownika do grupy „dialout” (sudo usermod -aG dialout $USER) i zaloguj się ponownie.</source>
            <translation>No permission for the port. Add your user to the “dialout” group (sudo usermod -aG dialout $USER) and log in again.</translation>
        </message>
        <message>
            <source>Port jest zajęty przez inny proces (np. ModemManager, terminal szeregowy, druga instancja programu). Zamknij go i spróbuj ponownie.</source>
            <translation>The port is in use by another process (e.g. ModemManager, a serial terminal, a second instance of this app). Close it and try again.</translation>
        </message>
        <message>
            <source>Port nie istnieje. Sprawdź połączenie programatora USB i odśwież listę portów.</source>
            <translation>The port does not exist. Check the USB programmer connection and refresh the port list.</translation>
        </message>
        <message>
            <source>Brak dostępu do portu COM. Zamknij programy używające portu (terminal szeregowy, inne narzędzia ISP, druga instancja) lub sprawdź politykę dostępu do urządzeń.</source>
            <translation>No access to the COM port. Close programs that use it (serial terminal, other ISP tools, a second instance) or check the device access policy.</translation>
        </message>
        <message>
            <source>Port COM jest zajęty (Windows zgłasza „Access is denied”). Zamknij inny program używający tego portu i spróbuj ponownie.</source>
            <translation>The COM port is busy (Windows reports “Access is denied”). Close the other program using this port and try again.</translation>
        </message>
        <message>
            <source>Port COM nie istnieje. Sprawdź kabel USB, Menedżer urządzeń i odśwież listę portów - numer COM mógł się zmienić.</source>
            <translation>The COM port does not exist. Check the USB cable and Device Manager, then refresh the port list. The COM number may have changed.</translation>
        </message>
        <message>
            <source>Utracono połączenie z adapterem USB-UART (odłączony lub zresetowany). Podłącz go ponownie, odśwież listę portów i powtórz operację.</source>
            <translation>Lost connection to the USB-UART adapter (unplugged or reset). Reconnect it, refresh the port list and repeat the operation.</translation>
        </message>
        <message>
            <source>Uprawnienia: sprawdź `id -nG` (grupa dialout) i `ls -l` na porcie; po `usermod` wyloguj się.</source>
            <translation>Permissions: check `id -nG` (dialout group) and `ls -l` on the port; log out after `usermod`.</translation>
        </message>
        <message>
            <source>Port zajęty: `fuser -v /dev/ttyUSB0`, `systemctl status ModemManager`.</source>
            <translation>Port busy: `fuser -v /dev/ttyUSB0`, `systemctl status ModemManager`.</translation>
        </message>
        <message>
            <source>Brak portu: `dmesg | tail`, `lsusb` (oczekiwane 1a86:7523, sterownik ch341).</source>
            <translation>No port: `dmesg | tail`, `lsusb` (expected 1a86:7523, ch341 driver).</translation>
        </message>
        <message>
            <source>Backend: `pipx install stcgal` lub wskaż ścieżkę w Ustawieniach.</source>
            <translation>Backend: `pipx install stcgal` or set the path in Settings.</translation>
        </message>
        <message>
            <source>Dostęp: zamknij inne programy używające COM; uruchom ponownie aplikację.</source>
            <translation>Access: close other programs using COM and restart the app.</translation>
        </message>
        <message>
            <source>Port zajęty: zamknij terminale szeregowe/inne programmery; w Menedżerze urządzeń sprawdź numer COM.</source>
            <translation>Port busy: close serial terminals and other programmers; check the COM number in Device Manager.</translation>
        </message>
        <message>
            <source>Backend: pakiet aplikacji jest niekompletny (brak stcgal-backend.exe) - zainstaluj ponownie.</source>
            <translation>Backend: the app package is incomplete (stcgal-backend.exe is missing). Reinstall it.</translation>
        </message>
        <message>
            <source>Brak portu: Menedżer urządzeń → Porty (COM i LPT); oczekiwany „USB-SERIAL CH340 (COMx)”, VID_1A86&amp;PID_7523.</source>
            <translation>No port: Device Manager → Ports (COM &amp; LPT); expected “USB-SERIAL CH340 (COMx)”, VID_1A86&amp;PID_7523.</translation>
        </message>
        <message>
            <source>Utrata urządzenia: sprawdź kabel/hub USB, zasilanie i ponownie wykryj port.</source>
            <translation>Device lost: check the USB cable or hub and power, then detect the port again.</translation>
        </message>
        <message>
            <source>Timeout: wyłącz i włącz zasilanie MCU zaraz po starcie wykrywania; nie odłączaj CH340; sprawdź TX↔RX, GND, poziomy logiczne.</source>
            <translation>Timeout: power-cycle the MCU right after detection starts; do not unplug the CH340; check TX↔RX, GND and logic levels.</translation>
        </message>
        <message>
            <source>Handshake: wybierz protokół ręcznie (STC8H → stc8d) lub obniż prędkość handshake.</source>
            <translation>Handshake: select the protocol manually (STC8H → stc8d) or lower the handshake speed.</translation>
        </message>
        <message>
            <source>Protokół: spróbuj niższego baud, krótszych przewodów i stabilnego zasilania.</source>
            <translation>Protocol: try a lower baud rate, shorter wires and a stable power supply.</translation>
        </message>
        <message>
            <source>Nie znaleziono wbudowanego backendu (stcgal-backend.exe). Pakiet aplikacji jest uszkodzony lub niekompletny - zainstaluj ponownie albo wskaż stcgal w Ustawieniach.</source>
            <translation>The built-in backend (stcgal-backend.exe) was not found. The app package is damaged or incomplete. Reinstall it or set the stcgal path in Settings.</translation>
        </message>
        <message>
            <source>Nie znaleziono programu stcgal. Zainstaluj: pipx install stcgal lub wskaż ścieżkę w Ustawieniach.</source>
            <translation>stcgal was not found. Install it with: pipx install stcgal, or set the path in Settings.</translation>
        </message>
    </context>
    <context>
        <name>DiagnosticsTab</name>
        <message>
            <source>Wszystkie</source>
            <translation>All</translation>
        </message>
        <message>
            <source>Ostrzeżenia i błędy</source>
            <translation>Warnings and errors</translation>
        </message>
        <message>
            <source>Tylko błędy</source>
            <translation>Errors only</translation>
        </message>
        <message>
            <source>Zdarzenia</source>
            <translation>Events</translation>
        </message>
        <message>
            <source>Surowy output (stdout/stderr)</source>
            <translation>Raw output (stdout/stderr)</translation>
        </message>
        <message>
            <source>Filtr poziomu zdarzeń</source>
            <translation>Event level filter</translation>
        </message>
        <message>
            <source>Szukaj w logu (Ctrl+F)…</source>
            <translation>Search the log (Ctrl+F)…</translation>
        </message>
        <message>
            <source>Tryb debug stcgal (-D)</source>
            <translation>stcgal debug mode (-D)</translation>
        </message>
        <message>
            <source>Wypisuje surowe pakiety protokołu (poziom DEBUG)</source>
            <translation>Prints raw protocol packets (DEBUG level)</translation>
        </message>
        <message>
            <source>Redaguj dane wrażliwe</source>
            <translation>Redact sensitive data</translation>
        </message>
        <message>
            <source>Przy kopiowaniu i eksporcie zastępuje katalog domowy, nazwę użytkownika/hosta, numery seryjne USB</source>
            <translation>When copying and exporting, replaces the home directory, user and host names and USB serial numbers</translation>
        </message>
        <message>
            <source>Kopiuj</source>
            <translation>Copy</translation>
        </message>
        <message>
            <source>Kopiuj zaznaczone (lub wszystkie widoczne) zdarzenia</source>
            <translation>Copy the selected (or all visible) events</translation>
        </message>
        <message>
            <source>Eksportuj…</source>
            <translation>Export…</translation>
        </message>
        <message>
            <source>Wyczyść</source>
            <translation>Clear</translation>
        </message>
        <message>
            <source>Informacje o środowisku</source>
            <translation>Environment info</translation>
        </message>
        <message>
            <source>Wynik ostatniej operacji</source>
            <translation>Last operation result</translation>
        </message>
        <message>
            <source>Brak zgłoszonych problemów.</source>
            <translation>No problems reported.</translation>
        </message>
        <message>
            <source>%1 z %2 zdarzeń</source>
            <translation>%1 of %2 events</translation>
        </message>
        <message>
            <source>Ostatnia operacja zakończona powodzeniem.</source>
            <translation>The last operation succeeded.</translation>
        </message>
        <message>
            <source>Eksportuj log</source>
            <translation>Export log</translation>
        </message>
        <message>
            <source>Log (*.log *.txt)</source>
            <translation>Log (*.log *.txt)</translation>
        </message>
        <message>
            <source># stcgal-gui %1 - zdarzenia (przefiltrowane widokiem)</source>
            <translation># stcgal-gui %1: events (filtered by the view)</translation>
        </message>
        <message>
            <source># Surowy output stcgal</source>
            <translation># Raw stcgal output</translation>
        </message>
        <message>
            <source>Port %1 vid:pid=%2 dostęp=%3</source>
            <translation>Port %1 vid:pid=%2 access=%3</translation>
        </message>
        <message>
            <source>tak</source>
            <translation>yes</translation>
        </message>
        <message>
            <source>NIE</source>
            <translation>NO</translation>
        </message>
    </context>
    <context>
        <name>Firmware</name>
        <message>
            <source>Linia %1: %2</source>
            <translation>Line %1: %2</translation>
        </message>
        <message>
            <source>dane po rekordzie końca pliku</source>
            <translation>data after the end-of-file record</translation>
        </message>
        <message>
            <source>niepoprawny rekord Intel HEX</source>
            <translation>invalid Intel HEX record</translation>
        </message>
        <message>
            <source>znaki spoza zapisu szesnastkowego</source>
            <translation>characters outside hexadecimal notation</translation>
        </message>
        <message>
            <source>niezgodna długość rekordu</source>
            <translation>record length mismatch</translation>
        </message>
        <message>
            <source>błędna suma kontrolna</source>
            <translation>bad checksum</translation>
        </message>
        <message>
            <source>nieznany typ rekordu %1</source>
            <translation>unknown record type %1</translation>
        </message>
        <message>
            <source>Brak rekordu końca pliku (:00000001FF)</source>
            <translation>Missing end-of-file record (:00000001FF)</translation>
        </message>
        <message>
            <source>Plik nie istnieje</source>
            <translation>The file does not exist</translation>
        </message>
        <message>
            <source>Plik jest pusty</source>
            <translation>The file is empty</translation>
        </message>
        <message>
            <source>Plik jest zbyt duży</source>
            <translation>The file is too large</translation>
        </message>
        <message>
            <source>Nieobsługiwane rozszerzenie. stcgal rozpoznaje Intel HEX tylko po rozszerzeniu .hex/.ihx/.ihex; inne pliki zapisuje jako surowy BIN.</source>
            <translation>Unsupported extension. stcgal treats a file as Intel HEX only by the .hex/.ihx/.ihex extension; other files are written as raw BIN.</translation>
        </message>
        <message>
            <source>Plik HEX zawiera znaki spoza ASCII</source>
            <translation>The HEX file contains non-ASCII characters</translation>
        </message>
        <message>
            <source>Plik HEX nie zawiera danych</source>
            <translation>The HEX file contains no data</translation>
        </message>
        <message>
            <source>Plik .bin wygląda jak Intel HEX (zaczyna się od „:”). stcgal zapisałby tekst jako surowe dane - zmień rozszerzenie na .hex.</source>
            <translation>The .bin file looks like Intel HEX (it starts with “:”). stcgal would write the text as raw data. Change the extension to .hex.</translation>
        </message>
        <message>
            <source>Plik zawiera wyłącznie bajty 0xFF (pusty obraz).</source>
            <translation>The file contains only 0xFF bytes (empty image).</translation>
        </message>
        <message>
            <source>Brak informacji o pamięci MCU - najpierw wykryj mikrokontroler.</source>
            <translation>No MCU memory information. Detect the microcontroller first.</translation>
        </message>
        <message>
            <source>Firmware (%1 B) przekracza całą pamięć programu+EEPROM (%2 B); stcgal obcina nadmiar.</source>
            <translation>Firmware (%1 B) exceeds the whole program + EEPROM memory (%2 B); stcgal truncates the excess.</translation>
        </message>
        <message>
            <source>Firmware (%1 B) wchodzi w obszar EEPROM (kod: %2 B) - zostanie zapisany także w segmencie EEPROM.</source>
            <translation>Firmware (%1 B) reaches into the EEPROM area (code: %2 B) and will also be written to the EEPROM segment.</translation>
        </message>
        <message>
            <source>Obraz EEPROM (%1 B) większy niż EEPROM (%2 B) - zostanie obcięty.</source>
            <translation>The EEPROM image (%1 B) is larger than the EEPROM (%2 B) and will be truncated.</translation>
        </message>
        <message>
            <source>Obraz kodu nachodzi na EEPROM - stcgal obetnie go, by dopisać obraz EEPROM.</source>
            <translation>The code image overlaps the EEPROM; stcgal will truncate it to append the EEPROM image.</translation>
        </message>
    </context>
    <context>
        <name>InfoButton</name>
        <message>
            <source>Informacja</source>
            <translation>Information</translation>
        </message>
    </context>
    <context>
        <name>LinkState</name>
        <message>
            <source>Brak adaptera</source>
            <translation>No adapter</translation>
        </message>
        <message>
            <source>Adapter dostępny</source>
            <translation>Adapter available</translation>
        </message>
        <message>
            <source>Oczekiwanie na zasilenie MCU</source>
            <translation>Waiting for MCU power</translation>
        </message>
        <message>
            <source>Trwa identyfikacja</source>
            <translation>Identifying</translation>
        </message>
        <message>
            <source>Trwa programowanie</source>
            <translation>Programming</translation>
        </message>
        <message>
            <source>Mikrokontroler wykryty</source>
            <translation>Microcontroller detected</translation>
        </message>
        <message>
            <source>Przekroczono czas oczekiwania</source>
            <translation>Timed out</translation>
        </message>
        <message>
            <source>Błąd komunikacji</source>
            <translation>Communication error</translation>
        </message>
    </context>
    <context>
        <name>LogTableModel</name>
        <message>
            <source>Czas</source>
            <translation>Time</translation>
        </message>
        <message>
            <source>Poziom</source>
            <translation>Level</translation>
        </message>
        <message>
            <source>Źródło</source>
            <translation>Source</translation>
        </message>
        <message>
            <source>Komunikat</source>
            <translation>Message</translation>
        </message>
    </context>
    <context>
        <name>MainWindow</name>
        <message>
            <source> [SYMULACJA]</source>
            <translation> [SIMULATION]</translation>
        </message>
        <message>
            <source>STC Programmer GUI</source>
            <translation>STC Programmer GUI</translation>
        </message>
        <message>
            <source>Połączenie</source>
            <translation>Connection</translation>
        </message>
        <message>
            <source>Mikrokontroler</source>
            <translation>Microcontroller</translation>
        </message>
        <message>
            <source>Programowanie</source>
            <translation>Programming</translation>
        </message>
        <message>
            <source>Odczyt i kopia</source>
            <translation>Read and backup</translation>
        </message>
        <message>
            <source>Diagnostyka</source>
            <translation>Diagnostics</translation>
        </message>
        <message>
            <source>Ustawienia</source>
            <translation>Settings</translation>
        </message>
        <message>
            <source>Nawigacja</source>
            <translation>Navigation</translation>
        </message>
        <message>
            <source>Gotowy</source>
            <translation>Ready</translation>
        </message>
        <message>
            <source>Przerwać zapis?</source>
            <translation>Stop writing?</translation>
        </message>
        <message>
            <source>Przerwanie w trakcie zapisu może zostawić niekompletny firmware. Przerwać?</source>
            <translation>Stopping during a write can leave incomplete firmware. Stop anyway?</translation>
        </message>
        <message>
            <source>Wykryto problem - zobacz Diagnostykę</source>
            <translation>A problem was detected. See Diagnostics</translation>
        </message>
        <message>
            <source>Operacja w toku</source>
            <translation>Operation in progress</translation>
        </message>
        <message>
            <source>Trwa operacja na porcie szeregowym. Anulować i zamknąć?</source>
            <translation>An operation is running on the serial port. Cancel it and close?</translation>
        </message>
        <message>
            <source>Anulowanie operacji… okno zamknie się po jej zakończeniu</source>
            <translation>Cancelling the operation… the window will close when it ends</translation>
        </message>
    </context>
    <context>
        <name>McuDb</name>
        <message>
            <source>Dla %1 stcgal w trybie auto używa protokołu „%2”, a wybrano „%3”. Niezgodny protokół może uniemożliwić zapis.</source>
            <translation>For %1, stcgal in auto mode uses the “%2” protocol, but “%3” is selected. A mismatched protocol may prevent writing.</translation>
        </message>
    </context>
    <context>
        <name>McuReport</name>
        <message>
            <source>Reset i zasilanie</source>
            <translation>Reset and power</translation>
        </message>
        <message>
            <source>Pin RST jako wejście resetu</source>
            <translation>RST pin as reset input</translation>
        </message>
        <message>
            <source>Reset przy niskim napięciu (LVD)</source>
            <translation>Low-voltage reset (LVD)</translation>
        </message>
        <message>
            <source>Próg niskiego napięcia</source>
            <translation>Low-voltage threshold</translation>
        </message>
        <message>
            <source>Opóźnienie resetu po włączeniu zasilania</source>
            <translation>Reset delay after power-on</translation>
        </message>
        <message>
            <source>Stan wyjścia P2.0 po resecie</source>
            <translation>P2.0 output state after reset</translation>
        </message>
        <message>
            <source>Watchdog</source>
            <translation>Watchdog</translation>
        </message>
        <message>
            <source>Watchdog włączony po włączeniu zasilania</source>
            <translation>Watchdog enabled at power-on</translation>
        </message>
        <message>
            <source>Zatrzymanie watchdoga w trybie idle</source>
            <translation>Watchdog stopped in idle mode</translation>
        </message>
        <message>
            <source>Dzielnik watchdoga</source>
            <translation>Watchdog prescaler</translation>
        </message>
        <message>
            <source>Zegar</source>
            <translation>Clock</translation>
        </message>
        <message>
            <source>Wzmocnienie oscylatora</source>
            <translation>Oscillator gain</translation>
        </message>
        <message>
            <source>UART</source>
            <translation>UART</translation>
        </message>
        <message>
            <source>Przemapowanie UART1</source>
            <translation>UART1 pin remap</translation>
        </message>
        <message>
            <source>Przelot UART2</source>
            <translation>UART2 passthrough</translation>
        </message>
        <message>
            <source>Tryb pinów UART2</source>
            <translation>UART2 pin mode</translation>
        </message>
        <message>
            <source>Bootloader i EEPROM</source>
            <translation>Bootloader and EEPROM</translation>
        </message>
        <message>
            <source>Wejście do bootloadera po stanie pinu</source>
            <translation>Enter bootloader by pin state</translation>
        </message>
        <message>
            <source>Kasowanie EEPROM razem z flash</source>
            <translation>Erase EEPROM together with flash</translation>
        </message>
        <message>
            <source>Podział flash/EEPROM (bajty)</source>
            <translation>Flash/EEPROM split (bytes)</translation>
        </message>
        <message>
            <source>Inne</source>
            <translation>Other</translation>
        </message>
        <message>
            <source>Wyjścia EPWM jako open-drain</source>
            <translation>EPWM outputs as open-drain</translation>
        </message>
        <message>
            <source>baza modeli stcgal (wg identyfikatora, nie pomiar)</source>
            <translation>stcgal model database (by identifier, not measured)</translation>
        </message>
        <message>
            <source>odpowiedź bootloadera układu</source>
            <translation>chip bootloader response</translation>
        </message>
        <message>
            <source>Model</source>
            <translation>Model</translation>
        </message>
        <message>
            <source>Identyfikator (magic)</source>
            <translation>Identifier (magic)</translation>
        </message>
        <message>
            <source>Protokół</source>
            <translation>Protocol</translation>
        </message>
        <message>
            <source>Bootloader</source>
            <translation>Bootloader</translation>
        </message>
        <message>
            <source>Flash (kod)</source>
            <translation>Flash (code)</translation>
        </message>
        <message>
            <source>Częstotliwość</source>
            <translation>Frequency</translation>
        </message>
        <message>
            <source>Zegar wybudzania</source>
            <translation>Wake-up clock</translation>
        </message>
        <message>
            <source>Data produkcji</source>
            <translation>Manufacturing date</translation>
        </message>
        <message>
            <source>Dodatkowe</source>
            <translation>Additional</translation>
        </message>
        <message>
            <source># Raport MCU - %1</source>
            <translation># MCU report: %1</translation>
        </message>
        <message>
            <source>nieznany</source>
            <translation>unknown</translation>
        </message>
        <message>
            <source>Wygenerowano: %1 · stcgal-gui %2 · Python %3</source>
            <translation>Generated: %1 · stcgal-gui %2 · Python %3</translation>
        </message>
        <message>
            <source>Port: %1</source>
            <translation>Port: %1</translation>
        </message>
        <message>
            <source>## Podstawowe (źródło: %1)</source>
            <translation>## Basic (source: %1)</translation>
        </message>
        <message>
            <source>## Pamięć (źródło: %1)</source>
            <translation>## Memory (source: %1)</translation>
        </message>
        <message>
            <source>## Zegar i zasilanie (źródło: %1)</source>
            <translation>## Clock and power (source: %1)</translation>
        </message>
        <message>
            <source>## Konfiguracja (źródło: %1; tylko odczyt)</source>
            <translation>## Configuration (source: %1; read only)</translation>
        </message>
    </context>
    <context>
        <name>McuTab</name>
        <message>
            <source>Nie zidentyfikowano jeszcze mikrokontrolera.
Użyj „Wykryj mikrokontroler” w widoku Połączenie (Ctrl+D).</source>
            <translation>No microcontroller identified yet.
Use “Detect microcontroller” in the Connection view (Ctrl+D).</translation>
        </message>
        <message>
            <source>Kopiuj raport</source>
            <translation>Copy report</translation>
        </message>
        <message>
            <source>Eksportuj raport…</source>
            <translation>Export report…</translation>
        </message>
        <message>
            <source>Podstawowe informacje</source>
            <translation>Basic information</translation>
        </message>
        <message>
            <source>Źródło: %1</source>
            <translation>Source: %1</translation>
        </message>
        <message>
            <source>Model</source>
            <translation>Model</translation>
        </message>
        <message>
            <source>Identyfikator (magic)</source>
            <translation>Identifier (magic)</translation>
        </message>
        <message>
            <source>Protokół</source>
            <translation>Protocol</translation>
        </message>
        <message>
            <source>Bootloader</source>
            <translation>Bootloader</translation>
        </message>
        <message>
            <source>Pamięć</source>
            <translation>Memory</translation>
        </message>
        <message>
            <source>Flash (kod)</source>
            <translation>Flash (code)</translation>
        </message>
        <message>
            <source>EEPROM / IAP</source>
            <translation>EEPROM / IAP</translation>
        </message>
        <message>
            <source>Zegar i zasilanie</source>
            <translation>Clock and power</translation>
        </message>
        <message>
            <source>Częstotliwość zegara</source>
            <translation>Clock frequency</translation>
        </message>
        <message>
            <source>Zegar wybudzania</source>
            <translation>Wake-up clock</translation>
        </message>
        <message>
            <source>Napięcie referencyjne</source>
            <translation>Reference voltage</translation>
        </message>
        <message>
            <source>Data produkcji</source>
            <translation>Manufacturing date</translation>
        </message>
        <message>
            <source>Konfiguracja (tylko odczyt)</source>
            <translation>Configuration (read only)</translation>
        </message>
        <message>
            <source>Źródło: %1. Nazwy techniczne stcgal w nawiasach.</source>
            <translation>Source: %1. Technical stcgal names in parentheses.</translation>
        </message>
        <message>
            <source>Nieznany model</source>
            <translation>Unknown model</translation>
        </message>
        <message>
            <source>Port %1 · odczytano %2</source>
            <translation>Port %1 · read at %2</translation>
        </message>
        <message>
            <source>Flash %1 B</source>
            <translation>Flash %1 B</translation>
        </message>
        <message>
            <source>EEPROM %1 B</source>
            <translation>EEPROM %1 B</translation>
        </message>
        <message>
            <source>Backend nie zwrócił opcji konfiguracyjnych.</source>
            <translation>The backend returned no configuration options.</translation>
        </message>
        <message>
            <source>Skopiowano raport MCU do schowka</source>
            <translation>MCU report copied to the clipboard</translation>
        </message>
        <message>
            <source>Eksportuj raport MCU</source>
            <translation>Export MCU report</translation>
        </message>
        <message>
            <source>Markdown (*.md);;Tekst (*.txt)</source>
            <translation>Markdown (*.md);;Text (*.txt)</translation>
        </message>
    </context>
    <context>
        <name>MockBackend</name>
        <message>
            <source>Backend symulowany - brak komunikacji ze sprzętem.</source>
            <translation>Simulated backend: no communication with hardware.</translation>
        </message>
        <message>
            <source>Błąd portu (symulacja).</source>
            <translation>Port error (simulation).</translation>
        </message>
        <message>
            <source>Anulowano.</source>
            <translation>Cancelled.</translation>
        </message>
        <message>
            <source>Timeout oczekiwania na MCU.</source>
            <translation>Timed out waiting for the MCU.</translation>
        </message>
        <message>
            <source>Port zajęty przez inną operację</source>
            <translation>The port is used by another operation</translation>
        </message>
        <message>
            <source>Identyfikacja zakończona (symulacja).</source>
            <translation>Identification finished (simulation).</translation>
        </message>
        <message>
            <source>Brak potwierdzenia kasowania</source>
            <translation>Erase not confirmed</translation>
        </message>
        <message>
            <source>Kasowanie zakończone (symulacja).</source>
            <translation>Erase finished (simulation).</translation>
        </message>
        <message>
            <source>Brak potwierdzenia zapisu</source>
            <translation>Write not confirmed</translation>
        </message>
        <message>
            <source>Zakres kasowania nie dotyczy zapisu</source>
            <translation>The erase scope does not apply to writing</translation>
        </message>
        <message>
            <source>Anulowano w trakcie zapisu - firmware może być niekompletny.</source>
            <translation>Cancelled during the write. The firmware may be incomplete.</translation>
        </message>
        <message>
            <source>Błąd protokołu (symulacja).</source>
            <translation>Protocol error (simulation).</translation>
        </message>
        <message>
            <source>Zapis zakończony (symulacja).</source>
            <translation>Write finished (simulation).</translation>
        </message>
    </context>
    <context>
        <name>ProgramTab</name>
        <message>
            <source>Firmware (*.bin *.hex *.ihx *.ihex);;Wszystkie pliki (*)</source>
            <translation>Firmware (*.bin *.hex *.ihx *.ihex);;All files (*)</translation>
        </message>
        <message>
            <source>Plik BIN/HEX do zapisu</source>
            <translation>BIN/HEX file to write</translation>
        </message>
        <message>
            <source>Wybierz…</source>
            <translation>Browse…</translation>
        </message>
        <message>
            <source>Wybierz plik firmware (Ctrl+O)</source>
            <translation>Choose a firmware file (Ctrl+O)</translation>
        </message>
        <message>
            <source>Tryb eksperta</source>
            <translation>Expert mode</translation>
        </message>
        <message>
            <source>Pełne parametry: opcje MCU, częstotliwość, offset obrazu, EEPROM, kasowanie. Operacje wymagają dodatkowych potwierdzeń.</source>
            <translation>Full parameters: MCU options, frequency, image offset, EEPROM, erase. These operations need extra confirmations.</translation>
        </message>
        <message>
            <source>Ryzyko zapisu</source>
            <translation>Write risk</translation>
        </message>
        <message>
            <source>Plik firmware</source>
            <translation>Firmware file</translation>
        </message>
        <message>
            <source>Zapis Flash dotyczy wyłącznie pamięci programu: bez obrazu EEPROM, bez opcji (-o) i bez zmiany częstotliwości. stcgal nie weryfikuje zapisu. Przerwanie zapisu może zostawić niekompletny firmware (bootloader ISP pozostaje dostępny).</source>
            <translation>A Flash write touches program memory only: no EEPROM image, no options (-o) and no frequency change. stcgal does not verify the write. Interrupting a write can leave incomplete firmware (the ISP bootloader stays available).</translation>
        </message>
        <message>
            <source>Programuj</source>
            <translation>Program</translation>
        </message>
        <message>
            <source>Kasuje i zapisuje pamięć programu (Ctrl+Shift+P). Wymaga potwierdzenia.</source>
            <translation>Erases and writes program memory (Ctrl+Shift+P). Needs confirmation.</translation>
        </message>
        <message>
            <source>Anuluj</source>
            <translation>Cancel</translation>
        </message>
        <message>
            <source>Raport wyniku pojawi się po zakończeniu operacji</source>
            <translation>The result report appears when the operation ends</translation>
        </message>
        <message>
            <source>Opcja</source>
            <translation>Option</translation>
        </message>
        <message>
            <source>Obecna</source>
            <translation>Current</translation>
        </message>
        <message>
            <source>Nowa (puste = bez zmiany)</source>
            <translation>New (empty = unchanged)</translation>
        </message>
        <message>
            <source>Opcje MCU (-o)</source>
            <translation>MCU options (-o)</translation>
        </message>
        <message>
            <source>Zmiana option bytes: EEPROM (eeprom_erase_enabled, program_eeprom_split), zegar, watchdog, reset, UART. Wpisz nową wartość tylko tam, gdzie chcesz zmianę. Błędna wartość może zablokować układ.</source>
            <translation>Changes option bytes: EEPROM (eeprom_erase_enabled, program_eeprom_split), clock, watchdog, reset, UART. Enter a new value only where you want a change. A wrong value can lock the chip.</translation>
        </message>
        <message>
            <source>bez zmiany</source>
            <translation>unchanged</translation>
        </message>
        <message>
            <source>Adres początkowy obrazu (dziesiętnie lub 0x…); wcześniejsze bajty zostają wypełnione</source>
            <translation>Image start address (decimal or 0x…); earlier bytes are filled</translation>
        </message>
        <message>
            <source>Parametry zapisu</source>
            <translation>Write parameters</translation>
        </message>
        <message>
            <source>Offset: obraz zostaje przesunięty o podaną liczbę bajtów, a początek wypełniony wybranym bajtem (stcgal zapisuje od adresu 0). Częstotliwość (-t): docelowy zegar RC w kHz.</source>
            <translation>Offset: the image is shifted by the given number of bytes and the start is filled with the chosen byte (stcgal writes from address 0). Frequency (-t): target RC clock in kHz.</translation>
        </message>
        <message>
            <source>Częstotliwość (trim):</source>
            <translation>Frequency (trim):</translation>
        </message>
        <message>
            <source>Offset początkowy:</source>
            <translation>Start offset:</translation>
        </message>
        <message>
            <source>Wypełnienie:</source>
            <translation>Fill byte:</translation>
        </message>
        <message>
            <source>Plik BIN/HEX z danymi EEPROM/IAP</source>
            <translation>BIN/HEX file with EEPROM/IAP data</translation>
        </message>
        <message>
            <source>Programuj Flash + EEPROM</source>
            <translation>Program Flash + EEPROM</translation>
        </message>
        <message>
            <source>EEPROM</source>
            <translation>EEPROM</translation>
        </message>
        <message>
            <source>Osobna operacja: EEPROM/IAP jest nadpisywany razem z Flash (stcgal nie zapisze samego EEPROM). Dane nie podlegają odzyskaniu, a aplikacja nie może ich wcześniej odczytać.</source>
            <translation>A separate operation: EEPROM/IAP is overwritten together with Flash (stcgal cannot write EEPROM alone). The data cannot be recovered and the app cannot read it beforehand.</translation>
        </message>
        <message>
            <source>Kasuj Flash</source>
            <translation>Erase Flash</translation>
        </message>
        <message>
            <source>Kasowanie</source>
            <translation>Erase</translation>
        </message>
        <message>
            <source>Kasuje pamięć programu bez zapisu nowego obrazu. stcgal może przy tym skasować także EEPROM.</source>
            <translation>Erases program memory without writing a new image. stcgal may also erase the EEPROM.</translation>
        </message>
        <message>
            <source>Wybierz plik firmware</source>
            <translation>Choose firmware file</translation>
        </message>
        <message>
            <source>Firmware: %1</source>
            <translation>Firmware: %1</translation>
        </message>
        <message>
            <source>EEPROM: %1</source>
            <translation>EEPROM: %1</translation>
        </message>
        <message>
            <source>Offset: liczba od 0 do 0x20000 (np. 0 lub 0x400)</source>
            <translation>Offset: a number from 0 to 0x20000 (e.g. 0 or 0x400)</translation>
        </message>
        <message>
            <source>Niepoprawna opcja: %1</source>
            <translation>Invalid option: %1</translation>
        </message>
        <message>
            <source>Plik nie przeszedł walidacji</source>
            <translation>The file failed validation</translation>
        </message>
        <message>
            <source>Nie wybrano pliku</source>
            <translation>No file selected</translation>
        </message>
        <message>
            <source>Cel: &lt;b&gt;%1&lt;/b&gt; · port %2 · protokół %3</source>
            <translation>Target: &lt;b&gt;%1&lt;/b&gt; · port %2 · protocol %3</translation>
        </message>
        <message>
            <source>MCU nie zidentyfikowany</source>
            <translation>MCU not identified</translation>
        </message>
        <message>
            <source>Flash %1 B</source>
            <translation>Flash %1 B</translation>
        </message>
        <message>
            <source>EEPROM %1 B</source>
            <translation>EEPROM %1 B</translation>
        </message>
        <message>
            <source>Wykorzystanie flash: %1 z %2 B (%3%)</source>
            <translation>Flash usage: %1 of %2 B (%3%)</translation>
        </message>
        <message>
            <source>Pojemność z bazy modeli stcgal i podziału odczytanego z układu</source>
            <translation>Capacity from the stcgal model database and the split read from the chip</translation>
        </message>
        <message>
            <source>Rozmiar nie został porównany z pamięcią MCU - najpierw wykryj mikrokontroler.</source>
            <translation>The size was not compared with MCU memory. Detect the microcontroller first.</translation>
        </message>
        <message>
            <source>Backend (stcgal) NIE gwarantuje zachowania EEPROM/IAP ani konfiguracji MCU.

</source>
            <translation>The backend (stcgal) does NOT guarantee that EEPROM/IAP or the MCU configuration are preserved.

</translation>
        </message>
        <message>
            <source>

Dane mogą zostać utracone bezpowrotnie. Czy na pewno kontynuować?</source>
            <translation>

Data may be lost permanently. Continue anyway?</translation>
        </message>
        <message>
            <source>Potwierdź ryzyko dla EEPROM i konfiguracji</source>
            <translation>Confirm the risk to EEPROM and configuration</translation>
        </message>
        <message>
            <source>Rozumiem, kontynuuj</source>
            <translation>I understand, continue</translation>
        </message>
        <message>
            <source>Migawka pliku: %1</source>
            <translation>File snapshot: %1</translation>
        </message>
        <message>
            <source>Za chwilę nastąpi KASOWANIE i ZAPIS pamięci %6 mikrokontrolera.

Port: %1
Protokół: %2
MCU: %3
Firmware: %4 (%5 B)

Po rozpoczęciu trzeba będzie wyłączyć i włączyć zasilanie MCU. Kontynuować?</source>
            <translation>The microcontroller's %6 memory is about to be ERASED and WRITTEN.

Port: %1
Protocol: %2
MCU: %3
Firmware: %4 (%5 B)

After it starts you will need to power-cycle the MCU. Continue?</translation>
        </message>
        <message>
            <source>Flash ORAZ EEPROM/IAP</source>
            <translation>Flash AND EEPROM/IAP</translation>
        </message>
        <message>
            <source>programu (Flash)</source>
            <translation>program (Flash)</translation>
        </message>
        <message>
            <source>Potwierdź zapis Flash + EEPROM</source>
            <translation>Confirm Flash + EEPROM write</translation>
        </message>
        <message>
            <source>Potwierdź zapis Flash</source>
            <translation>Confirm Flash write</translation>
        </message>
        <message>
            <source>Kasuj i programuj</source>
            <translation>Erase and program</translation>
        </message>
        <message>
            <source>Operacja anulowana: w trakcie potwierdzania zmienił się port, MCU, plik lub ryzyka.</source>
            <translation>Operation cancelled: the port, MCU, file or risks changed while confirming.</translation>
        </message>
        <message>
            <source>Za chwilę nastąpi KASOWANIE pamięci programu (Flash).

Port: %1
MCU: %2

Kontynuować?</source>
            <translation>The program memory (Flash) is about to be ERASED.

Port: %1
MCU: %2

Continue?</translation>
        </message>
        <message>
            <source>Potwierdź kasowanie Flash</source>
            <translation>Confirm Flash erase</translation>
        </message>
        <message>
            <source>Przygotowanie…</source>
            <translation>Preparing…</translation>
        </message>
        <message>
            <source>Rozpoczęto operację (%1), potwierdzone przez użytkownika</source>
            <translation>Operation started (%1), confirmed by the user</translation>
        </message>
        <message>
            <source>Oczekiwanie na zasilenie MCU</source>
            <translation>Waiting for MCU power</translation>
        </message>
        <message>
            <source>Kasowanie i przygotowanie pamięci…</source>
            <translation>Erasing and preparing memory…</translation>
        </message>
        <message>
            <source>Zapis flash: %1%</source>
            <translation>Writing flash: %1%</translation>
        </message>
        <message>
            <source>Wynik: %1</source>
            <translation>Result: %1</translation>
        </message>
        <message>
            <source>Weryfikacja: NIE wykonano (stcgal nie weryfikuje zawartości po zapisie).</source>
            <translation>Verification: NOT performed (stcgal does not verify contents after writing).</translation>
        </message>
        <message>
            <source>Weryfikacja: wykonana przez backend.</source>
            <translation>Verification: performed by the backend.</translation>
        </message>
        <message>
            <source>Uwaga: stan EEPROM/IAP i option bytes nie jest weryfikowany - wykryj MCU ponownie.</source>
            <translation>Note: the EEPROM/IAP and option bytes state is not verified. Detect the MCU again.</translation>
        </message>
        <message>
            <source>Zakończono (bez weryfikacji)</source>
            <translation>Finished (not verified)</translation>
        </message>
        <message>
            <source>Skasowano</source>
            <translation>Erased</translation>
        </message>
        <message>
            <source>Operacja nie powiodła się lub została przerwana</source>
            <translation>The operation failed or was interrupted</translation>
        </message>
        <message>
            <source>Operacja zakończona</source>
            <translation>Operation finished</translation>
        </message>
    </context>
    <context>
        <name>Safety</name>
        <message>
            <source>Zły zakres operacji</source>
            <translation>Wrong operation scope</translation>
        </message>
        <message>
            <source>Kasowanie ma osobną ścieżkę (erase).</source>
            <translation>Erase has its own code path (erase).</translation>
        </message>
        <message>
            <source>Zmiana opcji MCU (-o)</source>
            <translation>MCU option change (-o)</translation>
        </message>
        <message>
            <source>Zmieniane są option bytes (EEPROM, zegar, watchdog, reset, UART): %1. Nieprawidłowa wartość może zablokować układ lub zmienić jego działanie.</source>
            <translation>Option bytes are being changed (EEPROM, clock, watchdog, reset, UART): %1. A wrong value can lock the chip or change how it behaves.</translation>
        </message>
        <message>
            <source>Zmiana opcji (-o) jest zabroniona</source>
            <translation>Changing options (-o) is not allowed</translation>
        </message>
        <message>
            <source>Zmieniane są option bytes (EEPROM, zegar, watchdog, reset, UART): %1</source>
            <translation>Option bytes are being changed (EEPROM, clock, watchdog, reset, UART): %1</translation>
        </message>
        <message>
            <source>Zmiana częstotliwości (-t)</source>
            <translation>Frequency change (-t)</translation>
        </message>
        <message>
            <source>Zmiana częstotliwości (-t) jest zabroniona</source>
            <translation>Changing the frequency (-t) is not allowed</translation>
        </message>
        <message>
            <source>Trim częstotliwości RC jest częścią option bytes; zmieni się zegar układu.</source>
            <translation>The RC frequency trim is part of the option bytes; the chip clock will change.</translation>
        </message>
        <message>
            <source>Obraz EEPROM w zapisie tylko-Flash</source>
            <translation>EEPROM image in a Flash-only write</translation>
        </message>
        <message>
            <source>Zapis Flash nie może zawierać obrazu EEPROM - użyj osobnej operacji „Flash + EEPROM”.</source>
            <translation>A Flash write cannot include an EEPROM image. Use the separate “Flash + EEPROM” operation.</translation>
        </message>
        <message>
            <source>Brak obrazu EEPROM</source>
            <translation>No EEPROM image</translation>
        </message>
        <message>
            <source>Operacja „Flash + EEPROM” wymaga pliku z danymi EEPROM.</source>
            <translation>The “Flash + EEPROM” operation needs a file with EEPROM data.</translation>
        </message>
        <message>
            <source>MCU nie został zidentyfikowany</source>
            <translation>MCU not identified</translation>
        </message>
        <message>
            <source>Bez identyfikacji nie można sprawdzić, czy obraz mieści się w pamięci kodu. Najpierw użyj „Wykryj mikrokontroler”.</source>
            <translation>Without identification the app cannot check that the image fits in code memory. Use “Detect microcontroller” first.</translation>
        </message>
        <message>
            <source>Nieczytelny obraz firmware</source>
            <translation>Unreadable firmware image</translation>
        </message>
        <message>
            <source>Nie udało się odczytać rozmiaru obrazu.</source>
            <translation>Could not read the image size.</translation>
        </message>
        <message>
            <source>Obraz nachodzi na EEPROM/IAP</source>
            <translation>Image overlaps EEPROM/IAP</translation>
        </message>
        <message>
            <source>Obraz (%1 B) jest większy niż pamięć kodu (%2 B). stcgal wysłałby wtedy jawne kasowanie Flash i EEPROM oraz zapisałby dane w obszarze EEPROM.</source>
            <translation>The image (%1 B) is larger than code memory (%2 B). stcgal would then send an explicit Flash and EEPROM erase and write data into the EEPROM area.</translation>
        </message>
        <message>
            <source>EEPROM/IAP zostanie nadpisany</source>
            <translation>EEPROM/IAP will be overwritten</translation>
        </message>
        <message>
            <source>Ta operacja kasuje i nadpisuje dane w EEPROM/IAP (poza Flash). Dane nie podlegają odzyskaniu. Aplikacja nie potrafi odczytać EEPROM, więc nie wykona kopii.</source>
            <translation>This operation erases and overwrites data in EEPROM/IAP (besides Flash). The data cannot be recovered. The app cannot read EEPROM, so it cannot make a backup.</translation>
        </message>
        <message>
            <source>Backend nie gwarantuje zachowania EEPROM/IAP</source>
            <translation>The backend does not guarantee EEPROM/IAP is preserved</translation>
        </message>
        <message>
            <source>Komenda kasowania stcgal („always seems to erase everything”) może objąć także EEPROM/IAP, nawet przy zapisie samego Flash. Zawartość EEPROM może zostać utracona.</source>
            <translation>The stcgal erase command (“always seems to erase everything”) may also cover EEPROM/IAP, even when writing only Flash. EEPROM contents may be lost.</translation>
        </message>
        <message>
            <source>Backend nie gwarantuje zachowania konfiguracji MCU</source>
            <translation>The backend does not guarantee the MCU configuration is preserved</translation>
        </message>
        <message>
            <source>stcgal zawsze zapisuje blok option bytes (bieżące wartości z układu) i rekalibruje oraz zapisuje trim częstotliwości - zegar (np. 11,05 MHz) może zmienić się nieznacznie, a opcje nie są weryfikowane po zapisie.</source>
            <translation>stcgal always writes the option bytes block (current values from the chip) and recalibrates and writes the frequency trim, so the clock (e.g. 11.05 MHz) may shift slightly. Options are not verified after writing.</translation>
        </message>
        <message>
            <source>Kasowanie wymaga trybu eksperta</source>
            <translation>Erase needs expert mode</translation>
        </message>
        <message>
            <source>Samo kasowanie Flash jest dostępne wyłącznie w trybie eksperta.</source>
            <translation>Erasing Flash on its own is available in expert mode only.</translation>
        </message>
        <message>
            <source>Najpierw użyj „Wykryj mikrokontroler”.</source>
            <translation>Use “Detect microcontroller” first.</translation>
        </message>
        <message>
            <source>Kasowanie usunie program z Flash</source>
            <translation>Erase will remove the program from Flash</translation>
        </message>
        <message>
            <source>Zawartość pamięci programu zostanie nieodwracalnie skasowana.</source>
            <translation>Program memory contents will be erased irreversibly.</translation>
        </message>
        <message>
            <source>Komenda kasowania stcgal („always seems to erase everything”) może objąć także EEPROM/IAP.</source>
            <translation>The stcgal erase command (“always seems to erase everything”) may also cover EEPROM/IAP.</translation>
        </message>
        <message>
            <source>Operacja wymaga znanego modelu zidentyfikowanego MCU (kontrola zgodności układu).</source>
            <translation>The operation needs a known identified MCU model (chip compatibility check).</translation>
        </message>
        <message>
            <source>Kasowanie zablokowane ze względów bezpieczeństwa:</source>
            <translation>Erase blocked for safety reasons:</translation>
        </message>
        <message>
            <source>Zapis zablokowany ze względów bezpieczeństwa EEPROM/konfiguracji MCU:</source>
            <translation>Write blocked to protect the EEPROM and MCU configuration:</translation>
        </message>
    </context>
    <context>
        <name>SettingsTab</name>
        <message>
            <source>/dev/ttyUSB0 lub /dev/serial/by-id/…</source>
            <translation>/dev/ttyUSB0 or /dev/serial/by-id/…</translation>
        </message>
        <message>
            <source>(puste = wbudowany backend aplikacji)</source>
            <translation>(empty = the app's built-in backend)</translation>
        </message>
        <message>
            <source>(puste = backend aplikacji, PATH lub ~/.local/bin)</source>
            <translation>(empty = app backend, PATH or ~/.local/bin)</translation>
        </message>
        <message>
            <source>Systemowy</source>
            <translation>System</translation>
        </message>
        <message>
            <source>Jasny</source>
            <translation>Light</translation>
        </message>
        <message>
            <source>Ciemny</source>
            <translation>Dark</translation>
        </message>
        <message>
            <source>Ścieżka by-id jest stabilna po ponownym podłączeniu</source>
            <translation>The by-id path stays stable after reconnecting</translation>
        </message>
        <message>
            <source>Język interfejsu. Zmiana działa po ponownym uruchomieniu aplikacji.</source>
            <translation>Interface language. A change applies after restarting the app.</translation>
        </message>
        <message>
            <source>Wybierz…</source>
            <translation>Browse…</translation>
        </message>
        <message>
            <source>Automatyczny reset DTR domyślnie</source>
            <translation>Automatic DTR reset by default</translation>
        </message>
        <message>
            <source>Zapisz ustawienia</source>
            <translation>Save settings</translation>
        </message>
        <message>
            <source>Zapisz ustawienia (Ctrl+S)</source>
            <translation>Save settings (Ctrl+S)</translation>
        </message>
        <message>
            <source>Domyślne parametry połączenia</source>
            <translation>Default connection parameters</translation>
        </message>
        <message>
            <source>Port:</source>
            <translation>Port:</translation>
        </message>
        <message>
            <source>Protokół:</source>
            <translation>Protocol:</translation>
        </message>
        <message>
            <source>Transfer (baud):</source>
            <translation>Transfer (baud):</translation>
        </message>
        <message>
            <source>Handshake (baud):</source>
            <translation>Handshake (baud):</translation>
        </message>
        <message>
            <source>Limit czasu:</source>
            <translation>Timeout:</translation>
        </message>
        <message>
            <source>Aplikacja</source>
            <translation>Application</translation>
        </message>
        <message>
            <source>Motyw:</source>
            <translation>Theme:</translation>
        </message>
        <message>
            <source>Język:</source>
            <translation>Language:</translation>
        </message>
        <message>
            <source>Katalog firmware:</source>
            <translation>Firmware folder:</translation>
        </message>
        <message>
            <source>Poziom logowania:</source>
            <translation>Log level:</translation>
        </message>
        <message>
            <source>Ścieżka do stcgal:</source>
            <translation>stcgal path:</translation>
        </message>
        <message>
            <source>Znaleziono stcgal: %1</source>
            <translation>stcgal found: %1</translation>
        </message>
        <message>
            <source>Nie znaleziono stcgal - zainstaluj: pipx install stcgal</source>
            <translation>stcgal not found. Install it with: pipx install stcgal</translation>
        </message>
        <message>
            <source>Katalog firmware</source>
            <translation>Firmware folder</translation>
        </message>
    </context>
    <context>
        <name>StatusHeader</name>
        <message>
            <source>Adapter: -</source>
            <translation>Adapter: -</translation>
        </message>
        <message>
            <source>USB-UART</source>
            <translation>USB-UART</translation>
        </message>
        <message>
            <source>⚠ SYMULACJA (backend mock - brak sprzętu)</source>
            <translation>⚠ SIMULATION (mock backend, no hardware)</translation>
        </message>
        <message>
            <source>MCU: &lt;b&gt;%1&lt;/b&gt; (%2)</source>
            <translation>MCU: &lt;b&gt;%1&lt;/b&gt; (%2)</translation>
        </message>
        <message>
            <source>MCU: nie zidentyfikowany</source>
            <translation>MCU: not identified</translation>
        </message>
    </context>
    <context>
        <name>StcgalBackend</name>
        <message>
            <source>Nieznany protokół: %1</source>
            <translation>Unknown protocol: %1</translation>
        </message>
        <message>
            <source>Nie wybrano portu</source>
            <translation>No port selected</translation>
        </message>
        <message>
            <source>Zapis tylko-Flash nie może zawierać obrazu EEPROM</source>
            <translation>A Flash-only write cannot include an EEPROM image</translation>
        </message>
        <message>
            <source>Opcje -o i -t są dostępne wyłącznie w trybie eksperta</source>
            <translation>Options -o and -t are available in expert mode only</translation>
        </message>
        <message>
            <source>Niepoprawna opcja: %1 (oczekiwano klucz=wartość)</source>
            <translation>Invalid option: %1 (expected key=value)</translation>
        </message>
        <message>
            <source>stcgal nie rozpoznał protokołu dla tego układu. Wybierz protokół ręcznie.</source>
            <translation>stcgal did not recognize the protocol for this chip. Select the protocol manually.</translation>
        </message>
        <message>
            <source>Błąd protokołu ISP. Sprawdź zasilanie, przewody TX/RX, poziomy logiczne i spróbuj niższej prędkości transferu.</source>
            <translation>ISP protocol error. Check the power, the TX/RX wires and logic levels, and try a lower transfer speed.</translation>
        </message>
        <message>
            <source>Niepoprawna opcja konfiguracyjna.</source>
            <translation>Invalid configuration option.</translation>
        </message>
        <message>
            <source>Błąd portu szeregowego.</source>
            <translation>Serial port error.</translation>
        </message>
        <message>
            <source>Operacja zakończona błędem.</source>
            <translation>The operation ended with an error.</translation>
        </message>
        <message>
            <source>stcgal nie wykonuje odczytu zawartości flash ani weryfikacji po zapisie.</source>
            <translation>stcgal does not read flash contents or verify after writing.</translation>
        </message>
        <message>
            <source>Zapis zawsze zapisuje też bajty opcji (bieżące wartości z układu + zmiany -o).</source>
            <translation>A write always writes the option bytes too (current values from the chip plus any -o changes).</translation>
        </message>
        <message>
            <source>Zapis wymaga jawnego potwierdzenia użytkownika dla tego portu i pliku.</source>
            <translation>Writing needs explicit user confirmation for this port and file.</translation>
        </message>
        <message>
            <source>Zakres kasowania nie dotyczy zapisu (użyj erase).</source>
            <translation>The erase scope does not apply to writing (use erase).</translation>
        </message>
        <message>
            <source>Kasowanie wymaga jawnego potwierdzenia (zakres: kasowanie) dla tego portu.</source>
            <translation>Erasing needs explicit confirmation (scope: erase) for this port.</translation>
        </message>
        <message>
            <source>Inna operacja jest już w toku na tym backendzie</source>
            <translation>Another operation is already running on this backend</translation>
        </message>
        <message>
            <source>Zapis przerwany przed kasowaniem: podłączony układ (%1) różni się od zidentyfikowanego (%2). Wykryj mikrokontroler ponownie.</source>
            <translation>Write stopped before erasing: the connected chip (%1) differs from the identified one (%2). Detect the microcontroller again.</translation>
        </message>
        <message>
            <source> Przerwano po rozpoczęciu kasowania/zapisu - firmware w układzie może być niekompletny. Bootloader ISP pozostaje dostępny; zaprogramuj układ ponownie.</source>
            <translation> Stopped after erasing or writing began. The firmware on the chip may be incomplete. The ISP bootloader stays available; program the chip again.</translation>
        </message>
        <message>
            <source>Nie można uruchomić stcgal: %1</source>
            <translation>Cannot start stcgal: %1</translation>
        </message>
        <message>
            <source>Operacja anulowana przez użytkownika.</source>
            <translation>Operation cancelled by the user.</translation>
        </message>
        <message>
            <source> Anulowano po rozpoczęciu kasowania/zapisu.</source>
            <translation> Cancelled after erasing or writing began.</translation>
        </message>
        <message>
            <source>Przekroczono czas oczekiwania na MCU. Wyłącz i ponownie włącz zasilanie układu docelowego po rozpoczęciu wykrywania; sprawdź TX/RX, masę i poziomy logiczne.</source>
            <translation>Timed out waiting for the MCU. Power-cycle the target chip after detection starts; check TX/RX, ground and logic levels.</translation>
        </message>
        <message>
            <source>Przekroczono czas oczekiwania na odpowiedź układu.</source>
            <translation>Timed out waiting for the chip to respond.</translation>
        </message>
        <message>
            <source>Zapis zakończony. stcgal nie wykonuje weryfikacji zawartości flash.</source>
            <translation>Write finished. stcgal does not verify flash contents.</translation>
        </message>
        <message>
            <source>Identyfikacja zakończona.</source>
            <translation>Identification finished.</translation>
        </message>
        <message>
            <source>stcgal zakończył pracę bez informacji o układzie.</source>
            <translation>stcgal finished without any chip information.</translation>
        </message>
    </context>
</TS>
