# Vision Design - Service Restart Script
# Simple script to help restart backend and frontend services

Write-Host "`n🧹 Vision Design - Service Restart`n" -ForegroundColor Cyan

# Stop Python processes on port 8000
Write-Host "Stopping Python processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Stop Node processes  
Write-Host "Stopping Node processes..." -ForegroundColor Yellow
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host "`n✅ Services stopped`n" -ForegroundColor Green

# Instructions to start manually
Write-Host "To start services, run these commands in separate terminals:`n" -ForegroundColor White
Write-Host "Backend:  cd G:\Github\DAYOUR\Vision-Design && C:/Python313/python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Gray
Write-Host "Frontend: cd G:\Github\DAYOUR\Vision-Design\frontend && npm run dev`n" -ForegroundColor Gray

Write-Host "Or use these PowerShell commands:" -ForegroundColor White
Write-Host '  Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd G:\Github\DAYOUR\Vision-Design; C:/Python313/python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"' -ForegroundColor Gray
Write-Host '  Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd G:\Github\DAYOUR\Vision-Design\frontend; npm run dev"' -ForegroundColor Gray
Write-Host ""
