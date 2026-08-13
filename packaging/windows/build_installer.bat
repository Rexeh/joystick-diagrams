@echo off
rem Compiles the Inno Setup installer.
rem
rem Usage: build_installer.bat <version>
rem
rem This exists so the makefile never has to hand cmd.exe a command line
rem containing both quoted paths with spaces and forward slashes - cmd's switch
rem parser matches the "/c" inside "/config.iss" as a second /C switch and tries
rem to execute "onfig.iss".
setlocal enabledelayedexpansion

set "APP_VERSION=%~1"
if not defined APP_VERSION (
    echo ERROR: no version supplied. Usage: build_installer.bat ^<version^>
    exit /b 1
)

if not defined ISCC set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "!ISCC!" for %%I in (ISCC.exe) do set "ISCC=%%~$PATH:I"
if not exist "!ISCC!" (
    echo ERROR: ISCC.exe not found. Install Inno Setup 6, or set the ISCC
    echo environment variable to the full path of ISCC.exe.
    exit /b 1
)

echo Using !ISCC!
"!ISCC!" /Qp /DVersion="!APP_VERSION!" "%~dp0..\..\installer\config.iss"
exit /b %ERRORLEVEL%
