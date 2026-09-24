@echo off
title Compound Ops - LAN Server
cd /d "%~dp0"
echo ============================================
echo   COMPOUND OPS - LAN SERVER
echo ============================================
echo.
echo Opening firewall port 8080 (may ask for admin)...
netsh advfirewall firewall delete rule name="CompoundOps8080" >nul 2>&1
netsh advfirewall firewall add rule name="CompoundOps8080" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1
if errorlevel 1 (
  echo   [!] Could not open the firewall - run this file as Administrator.
) else (
  echo   OK - port 8080 is open for other PCs on your network.
)
echo.
node lan_server.js 8080
pause
