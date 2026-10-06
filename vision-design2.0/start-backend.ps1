# Start Backend Service
Write-Host "`n🚀 Starting Vision Design Backend...`n" -ForegroundColor Cyan

$env:PYTHONPATH = "G:\Github\DAYOUR\Vision-Design"
Set-Location "G:\Github\DAYOUR\Vision-Design"

Write-Host "Backend will start on: http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs available at: http://localhost:8000/docs`n" -ForegroundColor Green

C:/Python313/python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
