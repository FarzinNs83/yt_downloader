@echo off
setlocal

cd /d "%~dp0"
title YouTube Downloader

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
)

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
