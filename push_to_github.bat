@echo off
title Push Text To Plant to Jagadishjm-git GitHub
echo ========================================================
echo PUSHING TO https://github.com/Jagadishjm-git/Text_To_Plant.git
echo AS USER: Jagadishjm-git
echo ========================================================

cd /d "%~dp0"

echo [1/4] Staging files...
git init
git add .
git commit -m "feat: complete department authentication, 10,454-record botanical dataset integration, and calibrated hybrid confidence scoring" 2>nul

echo [2/4] Setting main branch...
git branch -M main

echo [3/4] Configuring remote URL for Jagadishjm-git...
git remote remove origin 2>nul
git remote add origin https://Jagadishjm-git@github.com/Jagadishjm-git/Text_To_Plant.git

echo [4/4] Pushing to GitHub...
echo (A GitHub login window or token prompt will appear - please sign in as Jagadishjm-git)
git push -u origin main --force

echo.
echo ========================================================
echo PUSH COMPLETED!
echo Repository: https://github.com/Jagadishjm-git/Text_To_Plant
echo ========================================================
pause
