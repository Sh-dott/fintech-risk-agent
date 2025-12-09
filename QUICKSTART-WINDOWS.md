# Quick Start Guide for Windows PowerShell

## Method 1: Using the PowerShell Script (Easiest)

1. **Open PowerShell as Administrator** (right-click PowerShell, select "Run as Administrator")

2. **Allow script execution** (only needed once):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Navigate to project directory**:
   ```powershell
   cd C:\Users\Shai\web-projects\fintech-risk-agent
   ```

4. **Run the startup script**:
   ```powershell
   .\start.ps1
   ```

This will open two new windows - one for backend and one for frontend.

## Method 2: Manual Commands

### Terminal 1 - Backend

```powershell
# Navigate to project root
cd C:\Users\Shai\web-projects\fintech-risk-agent

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start backend server
py -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 - Frontend

```powershell
# Navigate to frontend directory
cd C:\Users\Shai\web-projects\fintech-risk-agent\frontend

# Start frontend dev server
npm run dev
```

## Common Issues

### "Activate.ps1 cannot be loaded" Error

This means PowerShell execution policy is restricted. Run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "python is not recognized" Error

Use `py` instead of `python`:
```powershell
py -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Wrong Directory Error

Make sure you're in the project root directory (not backend folder):
```powershell
cd C:\Users\Shai\web-projects\fintech-risk-agent
```

The virtual environment (`.venv`) is in the project root, not in the backend folder.

## Method 3: Using Command Prompt (cmd.exe)

If you prefer Command Prompt instead of PowerShell:

### Terminal 1 - Backend
```cmd
cd C:\Users\Shai\web-projects\fintech-risk-agent
.venv\Scripts\activate.bat
py -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 - Frontend
```cmd
cd C:\Users\Shai\web-projects\fintech-risk-agent\frontend
npm run dev
```

Or simply double-click `start.bat`

## Access the Application

Once both servers are running:
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api-docs

## Stopping the Servers

- Press `Ctrl+C` in each terminal window
- Or close the terminal windows
