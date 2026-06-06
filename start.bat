@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Iniciando el Sistema de Turnos - Hotel La Palma y el Tucan...
python servidor_turnos.py
pause
