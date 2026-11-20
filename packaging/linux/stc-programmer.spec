# Pakiet RPM z gotowego katalogu PyInstaller (bez kompilacji). Wywołanie: scripts/build-linux.sh
%global debug_package %{nil}
%global __os_install_post %{nil}
AutoReqProv: no

Name:           stc-programmer
Version:        %{app_version}
Release:        1
Summary:        Graficzny programator mikrokontrolerów STC (stcgal)
License:        MIT
URL:            https://github.com/zvgelo/stcgal-gui
Requires:       libxkbcommon, mesa-libEGL, mesa-libGL, fontconfig, dbus-libs, xcb-util-cursor

%description
Aplikacja do identyfikacji i programowania mikrokontrolerów STC przez UART/ISP.
Zawiera wbudowany backend stcgal 1.10.

%install
mkdir -p %{buildroot}/opt/stc-programmer %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications %{buildroot}%{_datadir}/icons/hicolor/256x256/apps
cp -a %{app_dir}/. %{buildroot}/opt/stc-programmer/
install -m 0755 %{pkg_dir}/launcher.sh %{buildroot}/opt/stc-programmer/launcher.sh
ln -s /opt/stc-programmer/launcher.sh %{buildroot}%{_bindir}/stc-programmer
install -m 0644 %{pkg_dir}/stc-programmer.desktop %{buildroot}%{_datadir}/applications/stc-programmer.desktop
install -m 0644 %{pkg_dir}/stc-programmer.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/stc-programmer.png

%files
/opt/stc-programmer
%{_bindir}/stc-programmer
%{_datadir}/applications/stc-programmer.desktop
%{_datadir}/icons/hicolor/256x256/apps/stc-programmer.png
