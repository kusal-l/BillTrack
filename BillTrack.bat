@echo off
cd /d "C:\Users\kusal\Desktop\BillTrack\local_version"
start "Server" cmd /k python server.py
timeout /t 2 /nobreak >nul
start http://localhost:3000