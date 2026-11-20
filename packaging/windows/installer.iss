; Inno Setup 6 - instalator STC Programmer GUI (Windows 10/11 x64)
; Build: scripts\build-windows.ps1 -Installer   (buduje wariant onedir i wywołuje ISCC /DAppVersion=...)
; Wynik: dist\STC-Programmer-Setup-x64.exe

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppName "STC Programmer GUI"
#define AppExe "STC-Programmer.exe"

[Setup]
; Stały AppId: ten sam identyfikator = aktualizacja "nad" poprzednią wersją (bez deinstalacji).
AppId={{B2C1E8D4-7A3F-4C55-9E21-5D0F6A1C9B77}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=stcgal-gui
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} - instalator
; Instalacja per-user (bez administratora); użytkownik może wybrać instalację dla wszystkich (dialog).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\STC Programmer
DefaultGroupName=STC Programmer
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=STC-Programmer-Setup-x64
SetupIconFile=stcgal-gui.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Aktualizacja: zamknij działającą aplikację (usuwa blokady plików), nie restartuj.
CloseApplications=yes
RestartApplications=no
MinVersion=10.0

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
polish.RemoveSettings=Czy usunąć także zapisane ustawienia aplikacji (port, protokół, motyw, położenie okna)?%nWybierz „Nie”, aby zachować je na wypadek ponownej instalacji.
english.RemoveSettings=Also remove the saved application settings (port, protocol, theme, window layout)?%nChoose "No" to keep them in case you reinstall.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\windows-onedir\STC-Programmer\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\STC Programmer"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\STC Programmer"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; Brak sekcji [UninstallDelete] dla konfiguracji: ustawienia (QSettings) leżą w rejestrze
; HKCU\Software\stcgal-gui i nie są usuwane bez decyzji użytkownika (patrz [Code]).

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { Tryb cichy (/VERYSILENT) zawsze zachowuje ustawienia. }
    if not UninstallSilent() then
    begin
      if MsgBox(ExpandConstant('{cm:RemoveSettings}'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        RegDeleteKeyIncludingSubkeys(HKCU, 'Software\stcgal-gui');
    end;
  end;
end;
