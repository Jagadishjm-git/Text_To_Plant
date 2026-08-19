@echo off
echo ==========================================================
echo STARTING DEPARTMENT-BASED PLANT IDENTIFICATION PORTAL
echo ==========================================================
cd /d "%~dp0"
echo [1/3] Checking dependencies...
pip install -r requirements.txt
echo.
echo [2/3] Initializing database & seed accounts...
python init_db.py
echo.
echo [3/3] Launching Web Server on http://127.0.0.1:5000 ...
echo - Landing Page:       http://127.0.0.1:5000/
echo - Department Login:   http://127.0.0.1:5000/login  (BOTANY001 / Botany@Password123)
echo - Admin Console:      http://127.0.0.1:5000/admin/login (admin / Admin@Botanical2026!)
echo.
python main.py
pause
