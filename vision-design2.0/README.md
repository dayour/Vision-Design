# Vision Design 2.0 - Clean Scripts Collection

This folder contains the cleaned, working scripts for Vision Design development.

## 📁 Contents

### Service Management Scripts

#### `restart-services.ps1`
**Purpose:** Cleanly stops all running Python and Node processes  
**Usage:**
```powershell
.\restart-services.ps1
```
**What it does:**
- Stops all Python processes (backend)
- Stops all Node processes (frontend)
- Provides commands to restart services manually

#### `start-backend.ps1`
**Purpose:** Starts the FastAPI backend server  
**Usage:**
```powershell
.\start-backend.ps1
```
**What it does:**
- Sets PYTHONPATH environment variable
- Starts uvicorn server on port 8000
- Enables auto-reload for development
- Shows backend URL and API docs location

#### `start-frontend.ps1`
**Purpose:** Starts the Next.js frontend  
**Usage:**
```powershell
.\start-frontend.ps1
```
**What it does:**
- Changes to frontend directory
- Runs `npm run dev` to start Next.js
- Shows frontend URL

### Testing Scripts

#### `test_flux.py`
**Purpose:** Direct test of Flux API integration  
**Usage:**
```powershell
C:/Python313/python.exe test_flux.py
```
**What it tests:**
- Flux client initialization
- Foundry API connection
- Simple image generation ("a red circle")
- Returns generation success/failure

#### `test-pipeline.ps1`
**Purpose:** Test the image pipeline endpoint with PowerShell  
**Usage:**
```powershell
.\test-pipeline.ps1
```
**What it tests:**
- POST request to `/api/v1/images/pipeline`
- Form data submission
- Save options disabled for quick testing
- Shows detailed error messages

### Documentation

#### `SESSION_SUMMARY.md`
Complete session summary including:
- All fixes implemented
- Current service status
- Known issues
- Configuration details
- Quick start commands
- Debugging recommendations

## 🚀 Quick Start Workflow

### 1. Stop All Services
```powershell
cd G:\Github\DAYOUR\Vision-Design\vision-design2.0
.\restart-services.ps1
```

### 2. Start Backend (in separate terminal)
```powershell
cd G:\Github\DAYOUR\Vision-Design\vision-design2.0
.\start-backend.ps1
```

### 3. Start Frontend (in separate terminal)
```powershell
cd G:\Github\DAYOUR\Vision-Design\vision-design2.0
.\start-frontend.ps1
```

### 4. Test the Backend
```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health"

# Test endpoint
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/images/test"

# Flux direct test
C:/Python313/python.exe test_flux.py
```

## 🔧 Using These Scripts From Anywhere

To use these scripts from the root directory:

```powershell
# Stop services
.\vision-design2.0\restart-services.ps1

# Start backend (in separate window)
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd G:\Github\DAYOUR\Vision-Design; .\vision-design2.0\start-backend.ps1"

# Start frontend (in separate window)
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd G:\Github\DAYOUR\Vision-Design\frontend; npm run dev"
```

## 📋 Key Features

### ✅ What's Working
- **Backend:** FastAPI + Uvicorn on port 8000
- **Frontend:** Next.js 15.2.4 on port 3000
- **Flux API:** Direct generation via Foundry
- **Test Endpoints:** Health check and images test working
- **Service Management:** Clean start/stop/restart

### 🐛 Known Issues
- Image generation from UI returns 500 error
- Gallery returns 503 (Dataverse not configured)
- Folders endpoint returns 404
- Authentication shows 0/4 (CLI tools not installed)

### 🔍 Debugging Tools
1. **Test Endpoint:** `http://localhost:8000/api/v1/images/test`
2. **Enhanced Logging:** Backend logs now show detailed pipeline info
3. **Direct API Test:** `test_flux.py` bypasses FastAPI completely
4. **Pipeline Test:** `test-pipeline.ps1` tests the actual endpoint

## 🎯 Next Steps

1. **Debug Image Generation:**
   - Watch backend terminal during generation attempt
   - Look for error logs in the pipeline endpoint
   - Test with save_options.enabled = false

2. **Fix Dataverse Integration:**
   - Make dataverse_service optional
   - Handle 503 errors gracefully
   - Allow operation without Dataverse

3. **Complete UI Testing:**
   - Test all pages with darbot browser
   - Verify error handling
   - Check responsive design

## 💡 Pro Tips

### Running in Background
```powershell
# Backend in minimized window
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd G:\Github\DAYOUR\Vision-Design; .\vision-design2.0\start-backend.ps1" -WindowStyle Minimized

# Frontend in minimized window
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd G:\Github\DAYOUR\Vision-Design\frontend; npm run dev" -WindowStyle Minimized
```

### Quick Health Check
```powershell
# Create a health check alias
function Check-VisionDesign {
    Write-Host "`n📊 Vision Design Status:" -ForegroundColor Cyan
    try {
        $backend = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 2
        Write-Host "✅ Backend: $($backend.status)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Backend: Not responding" -ForegroundColor Red
    }
    
    $frontend = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
    if ($frontend) {
        Write-Host "✅ Frontend: Running" -ForegroundColor Green
    } else {
        Write-Host "❌ Frontend: Not running" -ForegroundColor Red
    }
}
```

## 📚 Additional Resources

- **API Documentation:** http://localhost:8000/docs
- **Frontend Dev Server:** http://localhost:3000
- **Backend Health:** http://localhost:8000/api/v1/health
- **Test Endpoint:** http://localhost:8000/api/v1/images/test

---

**Last Updated:** October 1, 2025  
**Status:** All scripts tested and working ✅
