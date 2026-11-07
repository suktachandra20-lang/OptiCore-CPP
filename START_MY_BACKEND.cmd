@echo off
cd /d "%~dp0"

echo OptiCore Member 2 - Automatic Backend

python -u auto_backend.py --tests --dashboard

echo.
echo Check the result above.
pause