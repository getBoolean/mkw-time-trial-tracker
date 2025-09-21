param(
    [Parameter(Mandatory = $true)]
    [string]$LapTime,
    
    [Parameter(Mandatory = $true)]
    [int]$LapNumber,
    
    [Parameter(Mandatory = $true)]
    [bool]$IsFinalLap,
    
    [Parameter(Mandatory = $true)]
    [int]$RunNumber,
    
    [Parameter(Mandatory = $false)]
    [string]$BasePath = "G:\OBS\Mario Kart World\time trials"
)

# Function to ensure ImportExcel module is installed
function ImportExcelModule {
    try {
        # Check if ImportExcel module is available
        if (-not (Get-Module -ListAvailable -Name ImportExcel)) {
            Write-Host "ImportExcel module not found. Installing..." -ForegroundColor Yellow
            
            # Try to install the module
            try {
                Install-Module -Name ImportExcel -Force -Scope CurrentUser -AllowClobber
                Write-Host "ImportExcel module installed successfully!" -ForegroundColor Green
            }
            catch {
                Write-Error "Failed to install ImportExcel module: $($_.Exception.Message)"
                Write-Host "Please run PowerShell as Administrator and try again, or install manually with:" -ForegroundColor Red
                Write-Host "Install-Module -Name ImportExcel -Force -Scope CurrentUser" -ForegroundColor Red
                exit 1
            }
        }
        else {
            Write-Host "ImportExcel module is available" -ForegroundColor Green
        }
        
        # Import the module
        Import-Module ImportExcel -Force
    }
    catch {
        Write-Error "Error checking/installing ImportExcel module: $($_.Exception.Message)"
        exit 1
    }
}

# Function to validate lap time format (0:00.000)
function Test-LapTimeFormat {
    param([string]$TimeString)
    
    # Regex pattern for format 0:00.000
    $pattern = '^\d+:\d{2}\.\d{3}$'
    return $TimeString -match $pattern
}

# Function to convert lap time to seconds for calculations
function Convert-LapTimeToSeconds {
    param([string]$TimeString)
    
    $parts = $TimeString -split ':'
    $minutes = [int]$parts[0]
    $seconds = [double]$parts[1]
    
    return ($minutes * 60) + $seconds
}

# Function to create or update Excel file
function Save-LapTimeToExcel {
    param(
        [string]$LapTime,
        [int]$LapNumber,
        [bool]$IsFinalLap,
        [int]$RunNumber,
        [string]$BasePath
    )
    
    $excelFile = Join-Path $BasePath "lap_times.xlsx"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # Create data object
    $lapData = [PSCustomObject]@{
        Timestamp      = $timestamp
        RunNumber      = $RunNumber
        LapNumber      = $LapNumber
        Time           = $LapTime
        LapTimeSeconds = Convert-LapTimeToSeconds -TimeString $LapTime
        IsFinalLap     = $IsFinalLap
    }
    
    try {
        # Check if Excel file exists
        if (Test-Path $excelFile) {
            # Import existing data
            $existingData = Import-Excel -Path $excelFile
            # Convert to array and add new data
            $allData = @($existingData) + @($lapData)
        }
        else {
            $allData = @($lapData)
        }
        
        # Export to Excel
        $allData | Export-Excel -Path $excelFile -AutoSize -TableStyle Medium2 -WorksheetName "Lap Times"
        
        Write-Host "Lap time saved successfully!" -ForegroundColor Green
        Write-Host "Run Number: $RunNumber" -ForegroundColor Cyan
        Write-Host "Lap Number: $LapNumber" -ForegroundColor Cyan
        Write-Host "Lap Time: $LapTime" -ForegroundColor Cyan
        Write-Host "Final Lap: $IsFinalLap" -ForegroundColor Cyan
        Write-Host "Saved to: $excelFile" -ForegroundColor Yellow
        
    }
    catch {
        Write-Error "Failed to save lap time: $($_.Exception.Message)"
        exit 1
    }
}

# Main execution
try {
    # Ensure ImportExcel module is available
    ImportExcelModule
    
    # Validate lap time format
    if (-not (Test-LapTimeFormat -TimeString $LapTime)) {
        Write-Error "Invalid lap time format. Expected format: 0:00.000 (e.g., 1:23.456)"
        exit 1
    }
    
    # Validate lap number
    if ($LapNumber -lt 1) {
        Write-Error "Lap number must be greater than 0"
        exit 1
    }
    
    # Validate run number
    if ($RunNumber -lt 1) {
        Write-Error "Run number must be greater than 0"
        exit 1
    }
    
    # Save to Excel
    Save-LapTimeToExcel -LapTime $LapTime -LapNumber $LapNumber -IsFinalLap $IsFinalLap -RunNumber $RunNumber -BasePath $BasePath
    
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    exit 1
}

# Usage examples:
# .\save_lap_time.ps1 -LapTime "1:23.456" -LapNumber 1 -IsFinalLap $false -RunNumber 1
# .\save_lap_time.ps1 -LapTime "1:20.123" -LapNumber 2 -IsFinalLap $true -RunNumber 1
# .\save_lap_time.ps1 -LapTime "1:18.789" -LapNumber 1 -IsFinalLap $false -RunNumber 2
# .\save_lap_time.ps1 -LapTime "1:15.234" -LapNumber 1 -IsFinalLap $false -RunNumber 1 -BasePath "C:\MyTimeTrials"
