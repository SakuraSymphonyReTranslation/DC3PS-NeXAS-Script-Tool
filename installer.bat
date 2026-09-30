@echo off
setlocal
title Installer Patch Da Capo III Plus Story Bahasa Indonesia

echo ===============================================================================
echo         INSTALLER PATCH BAHASA INDONESIA - DA CAPO III PLUS STORY
echo ===============================================================================
echo.
echo Installer ini akan mendeteksi emulator Nintendo Switch yang terpasang
echo di PC Anda dan memasang patch otomatis.
echo.
echo Cara pakai: LETAKKAN installer.bat ini SEJAJAR dengan folder "load"
echo dari paket ZIP, lalu dobel-klik. (Jika Anda mengekstrak seluruh ZIP,
echo file ini sudah berada di posisi yang benar.)
echo.

set "TID=010041601B544000"
set "MOD=Da Capo III Plus Story Patch"
set "FOUND=0"

if not exist "load\%TID%\%MOD%\romfs" (
    echo [ERROR] Folder load\%TID%\%MOD%\romfs tidak ditemukan di lokasi ini!
    echo Jalankan installer ini dari dalam folder hasil ekstrak ZIP.
    pause
    exit /b 1
)

REM ---------- Eden ----------
set "EDEN=%APPDATA%\eden\load\%TID%"
if exist "%APPDATA%\eden" (
    echo [*] Eden terdeteksi - memasang patch...
    if not exist "%EDEN%\%MOD%\romfs" mkdir "%EDEN%\%MOD%\romfs"
    xcopy /e /i /y "load\%TID%\%MOD%\romfs" "%EDEN%\%MOD%\romfs" >nul
    echo     OK: %EDEN%\%MOD%\romfs
    set "FOUND=1"
)

REM ---------- Citron ----------
if exist "%APPDATA%\citron" (
    echo [*] Citron terdeteksi.
    echo     Untuk Citron: klik kanan game ^> Open Mod Data Location, lalu
    echo     salin isi folder "load\%TID%\%MOD%" ke folder yang terbuka.
    set "FOUND=1"
)

REM ---------- Yuzu ----------
if exist "%APPDATA%\yuzu" (
    set "YUZU=%APPDATA%\yuzu\load\%TID%"
    echo [*] Yuzu terdeteksi - memasang patch...
    if not exist "%YUZU%\%MOD%\romfs" mkdir "%YUZU%\%MOD%\romfs"
    xcopy /e /i /y "load\%TID%\%MOD%\romfs" "%YUZU%\%MOD%\romfs" >nul
    echo     OK: %YUZU%\%MOD%\romfs
    set "FOUND=1"
)

REM ---------- Ryujinx ----------
if exist "%APPDATA%\Ryujinx" (
    set "RYU=%APPDATA%\Ryujinx\mods\contents\%TID%"
    echo [*] Ryujinx terdeteksi - memasang patch...
    if not exist "%RYU%\romfs" mkdir "%RYU%\romfs"
    xcopy /e /i /y "load\%TID%\%MOD%\romfs" "%RYU%\romfs" >nul
    echo     OK: %RYU%\romfs
    set "FOUND=1"
)

REM ---------- Sudachi / portable paths ----------
if exist "%USERPROFILE%\AppData\Roaming\sudachi" (
    set "SUD=%USERPROFILE%\AppData\Roaming\sudachi\load\%TID%"
    echo [*] Sudachi terdeteksi - memasang patch...
    if not exist "%SUD%\%MOD%\romfs" mkdir "%SUD%\%MOD%\romfs"
    xcopy /e /i /y "load\%TID%\%MOD%\romfs" "%SUD%\%MOD%\romfs" >nul
    echo     OK: %SUD%\%MOD%\romfs
    set "FOUND=1"
)

echo.
if "%FOUND%"=="0" (
    echo [!] Tidak ada emulator terdeteksi di lokasi standar.
    echo     Untuk emulator Android / lokasi portable: salin manual folder
    echo     "load\%TID%\%MOD%" ke folder "load" milik emulator Anda.
) else (
    echo [SUKSES] Patch terpasang. Jalankan game dan nikmati terjemahannya!
)
echo.
pause
endlocal
