@echo off
setlocal EnableExtensions

cd /d "%~dp0"
title YouTube Downloader Installer

set "FFMPEG_REPO=https://github.com/FFmpeg/FFmpeg.git"
set "FFMPEG_ZIP_URL=https://github.com/FFmpeg/FFmpeg/archive/refs/heads/master.zip"
set "FFMPEG_DIR=%USERPROFILE%\.flutter_stuff\ffmpeg-source"

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
)

echo Flutter Stuff YouTube Downloader installer
echo.

call :ensure_python_dependencies
if errorlevel 1 goto :failed
echo.

call :ensure_ffmpeg
if errorlevel 1 goto :failed
echo.

echo [OK] Install/update check finished.
echo.
pause
exit /b 0

:failed
echo.
echo [WARN] Install/update check finished with errors.
echo.
pause
exit /b 1

:ensure_python_dependencies
echo Checking Python dependencies and updates...
if not exist "requirements.txt" (
    echo [WARN] requirements.txt was not found.
    exit /b 1
)
echo [INFO] Running dependency update check:
echo        "%PYTHON%" -m pip install --upgrade -r requirements.txt
"%PYTHON%" -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [WARN] Python dependency installation/update failed.
    echo        Check your Python and pip installation, then run this installer again.
    exit /b 1
)
echo [OK] Python dependencies are installed and checked for updates.
exit /b 0

:ensure_ffmpeg
echo Checking FFmpeg...
where ffmpeg >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%F in ('where ffmpeg 2^>nul') do (
        echo [OK] FFmpeg already available: %%F
        ffmpeg -version 2>nul | findstr /b /c:"ffmpeg version"
        call :update_existing_ffmpeg_source
        exit /b 0
    )
)

echo [WARN] FFmpeg is not available in PATH.
echo        The downloader needs FFmpeg for merging video/audio and converting audio.
echo.

if exist "%FFMPEG_DIR%\.git" (
    echo [INFO] FFmpeg source already exists. Checking for source updates...
    git -C "%FFMPEG_DIR%" pull --ff-only
    if errorlevel 1 (
        echo [WARN] Could not update FFmpeg source with Git. Continuing with existing source.
    )
) else if exist "%FFMPEG_DIR%\configure" (
    echo [INFO] FFmpeg source already exists, but it is not a Git checkout.
    echo [INFO] Downloading the latest source ZIP to refresh it.
    call :download_ffmpeg_source
    if errorlevel 1 exit /b 1
) else (
    where git >nul 2>nul
    if errorlevel 1 (
        echo [WARN] Git is not installed or not available in PATH.
        echo [INFO] Downloading FFmpeg source ZIP instead.
        call :download_ffmpeg_source
        if errorlevel 1 exit /b 1
    ) else (
        echo [INFO] Cloning FFmpeg source from:
        echo        %FFMPEG_REPO%
        echo [INFO] Download progress will be shown below.
        git clone --progress "%FFMPEG_REPO%" "%FFMPEG_DIR%"
        if errorlevel 1 (
            echo [WARN] FFmpeg clone failed. Trying source ZIP download instead.
            call :download_ffmpeg_source
            if errorlevel 1 exit /b 1
        )
    )
)

set "FFMPEG_BIN="
for /r "%FFMPEG_DIR%" %%F in (ffmpeg.exe) do (
    if not defined FFMPEG_BIN set "FFMPEG_BIN=%%~dpF"
)

if defined FFMPEG_BIN (
    call :add_to_user_path "%FFMPEG_BIN:~0,-1%"
    where ffmpeg >nul 2>nul
    if not errorlevel 1 (
        echo [OK] FFmpeg has been installed and is available in PATH.
    ) else (
        echo [WARN] FFmpeg path was added, but this terminal cannot find it yet.
        echo        Open a new terminal and run run.bat again.
    )
) else (
    call :add_to_user_path "%FFMPEG_DIR%"
    echo [WARN] The GitHub FFmpeg repository contains source code, not a prebuilt ffmpeg.exe.
    echo        The source folder was downloaded and added to your user PATH as requested:
    echo        %FFMPEG_DIR%
    echo        FFmpeg is still not runnable until you build it or install a binary package.
)
exit /b 0

:update_existing_ffmpeg_source
if exist "%FFMPEG_DIR%\.git" (
    echo [INFO] Existing FFmpeg source checkout found. Checking for source updates...
    git -C "%FFMPEG_DIR%" pull --ff-only
    if errorlevel 1 (
        echo [WARN] Could not check FFmpeg source updates.
    ) else (
        echo [OK] FFmpeg source checkout is up to date or updated.
    )
) else (
    echo [INFO] FFmpeg is already satisfied. No managed source checkout was found to update.
)
exit /b 0

:add_to_user_path
set "PATH_TO_ADD=%~1"
echo [INFO] Adding to user PATH permanently:
echo        %PATH_TO_ADD%
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pathToAdd = [IO.Path]::GetFullPath('%PATH_TO_ADD%'); $userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); $parts = @($userPath -split ';' | Where-Object { $_ }); if ($parts -notcontains $pathToAdd) { [Environment]::SetEnvironmentVariable('Path', (($parts + $pathToAdd) -join ';'), 'User'); Write-Host '[OK] Added to user PATH permanently.' } else { Write-Host '[OK] User PATH already contains this folder.' }"
set "PATH=%PATH%;%PATH_TO_ADD%"
exit /b 0

:download_ffmpeg_source
echo [INFO] Downloading FFmpeg source from:
echo        %FFMPEG_ZIP_URL%
echo [INFO] Download and extraction progress will be shown below.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'Continue'; $zipUrl = '%FFMPEG_ZIP_URL%'; $dest = [Environment]::ExpandEnvironmentVariables('%FFMPEG_DIR%'); $zip = Join-Path $env:TEMP 'ffmpeg-source.zip'; $extract = Join-Path $env:TEMP ('ffmpeg-source-' + [Guid]::NewGuid().ToString()); New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null; Invoke-WebRequest -Uri $zipUrl -OutFile $zip; Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force; $src = Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1; if (-not $src) { throw 'Downloaded archive did not contain a source folder.' }; if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }; Move-Item -LiteralPath $src.FullName -Destination $dest; Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue; Write-Host '[OK] FFmpeg source downloaded and extracted.'"
if errorlevel 1 (
    echo [WARN] FFmpeg source download failed.
    exit /b 1
)
exit /b 0
