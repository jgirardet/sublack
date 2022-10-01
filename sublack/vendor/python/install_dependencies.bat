@echo off

set VENDORDIR=%CD%
set VENVDIR=%VENDORDIR%/../.venv_dependencies
cd windows
call python -m virtualenv %VENVDIR%
cd %VENVDIR%/Scripts
activate & py -m pip install requests & py -m pip install toml & py -m pip install PyYAML & pause