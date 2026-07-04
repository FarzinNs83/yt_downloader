@echo off
setlocal EnableExtensions

cd /d "%~dp0"
title YouTube Downloader

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
)

call :warn_if_setup_missing
echo.

if "%~1"=="" (
    "%PYTHON%" yt_downloader.py
    set "EXIT_CODE=%ERRORLEVEL%"
    echo.
    pause
) else (
    "%PYTHON%" yt_downloader.py %*
    set "EXIT_CODE=%ERRORLEVEL%"
)

exit /b %EXIT_CODE%

:warn_if_setup_missing
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo [WARN] FFmpeg is not available in PATH.
    echo        Run install.bat to set up FFmpeg support.
) else (
    for /f "delims=" %%F in ('where ffmpeg 2^>nul') do (
        echo [OK] FFmpeg found: %%F
        goto :check_python_dependencies
    )
)

:check_python_dependencies
if not exist "requirements.txt" (
    echo [WARN] requirements.txt was not found.
    goto :eof
)

"%PYTHON%" -c "import rich, yt_dlp" >nul 2>nul
if errorlevel 1 (
    echo [WARN] Python dependencies are missing.
    echo        Run install.bat to install them.
) else (
    echo [OK] Python dependencies found.
)
goto :eof
