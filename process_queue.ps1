# Process Queue Script for Mario Kart Time Trial Tracker
# This script processes any queued lap times that couldn't be saved due to Excel file being locked

param(
    [Parameter(Mandatory = $false)]
    [string]$BasePath = "G:\OBS\Mario Kart World\time trials"
)

Write-Host "Mario Kart Time Trial Tracker - Queue Processor" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Check if the main script exists
$scriptPath = Join-Path $PSScriptRoot "save_lap_time.ps1"
if (-not (Test-Path $scriptPath)) {
    Write-Error "save_lap_time.ps1 not found in the same directory as this script."
    exit 1
}

# Run the main script with ProcessQueueOnly parameter
try {
    Write-Host "Processing queued lap times..." -ForegroundColor Yellow
    & $scriptPath -ProcessQueueOnly -BasePath $BasePath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Queue processing completed successfully!" -ForegroundColor Green
    }
    else {
        Write-Host "Queue processing completed with warnings or errors." -ForegroundColor Yellow
    }
}
catch {
    Write-Error "Failed to process queue: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "Queue processing finished." -ForegroundColor Cyan
