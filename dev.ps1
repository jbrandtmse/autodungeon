# autodungeon dev startup script (PowerShell)
# Starts both the FastAPI backend and SvelteKit frontend dev servers.
# Usage: .\dev.ps1

$ErrorActionPreference = "Stop"

# ── Prerequisite checks ──────────────────────────────────────────

# Check Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "ERROR: Python is not installed. Please install Python 3.10+ and try again." -ForegroundColor Red
    exit 1
}

$pyVersion = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pyMajor = [int](& $pythonCmd -c "import sys; print(sys.version_info.major)")
$pyMinor = [int](& $pythonCmd -c "import sys; print(sys.version_info.minor)")
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 10)) {
    Write-Host "ERROR: Python 3.10+ is required (found $pyVersion)." -ForegroundColor Red
    exit 1
}

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js is not installed. Please install Node.js 18+ and try again." -ForegroundColor Red
    exit 1
}

$nodeMajor = [int](node -e "console.log(process.versions.node.split('.')[0])")
if ($nodeMajor -lt 18) {
    $nodeVersion = node --version
    Write-Host "ERROR: Node.js 18+ is required (found $nodeVersion)." -ForegroundColor Red
    exit 1
}

# Check npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npm is not installed. Please install npm and try again." -ForegroundColor Red
    exit 1
}

# ── Determine uvicorn command ─────────────────────────────────────

$uvicornDirect = Get-Command uvicorn -ErrorAction SilentlyContinue
$uvicornArgs = @("api.main:app", "--reload", "--port", "8000")

# ── Start servers ─────────────────────────────────────────────────

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if ($uvicornDirect) {
    $backend = Start-Process -NoNewWindow -PassThru uvicorn -ArgumentList ($uvicornArgs -join " ")
} else {
    $backend = Start-Process -NoNewWindow -PassThru $pythonCmd -ArgumentList ("-m uvicorn " + ($uvicornArgs -join " "))
}

$frontend = Start-Process -NoNewWindow -PassThru -WorkingDirectory "./frontend" npm -ArgumentList "run dev"

# ── Startup banner ────────────────────────────────────────────────

Write-Host ""
Write-Host "  autodungeon dev servers starting..."
Write-Host ""
Write-Host "    Backend  (FastAPI):    http://localhost:8000"
Write-Host "    Frontend (SvelteKit):  http://localhost:5173"
Write-Host "    API docs:              http://localhost:8000/docs"
Write-Host ""
Write-Host "    Legacy (Streamlit):    Run 'streamlit run app.py' separately"
Write-Host ""
Write-Host "  Press Ctrl+C to stop both servers."
Write-Host ""

# ── Cleanup on exit ───────────────────────────────────────────────

$cleanup = {
    Write-Host ""
    Write-Host "  Stopping dev servers..."
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontend -and -not $frontend.HasExited) {
        Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  Done."
}

try {
    # Register cleanup for Ctrl+C
    [Console]::TreatControlCAsInput = $false
    $null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanup

    # Wait for either process to exit
    while ($true) {
        if ($backend.HasExited -and $frontend.HasExited) {
            break
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    & $cleanup
}
