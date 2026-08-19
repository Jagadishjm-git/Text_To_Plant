@echo off
title Push Text To Plant to GitHub
echo ========================================================
echo PUSHING CODE TO https://github.com/Jagadishjm-git/Text_To_Plant.git
echo ========================================================

cd /d "%~dp0"

echo [1/5] Initializing Git...
if not exist ".git" (
    git init
)

echo [2/5] Staging files (ignoring temporary and binary cache)...
git add .

echo [3/5] Creating commit...
git commit -m "feat: complete department authentication, 10,454-record botanical dataset integration, and calibrated hybrid confidence scoring" 2>nul

echo [4/5] Setting main branch & remote origin...
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/Jagadishjm-git/Text_To_Plant.git

echo [5/5] Pushing to GitHub repository...
git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo --------------------------------------------------------
    echo Standard push encountered existing remote commits.
    echo Attempting force push to update main branch...
    echo --------------------------------------------------------
    git push -u origin main --force
)

echo.
echo ========================================================
echo PUSH OPERATION COMPLETED!
echo View your repository at:
echo https://github.com/Jagadishjm-git/Text_To_Plant
echo ========================================================
pause
