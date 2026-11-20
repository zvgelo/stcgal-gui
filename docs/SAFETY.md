# Bezpieczeństwo danych MCU: EEPROM/IAP i konfiguracja (option bytes)

**Priorytet:** żadnych niejawnych zmian EEPROM/IAP, option bytes ani konfiguracji (zegar, watchdog,
reset, UART). W razie wątpliwości operacja jest **blokowana**, a nie wykonywana z ryzykiem utraty danych.
Zasady są identyczne na Linuksie i Windows (jeden kod: `core/safety.py`, egzekwowany w backendzie).

## Co naprawdę robi stcgal 1.10 (analiza źródeł)

| Element | Zachowanie | Skutek |
|---|---|---|
| Identyfikacja (bez pliku i bez `-e`) | `connect` + odczyt statusu + `disconnect`; nie woła `handshake`, kasowania ani `program_options` | **niedestrukcyjna** |
| `erase_flash` (STC15/STC8/stc8d) | komenda `0x03`; docstring autorów: *„this protocol always seems to erase everything”*. Parametr 2. bajtu: `0x00` „tylko flash”, `0x01` „flash **i EEPROM**” - wybierany, gdy obraz jest większy niż pamięć kodu albo podano obraz EEPROM | nie da się zagwarantować zachowania EEPROM nawet przy zapisie samego Flash |
| `handshake()` / `calibrate()` | rekalibracja częstotliwości RC (trim) | zegar może się nieznacznie zmienić |
| `program_options` | **zawsze** po zapisie flash: zapisuje cały blok opcji (bajty MSR odczytane z układu + zmiany `-o`) oraz trim | brak trybu „tylko flash”; opcje są przepisywane |
| Weryfikacja | brak | nie można potwierdzić, że EEPROM/opcje pozostały bez zmian |
| Odczyt EEPROM/Flash | brak | nie da się zrobić kopii przed zapisem |

Wniosek: backend **nie potrafi** zagwarantować zachowania EEPROM/IAP ani konfiguracji. Dlatego
`Capabilities.preserves_eeprom` i `preserves_options` dla stcgal mają wartość `False`.

### Dokładność analizy (szczegóły potwierdzone w źródłach)

* Warunek kasowania: stcgal porównuje długość obrazu **po dopełnieniu do 512 B** (`bindata`) z `code_size`
  (`frontend.py`): `erase_size <= flash_size` → `0x00`, inaczej `0x01` (Flash **i EEPROM**). GUI porównuje rozmiar przed
  dopełnieniem; dla STC8H8K64U (kod 65024 B = wielokrotność 512) jest to równoważne.
* `code_size` ustawia podział `program_eeprom_split` tylko wtedy, gdy podano `-o program_eeprom_split` (`Stc8dProtocol.set_option`).
  Bez `-o` stcgal używa `model.code` z bazy i **ignoruje** podział zapisany w układzie. Aplikacja bierze mniejszą z obu
  wartości (ostrożniej).
* `get_flash_split` zwraca `msr[4]*256`; `set_flash_split` wymaga wielokrotności 512 - wartość z układu nie musi być
  podzielna przez 512.
* Rozmiar obrazu HEX liczymy **dokładnie jak `stcgal.ihex.IHex`** (sklejanie obszarów, „splice” nakładających się
  rekordów, rekordy bazy liniowej ignorowane); zgodność sprawdza test na losowych plikach z prawdziwym `stcgal.ihex`.
  stcgal wybiera HEX/BIN wyłącznie po **nazwie** pliku, dlatego aplikacja nie rozwiązuje symlinków.

## Polityka aplikacji

1. **Identyfikacja** - zawsze niedestrukcyjna: polecenie bez pliku, `-e`, `-o`, `-t` (test dla każdego
   protokołu i flag). Skrypty budowania i CI nigdy nie otwierają portów ani nie wołają `stcgal` z portem
   (test regresyjny skanuje skrypty).
2. **Zapis Flash** obejmuje wyłącznie pamięć programu: bez obrazu EEPROM, bez `-o`, bez `-t`.
3. **Tryb podstawowy** (domyślny, prosty): wybór pliku i jeden przycisk. Ryzyka twarde, których nie da się obejść:
   zmiana opcji (`-o`, w tym `eeprom_erase_enabled` i `program_eeprom_split`), zmiana częstotliwości (`-t`), obraz EEPROM
   w zapisie Flash, MCU niezidentyfikowany lub identyfikacja starsza niż 15 min, obraz większy niż obszar kodu.
4. **Ryzyka miękkie** (backend bez gwarancji, czyli stcgal): każdy zapis wymaga **dwóch osobnych potwierdzeń**: zapisu
   oraz ryzyka dla EEPROM i konfiguracji (domyślny przycisk: Anuluj). Odmowa w którymkolwiek anuluje operację.
   **Tryb eksperta** (przełącznik, wyłączony przy każdym starcie) odblokowuje pełne parametry: opcje `-o` (edytor
   z wartościami bieżącymi), trim `-t`, offset i wypełnienie obrazu, zapis Flash+EEPROM oraz samo kasowanie Flash.
   W trybie eksperta zmiany opcji, trimu i obraz nachodzący na EEPROM są ryzykami miękkimi (lista w dialogu
   ryzyka); backend egzekwuje to samo na podstawie flagi `expert` w `WriteConfirmation`. Kasowanie bez trybu eksperta
   jest odrzucane przez backend.
5. **Zapis Flash + EEPROM** to osobna operacja (tryb eksperta, własny przycisk, własne potwierdzenia). stcgal nie
   potrafi zapisać samego EEPROM - dane są dopisywane do obrazu, więc Flash jest przy tym kasowany.
6. **Konfiguracja MCU** jest w aplikacji wyłącznie do odczytu; aplikacja nigdy nie przywraca wartości domyślnych.
7. **Migawka pliku:** przed zapisem pliki są kopiowane do prywatnego katalogu; rozmiar/format sprawdza się na kopii i ta
   sama kopia trafia do stcgal (brak podmiany pliku po sprawdzeniu - TOCTOU; spójny format przy symlinkach). Katalog jest
   sprzątany po operacji.
8. **Świeża identyfikacja:** zapis wymaga udanego wykrycia MCU na bieżącym porcie, nie starszego niż 15 minut; każde
   „Wykryj” kasuje poprzedni wynik (nieudana identyfikacja nie zostawia starego MCU).
9. **Zgodność układu w trakcie zapisu:** backend porównuje model zgłoszony przez stcgal (`Name:`, wypisywany przed
   kasowaniem) z zidentyfikowanym; przy różnicy przerywa **przed** kasowaniem („inny układ niż zidentyfikowany”).
10. **Dialogi:** na czas okien potwierdzenia wstrzymane jest automatyczne odświeżanie portów, a po dialogach ponownie
    sprawdzany jest port, MCU, plik i ryzyka; zmiana w trakcie anuluje zapis.
11. **Egzekwowanie w backendzie** (wymaga znanego modelu MCU; żądany `program_eeprom_split` zawęża obszar kodu; zakres kasowania nie dotyczy zapisu) (`Backend.program()`): niemutowalne `WriteConfirmation` (zakres, pojemność kodu, model,
    zbiór zaakceptowanych ryzyk, kontrola typów) i `SafetyError` zanim uruchomi się proces. To obrona w głąb - backend
    ufa danym o MCU od wywołującego, dlatego dodatkowo działa kontrola z pkt 9.
12. **Symulacja** (`MockBackend`) włącza się wyłącznie jawnym `--mock` (bez zmiennej środowiskowej), z banerem
    „SYMULACJA” w oknie i domyślnie bez deklaracji gwarancji.
13. Aplikacja **nie deklaruje** zachowania EEPROM/opcji ani poprawnej weryfikacji - raport po zapisie mówi
    wprost, że stan EEPROM/IAP i option bytes nie jest weryfikowany.

## Co to znaczy w praktyce dla STC8H8K64U

Zapis firmware przez stcgal jest zawsze obarczony ryzykiem utraty zawartości EEPROM (512 B, obszar IAP)
oraz przepisania opcji i trimu zegara. Aplikacja pokazuje te ryzyka i wymaga świadomej decyzji. Jeżeli
zawartość EEPROM jest dla Ciebie krytyczna, zapisz ją innym narzędziem przed programowaniem - ta aplikacja
nie potrafi jej odczytać.

Testy: `tests/test_safety_eeprom.py`. Zapis i kasowanie na fizycznym STC8H8K64U **nie były testowane**.
