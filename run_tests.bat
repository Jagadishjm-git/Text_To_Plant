@echo off
echo ==========================================================
echo RUNNING 12-SCENARIO DEPARTMENT AUTHENTICATION TEST SUITE
echo ==========================================================
cd /d "%~dp0\Text_To_Plant-main"
python test_auth_and_access.py
echo.
echo ==========================================================
echo RUNNING BOTANICAL PIPELINE VERIFICATION SUITE (25 CASES)
echo ==========================================================
python test_pipeline_20.py
echo.
pause
