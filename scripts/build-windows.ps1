<#
.SYNOPSIS
  Natywny build STC-Programmer.exe (onefile) na Windows 10/11 x64 - bez uprawnień administratora.

.DESCRIPTION
  Pobiera izolowany Python (pakiet NuGet, bez instalatora i bez zmian w systemie), instaluje
  zależności z packaging\requirements-build.txt (PySide6, pyserial, PyInstaller, stcgal 1.10),
  buduje backend (stcgal) i GUI wspólną konfiguracją PyInstaller (packaging\pyinstaller\*.spec,
  scripts\pyi_build.py - tą samą co build-windows.sh pod Wine), weryfikuje wynik i liczy SHA-256.

  Wynik:  dist\windows\STC-Programmer.exe        (onefile)
          dist\windows-onedir\STC-Programmer\    (-Onedir; wariant diagnostyczny)

.PARAMETER Clean      Usuń poprzednie wyniki i katalogi robocze buildu.
.PARAMETER Onedir     Zbuduj wariant onedir (diagnostyczny) zamiast onefile.
.PARAMETER SkipTests  Pomiń testy uruchomieniowe wyniku (--selftest, --smoke-gui).
.PARAMETER PythonExe  Użyj istniejącego Pythona 3.12/3.13 x64 zamiast pobierać izolowany
                      (zależności zostaną zainstalowane DO TEGO interpretera - np. w CI).
.PARAMETER PythonVersion  Wersja Pythona do pobrania (domyślnie 3.13.12).
.PARAMETER PythonSha256   Oczekiwany SHA-256 pakietu NuGet (domyślnie przypięty dla 3.13.12).
.PARAMETER CacheDir   Katalog cache (domyślnie %LOCALAPPDATA%\stcgal-gui-winbuild).
.PARAMETER Installer  Dodatkowo zbuduj instalator Inno Setup (wymaga ISCC.exe; używa wariantu onedir).
.PARAMETER Verbose    (parametr wspólny) pełne wyjście pip/PyInstaller.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Clean -Verbose
#>
[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$Onedir,
    [switch]$SkipTests,
    [string]$PythonExe = "",
    [string]$PythonVersion = "3.13.12",
    [string]$PythonSha256 = "",
    [string]$CacheDir = "",
    [switch]$Installer
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest bez paska postępu jest wielokrotnie szybszy

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$IsVerbose = ($VerbosePreference -eq 'Continue')
if (-not $CacheDir) { $CacheDir = Join-Path $env:LOCALAPPDATA 'stcgal-gui-winbuild' }
$LogDir = Join-Path $CacheDir 'logs'
New-Item -ItemType Directory -Force -Path $LogDir, (Join-Path $CacheDir 'downloads') | Out-Null
$script:LogFile = Join-Path $LogDir ("build-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType File -Force -Path $script:LogFile | Out-Null
$Requirements = Join-Path $Root 'packaging\requirements-build.txt'
$KnownPythonSha256 = @{ '3.13.12' = '389c0228afbb3530f6cd079f5cec44139b1441dd51c85ec704f7a63f1c9f3802' }
if (-not $PythonSha256 -and $KnownPythonSha256.ContainsKey($PythonVersion)) { $PythonSha256 = $KnownPythonSha256[$PythonVersion] }

function Say([string]$Message) {
    Write-Host "[build-windows] $Message" -ForegroundColor Cyan
    Add-Content -Path $script:LogFile -Value "[build-windows] $Message"
}

function Invoke-Native {
    # Uruchamia program natywny: pełne wyjście do logu, na ekran tylko w trybie -Verbose
    # (oraz linie [pyi_build] OK/FAIL). Zgłasza wyjątek przy kodzie != 0 (chyba że -AllowFail:
    # wtedy zwraca kod). Uwaga PS 5.1: stderr programu natywnego nie może wyzwalać wyjątku.
    param([string]$Exe, [string[]]$Arguments, [switch]$AllowFail)
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { throw "Nie znaleziono programu: $Exe" }
    Add-Content -Path $script:LogFile -Value ('$ ' + $Exe + ' ' + ($Arguments -join ' '))
    $global:LASTEXITCODE = 0
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object {
            $line = "$_"
            Add-Content -Path $script:LogFile -Value $line
            if ($IsVerbose -or $line -match '^\[pyi_build\] (OK|FAIL|tryb)') { Write-Host $line }
        }
        $code = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previous }
    if ($AllowFail) { return $code }
    if ($code -ne 0) { throw "Polecenie zakończone kodem ${code}: $Exe $($Arguments -join ' ')" }
}

function Get-NativeOutput {
    # Zwraca stdout programu natywnego; pusty wynik lub kod != 0 to błąd (nigdy cicha pusta wartość).
    param([string]$Exe, [string[]]$Arguments)
    $global:LASTEXITCODE = 0
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $out = & $Exe @Arguments 2>$null; $code = $LASTEXITCODE }
    finally { $ErrorActionPreference = $previous }
    $text = (($out | Out-String).Trim())
    if ($code -ne 0 -or -not $text) { throw "Polecenie nie zwróciło wyniku (kod ${code}): $Exe $($Arguments -join ' ')" }
    return $text
}

function Get-IsolatedPython {
    # NuGet 'python' to pełny interpreter (tools\python.exe) w zwykłym archiwum ZIP:
    # nie wymaga instalatora, rejestru ani administratora.
    $dir = Join-Path $CacheDir "py\$PythonVersion"
    $exe = Join-Path $dir 'tools\python.exe'
    if (-not (Test-Path $exe)) {
        $pkg = Join-Path $CacheDir "downloads\python-$PythonVersion.zip"
        if (-not (Test-Path $pkg)) {
            Say "    pobieranie Pythona $PythonVersion (NuGet)"
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $part = "$pkg.part"
            Invoke-WebRequest -UseBasicParsing -Uri "https://www.nuget.org/api/v2/package/python/$PythonVersion" -OutFile $part
            Move-Item -Force $part $pkg
        }
        if ($PythonSha256) {
            $actual = (Get-FileHash -Algorithm SHA256 $pkg).Hash.ToLower()
            if ($actual -ne $PythonSha256.ToLower()) {
                Remove-Item -Force $pkg
                throw "Suma SHA-256 pakietu Pythona nie zgadza się (oczekiwano $PythonSha256, jest $actual) - pakiet usunięto."
            }
        }
        else { Say "    UWAGA: brak przypiętej sumy SHA-256 dla Pythona $PythonVersion (użyj -PythonSha256)" }
        if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Expand-Archive -Path $pkg -DestinationPath $dir -Force
        if (-not (Test-Path $exe)) { throw "Pakiet Pythona nie zawiera tools\python.exe (usuń $pkg i ponów)" }
        Remove-Item -Force (Join-Path $CacheDir 'deps.stamp') -ErrorAction SilentlyContinue
    }
    return $exe
}

try {
    $mode = if ($Onedir) { 'onedir' } else { 'onefile' }

    Say '1/7 Sprawdzanie środowiska'
    if ([System.Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Ten skrypt działa tylko na Windows (na Linuksie: scripts/build-windows.sh).' }
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Wymagany Windows x64.' }
    $env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONNOUSERSITE = '1'
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'

    Say '2/7 Interpreter Pythona'
    if ($PythonExe) {
        $py = (Get-Command $PythonExe -ErrorAction Stop).Source
        Say "    użyto wskazanego interpretera: $py"
    }
    else { $py = Get-IsolatedPython }
    $pyInfo = Get-NativeOutput $py @((Join-Path $Root 'scripts\pyinfo.py'))
    if ($pyInfo -notmatch '^3\.(12|13)\.\d+ 64$') { throw "Wymagany Python 3.12/3.13 x64, wykryto: '$pyInfo'" }
    $pyVersion = ($pyInfo -split ' ')[0]
    Say "    Python $pyVersion (x64): $py"

    Say '3/7 Zależności (PySide6, pyserial, PyInstaller, stcgal 1.10)'
    $stampFile = Join-Path $CacheDir 'deps.stamp'
    $stamp = "$((Get-FileHash -Algorithm SHA256 $Requirements).Hash)-$pyVersion-$py"
    $current = if (Test-Path $stampFile) { (Get-Content $stampFile -Raw).Trim() } else { '' }
    if ($PythonExe -or ($current -ne $stamp)) {
        Invoke-Native $py @('-m', 'ensurepip', '--upgrade')
        Invoke-Native $py @('-m', 'pip', 'install', '--only-binary=:all:', '--no-warn-script-location', '-r', $Requirements)
        Set-Content -Path $stampFile -Value $stamp
    }
    else { Say '    zależności aktualne (cache) - pomijam' }
    $frozen = (Get-NativeOutput $py @('-m', 'pip', 'list', '--format=freeze')) -split "`r?`n"
    function PkgVersion([string]$name) {
        $m = $frozen | Where-Object { $_ -match "^$([regex]::Escape($name))==" } | Select-Object -First 1
        if ($m) { return ($m -split '==')[1] } else { return '?' }
    }
    $verPySide = PkgVersion 'PySide6'; $verPyi = PkgVersion 'pyinstaller'; $verStcgal = PkgVersion 'stcgal'
    Say "    PySide6 $verPySide · PyInstaller $verPyi · stcgal $verStcgal"
    if ($verStcgal -ne '1.10') { throw "Oczekiwano stcgal 1.10, jest '$verStcgal'" }

    Say '4/7 Ikona'
    if (-not (Test-Path (Join-Path $Root 'packaging\windows\stcgal-gui.ico'))) {
        Invoke-Native $py @((Join-Path $Root 'scripts\make_icon.py'))
    }

    Say "5/7 Budowanie ($mode) - PyInstaller (kilka minut; log: $script:LogFile)"
    Push-Location $Root
    try {
        $buildArgs = @('scripts\pyi_build.py', '--mode', $mode)
        if ($Clean) { $buildArgs += '--clean' }
        if ($SkipTests) { $buildArgs += '--skip-verify'; Say '    (testy uruchomieniowe pominięte: -SkipTests)' }
        $buildCode = Invoke-Native $py $buildArgs -AllowFail   # raport powstaje także po niepowodzeniu testów
        if ($Installer -and $mode -ne 'onedir' -and $buildCode -eq 0) {
            Say '    wariant onedir dla instalatora'
            Invoke-Native $py @('scripts\pyi_build.py', '--mode', 'onedir', '--skip-verify')
        }
    }
    finally { Pop-Location }

    $outDir = if ($Onedir) { Join-Path $Root 'dist\windows-onedir' } else { Join-Path $Root 'dist\windows' }
    $exe = if ($Onedir) { Join-Path $outDir 'STC-Programmer\STC-Programmer.exe' } else { Join-Path $outDir 'STC-Programmer.exe' }

    Say '6/7 Weryfikacja wyniku i suma SHA-256'
    if (-not (Test-Path $exe)) { throw "Nie powstał plik wynikowy: $exe (kod PyInstaller: $buildCode)" }
    $item = Get-Item $exe
    $hash = (Get-FileHash -Algorithm SHA256 $exe).Hash.ToLower()
    $reportJson = Join-Path $outDir 'build-report.json'
    $failures = @()
    if (Test-Path $reportJson) {
        $failures = @((Get-Content $reportJson -Raw | ConvertFrom-Json).failures)
    }
    $testsLine = if ($SkipTests) { 'POMINIĘTE (-SkipTests)' } elseif ($failures.Count -eq 0) { 'PRZESZŁY' } else { 'NIEPOWODZENIE: ' + ($failures -join '; ') }
    $lines = @(
        "STC Programmer GUI - build Windows x64 ($mode) $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
        ('Status kompilacji : ' + $(if ($buildCode -eq 0) { 'OK' } else { 'BŁĄD (kod ' + $buildCode + ')' })),
        "Plik              : $exe",
        ('Rozmiar           : {0:N0} B ({1:N1} MiB)' -f $item.Length, ($item.Length / 1MB)),
        "SHA-256           : $hash",
        "Testy uruchomien. : $testsLine",
        "Python            : $pyVersion",
        "PyInstaller       : $verPyi",
        "PySide6           : $verPySide",
        "stcgal (backend)  : $verStcgal (wbudowany)",
        'UWAGA: wynik zweryfikowany testami dymnymi (--selftest, --smoke-gui); komunikacja z fizycznym MCU nie była testowana.'
    )
    $lines | Set-Content -Path (Join-Path $outDir 'BUILD-REPORT.txt') -Encoding UTF8
    $lines | ForEach-Object { Write-Host $_ }
    Set-Content -Path (Join-Path $outDir 'STC-Programmer.sha256') -Value "$hash  $(Split-Path -Leaf $exe)" -Encoding ASCII
    if ($failures.Count -gt 0 -or $buildCode -ne 0) { throw "Build lub testy uruchomieniowe nie przeszły (kod $buildCode): $($failures -join '; ')" }

    if ($Installer) {
        Say '7/7 Instalator Inno Setup'
        $iscc = (Get-Command ISCC -ErrorAction SilentlyContinue)
        $candidates = @()
        if ($iscc) { $candidates += $iscc.Source }
        foreach ($b in @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)) {
            if ($b) { $candidates += (Join-Path $b 'Inno Setup 6\ISCC.exe'); $candidates += (Join-Path $b 'Programs\Inno Setup 6\ISCC.exe') }
        }
        $isccPath = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
        if (-not $isccPath) { throw 'Nie znaleziono ISCC.exe (zainstaluj Inno Setup 6, np. winget install JRSoftware.InnoSetup).' }
        $appVersion = Get-NativeOutput $py @((Join-Path $Root 'scripts\appversion.py'))
        Invoke-Native $isccPath @("/DAppVersion=$appVersion", (Join-Path $Root 'packaging\windows\installer.iss'))
        $setup = Join-Path $Root 'dist\STC-Programmer-Setup-x64.exe'
        if (-not (Test-Path $setup)) { throw "Instalator nie powstał: $setup" }
        $setupHash = (Get-FileHash -Algorithm SHA256 $setup).Hash.ToLower()
        Say ("    instalator: {0} ({1:N1} MiB) SHA-256 {2}" -f $setup, ((Get-Item $setup).Length / 1MB), $setupHash)
    }
    else { Say '7/7 Instalator pominięty (użyj -Installer)' }

    Say "Gotowe: $exe"
    Say "Log: $script:LogFile"
    exit 0
}
catch {
    Write-Host "[build-windows] BŁĄD: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Pełny log: $script:LogFile" -ForegroundColor Red
    exit 1
}
