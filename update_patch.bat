@echo off
setlocal
title Update Patch Da Capo III Plus Story
cd /d "%~dp0"

echo ===============================================================================
echo                   PEMBARUAN PATCH DA CAPO III PLUS STORY
echo ===============================================================================
echo.
echo [*] Mendelegasikan ke builder patch lengkap terpadu (build_full_patch.py)...
echo     Builder otomatis: menyalin naskah scenario (.binu8), font kustom,
echo     UI Config (.datu8 dari CSV), UI Layout (.spm), PNG hasil edit,
echo     dan video lirik OP Indonesia — komponen yang tidak ada DILEWATI.
echo.

python build_full_patch.py --install --zip
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo [ERROR] Builder gagal dengan kode %RC%. Pastikan:
    echo     - Python terpasang dan ada di PATH
    echo     - Jalankan dari folder root proyek
    echo.
    pause
    exit /b %RC%
)

echo.
echo ===============================================================================
echo                       [SUKSES] PATCH DIPERBARUI!
echo ===============================================================================
echo.
echo LOKASI OUTPUT DAN STATUS:
echo.
echo [1] Emulator Eden - Terpasang dan Siap Dimainkan:
echo     %APPDATA%\eden\load\010041601B544000\Da Capo III Plus Story Patch\romfs
echo.
echo [2] Folder Mod Lokal - Struktur LayeredFS:
echo     %~dp0DC3PS_Indo_Patch\romfs
echo.
echo [3] Paket ZIP - Siap Dibagikan / Salin ke Nintendo Switch SD Card:
echo     %~dp0DC3PS_Translation_Patch.zip
echo     Plus 3 paket ZIP rilis resmi dari build_release_packages.py
echo.
echo ===============================================================================
echo.
echo [i] KEBIJAKAN DISTRIBUSI:
echo     Patch bahasa Indonesia DISTRIBUSIKAN TERPISAH dari base game
echo     (format LayeredFS ZIP di atas) agar tidak melanggar hak cipta Nintendo.
echo     Pengguna memasang patch dengan menyalin isi ZIP ke folder mod emulator/konsol.
echo.
echo     Pembuatan NSP gabungan (base + patch) dinonaktifkan.
echo     Video lirik OP Indonesia: encode sesuai docs\SPEK_ENCODE_VIDEO.md,
echo     lalu salin ke romfs\Movie\dc3ps_op.mp4 pada patch.
echo.
echo Selesai.
pause
endlocal
