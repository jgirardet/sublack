@echo off

set VENDORDIR=%CD%
set VENVDIR=%VENDORDIR%/../.venv
cd windows
call python -m virtualenv %VENVDIR%
cd %VENVDIR%/Scripts
activate & py -m pip install black & py -m pip install black[d]