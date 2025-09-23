param(
    [Parameter(Mandatory = $false)]
    [string]$LapTime,
    
    [Parameter(Mandatory = $false)]
    [int]$LapNumber,
    
    [Parameter(Mandatory = $false)]
    [bool]$IsFinalLap,
    
    [Parameter(Mandatory = $false)]
    [int]$RunNumber,
    
    [Parameter(Mandatory = $false)]
    [string]$Track,
    
    [Parameter(Mandatory = $false)]
    [string]$Coins = "0",
    
    [Parameter(Mandatory = $false)]
    [int]$Shrooms = 0,
    
    [Parameter(Mandatory = $false)]
    [string]$BasePath = "G:\OBS\Mario Kart World\time trials",
    
    [Parameter(Mandatory = $false)]
    [switch]$ProcessQueueOnly,
    
    [Parameter(Mandatory = $false)]
    [switch]$LogToFile,
    
    [Parameter(Mandatory = $false)]
    [string]$LogPath
)

# Queue/lock helpers
function Get-ExcelFilePath {
    param([string]$BasePath)
    return (Join-Path $BasePath "lap_times.xlsx")
}

function Get-QueueFilePath {
    param([string]$BasePath)
    return (Join-Path $BasePath "lap_times_queue.json")
}

function Test-ExcelLocked {
    param([string]$ExcelPath)
    try {
        if (-not (Test-Path $ExcelPath)) {
            return $false
        }
        $fs = [System.IO.File]::Open($ExcelPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        $fs.Close()
        return $false
    }
    catch {
        return $true
    }
}

function Read-QueueItems {
    param([string]$BasePath)
    $queuePath = Get-QueueFilePath -BasePath $BasePath
    if (-not (Test-Path $queuePath)) { return @() }
    try {
        $raw = Get-Content -Path $queuePath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
        $items = $raw | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $items) { return @() }
        # Always normalize to an array, even for a single PSCustomObject
        return @($items)
    }
    catch {
        Write-Warning "Queue file is corrupt. Backing up and clearing: $($_.Exception.Message)"
        try { Copy-Item -Path $queuePath -Destination ($queuePath + ".bak_" + (Get-Date -Format "yyyyMMddHHmmss")) -Force } catch {}
        try { Remove-Item -Path $queuePath -Force } catch {}
        return @()
    }
}

function Write-QueueItems {
    param([string]$BasePath, [array]$Items)
    $queuePath = Get-QueueFilePath -BasePath $BasePath
    $Items | ConvertTo-Json -Depth 5 | Set-Content -Path $queuePath -Encoding UTF8
}

function Add-QueuedSubmission {
    param(
        [string]$LapTime,
        [int]$LapNumber,
        [bool]$IsFinalLap,
        [int]$RunNumber,
        [string]$Track,
        [int]$Coins,
        [int]$Shrooms,
        [string]$BasePath
    )
    $items = Read-QueueItems -BasePath $BasePath
    $submission = [PSCustomObject]@{
        Timestamp  = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        # Ensure no stray newline/whitespace is kept in queued LapTime
        LapTime    = if ($null -ne $LapTime) { $LapTime.Trim() } else { $LapTime }
        LapNumber  = $LapNumber
        IsFinalLap = $IsFinalLap
        RunNumber  = $RunNumber
        Track      = $Track
        Coins      = $Coins
        Shrooms    = $Shrooms
    }
    $items = @($items) + @($submission)
    Write-QueueItems -BasePath $BasePath -Items $items
}

function Invoke-QueuedSubmissions {
    param([string]$BasePath)
    $excelFile = Get-ExcelFilePath -BasePath $BasePath
    Write-Host "Checking Excel lock status for queue processing..." -ForegroundColor Cyan
    if (Test-ExcelLocked -ExcelPath $excelFile) { 
        Write-Host "Excel file is locked, skipping queue processing" -ForegroundColor Red
        return 
    }
    Write-Host "Excel file is available for queue processing" -ForegroundColor Green
    $items = Read-QueueItems -BasePath $BasePath
    # Normalize again here for double safety
    $items = @($items)
    $queuedCount = $items.Count
    if ($queuedCount -eq 0) { 
        Write-Host "No queued items found" -ForegroundColor Yellow
        return 
    }
    Write-Host "Flushing queued lap submissions: $queuedCount" -ForegroundColor Yellow
    $failed = @()
    for ($i = 0; $i -lt $queuedCount; $i++) {
        $it = $items[$i]
        try {
            $queuedCoins = if ($it.PSObject.Properties.Name -contains 'Coins' -and $null -ne $it.Coins) { [int]$it.Coins } else { 0 }
            $queuedShrooms = if ($it.PSObject.Properties.Name -contains 'Shrooms' -and $null -ne $it.Shrooms) { [int]$it.Shrooms } else { 0 }
            # Sanitize LapTime coming from queue (could include a trailing \n)
            $queuedLapTime = ("$($it.LapTime)").Trim()
            Write-Host "Processing queued item: Run $($it.RunNumber), Lap $($it.LapNumber), Time $queuedLapTime" -ForegroundColor Magenta
            Save-LapTimeToExcel -LapTime $queuedLapTime -LapNumber $it.LapNumber -IsFinalLap $it.IsFinalLap -RunNumber $it.RunNumber -Track $it.Track -Coins $queuedCoins -Shrooms $queuedShrooms -BasePath $BasePath
            Write-Host "Successfully processed queued item: Run $($it.RunNumber)" -ForegroundColor Green
        }
        catch {
            Write-Warning "Failed to flush a queued item: $($_.Exception.Message)"
            Write-Warning "Error details: $($_.Exception)"
            $failed = $items[$i..($items.Count - 1)]
            break
        }
        if (Test-ExcelLocked -ExcelPath $excelFile) {
            if ($i -lt ($items.Count - 1)) {
                $failed = $items[($i + 1)..($items.Count - 1)]
            }
            break
        }
    }
    if ($failed.Count -gt 0) {
        Write-QueueItems -BasePath $BasePath -Items $failed
        Write-Warning "Some queued items could not be flushed and were kept for next run. Remaining: $($failed.Count)"
    }
    else {
        $queuePath = Get-QueueFilePath -BasePath $BasePath
        if (Test-Path $queuePath) { Remove-Item -Path $queuePath -Force }
        Write-Host "All queued items flushed." -ForegroundColor Green
    }
}

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
    
    # Normalize any stray whitespace or newlines from OCR/queue
    if ($null -ne $TimeString) { $TimeString = $TimeString.Trim() }
    $parts = $TimeString -split ':'
    $minutes = [int]$parts[0]
    $seconds = [double]$parts[1]
    
    return ($minutes * 60) + $seconds
}


# Function to convert seconds back to lap time format
function Convert-SecondsToLapTime {
    param([double]$Seconds)
    
    $minutes = [math]::Floor($Seconds / 60)
    $remainingSeconds = $Seconds % 60
    
    return "{0}:{1:F3}" -f $minutes, $remainingSeconds
}

# Function to create or update Excel file
function Save-LapTimeToExcel {
    param(
        [string]$LapTime,
        [int]$LapNumber,
        [bool]$IsFinalLap,
        [int]$RunNumber,
        [string]$Track,
        [int]$Coins,
        [int]$Shrooms,
        [string]$BasePath
    )
    
    $excelFile = Get-ExcelFilePath -BasePath $BasePath
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # Calculate last lap time if this is a final lap
    $lastLapTime = ""
    $lastLapTimeSeconds = ""
    
    if ($IsFinalLap) {
        # Get all previous laps for this run
        $existingData = @()
        if (Test-Path $excelFile) {
            $existingData = Import-Excel -Path $excelFile
        }
        
        $previousLaps = $existingData | Where-Object { $_.RunNumber -eq $RunNumber -and $_.IsFinalLap -eq $false }
        $currentLapSeconds = Convert-LapTimeToSeconds -TimeString $LapTime
        $previousLapsSum = ($previousLaps | Measure-Object -Property LapTimeSeconds -Sum).Sum
        
        if ($previousLapsSum -gt 0) {
            $lastLapTimeSeconds = $currentLapSeconds - $previousLapsSum
            $lastLapTime = Convert-SecondsToLapTime -Seconds $lastLapTimeSeconds
        }
    }
    
    # Calculate per-lap Coins/Shrooms by subtracting previous laps in same run
    $coinsToSave = $Coins
    $shroomsToSave = $Shrooms
    try {
        if (Test-Path $excelFile) {
            $existingForRun = (Import-Excel -Path $excelFile) | Where-Object { $_.RunNumber -eq $RunNumber }
            if ($existingForRun) {
                $prevCoins = ($existingForRun | ForEach-Object { if ($null -ne $_.Coins) { [int]$_.Coins } else { 0 } } | Measure-Object -Sum).Sum
                $prevShrooms = ($existingForRun | ForEach-Object { if ($null -ne $_.Shrooms) { [int]$_.Shrooms } else { 0 } } | Measure-Object -Sum).Sum
                if ($null -ne $prevCoins) { $coinsToSave = $Coins - [int]$prevCoins }
                if ($null -ne $prevShrooms) { $shroomsToSave = [int]$Shrooms - [int]$prevShrooms }
            }
        }
    }
    catch {
        # If reading existing fails, fall back to provided values
    }

    # Create data object
    $lapData = [PSCustomObject]@{
        Timestamp      = $timestamp
        RunNumber      = $RunNumber
        LapNumber      = $LapNumber
        Time           = if ($IsFinalLap -and $lastLapTime -ne "") { $lastLapTime } else { $LapTime }
        LapTimeSeconds = if ($IsFinalLap -and $lastLapTimeSeconds -ne "") { $lastLapTimeSeconds } else { Convert-LapTimeToSeconds -TimeString $LapTime }
        IsFinalLap     = $IsFinalLap
        Track          = $Track
        Coins          = $coinsToSave
        Shrooms        = $shroomsToSave
    }
    
    try {
        # Check if Excel file exists
        if (Test-Path $excelFile) {
            # Import existing data
            $existingData = Import-Excel -Path $excelFile
            
            # Ensure all existing data has the new columns
            foreach ($item in $existingData) {
                if (-not $item.PSObject.Properties.Name -contains "LastLapTime") {
                    $item | Add-Member -NotePropertyName "LastLapTime" -NotePropertyValue "" -Force
                }
                if (-not $item.PSObject.Properties.Name -contains "LastLapTimeSeconds") {
                    $item | Add-Member -NotePropertyName "LastLapTimeSeconds" -NotePropertyValue "" -Force
                }
                if (-not $item.PSObject.Properties.Name -contains "Track") {
                    $item | Add-Member -NotePropertyName "Track" -NotePropertyValue "" -Force
                }
                if (-not $item.PSObject.Properties.Name -contains "Coins") {
                    $item | Add-Member -NotePropertyName "Coins" -NotePropertyValue $null -Force
                }
                if (-not $item.PSObject.Properties.Name -contains "Shrooms") {
                    $item | Add-Member -NotePropertyName "Shrooms" -NotePropertyValue $null -Force
                }
            }
            
            # Convert to array and add new data
            $allData = @($existingData) + @($lapData)
        }
        else {
            $allData = @($lapData)
        }
        
        # Export to Excel with manual formatting to avoid table issues
        $allData | Export-Excel -Path $excelFile -AutoSize -WorksheetName "Lap Times" -BoldTopRow -FreezeTopRow
        
        Write-Host "Lap time saved successfully!" -ForegroundColor Green
        Write-Host "Run Number: $RunNumber" -ForegroundColor Cyan
        Write-Host "Lap Number: $LapNumber" -ForegroundColor Cyan
        Write-Host "Lap Time: $LapTime" -ForegroundColor Cyan
        Write-Host "Final Lap: $IsFinalLap" -ForegroundColor Cyan
        Write-Host "Track: $Track" -ForegroundColor Cyan
        Write-Host "Saved to: $excelFile" -ForegroundColor Yellow
        
    }
    catch {
        Write-Error "Failed to save lap time: $($_.Exception.Message)"
        throw $_.Exception
    }
}

# Main execution
try {
    # Configure logging to file if requested
    $transcriptStarted = $false
    if ($LogToFile) {
        try {
            if ([string]::IsNullOrWhiteSpace($LogPath)) {
                $logDir = Join-Path $BasePath "logs"
                if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
                $LogPath = Join-Path $logDir ("save_lap_time_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")
            }
            else {
                $logParent = Split-Path -Path $LogPath -Parent
                if ($logParent -and -not (Test-Path $logParent)) { New-Item -ItemType Directory -Path $logParent -Force | Out-Null }
            }
            Start-Transcript -Path $LogPath -Append | Out-Null
            $transcriptStarted = $true
            Write-Host "Logging to: $LogPath" -ForegroundColor Yellow
        }
        catch { Write-Warning "Failed to start transcript logging: $($_.Exception.Message)" }
    }
    # Ensure ImportExcel module is available
    ImportExcelModule
    
    # If ProcessQueueOnly is specified, just process the queue and exit
    if ($ProcessQueueOnly) {
        Write-Host "Processing queued submissions only..." -ForegroundColor Yellow
        Invoke-QueuedSubmissions -BasePath $BasePath
        if ($transcriptStarted) { try { Stop-Transcript | Out-Null } catch {} }
        exit 0
    }
    
    # Validate required parameters when not processing queue only
    if ([string]::IsNullOrWhiteSpace($LapTime)) {
        Write-Error "LapTime parameter is required when not using ProcessQueueOnly"
        exit 1
    }
    if (-not $LapNumber) {
        Write-Error "LapNumber parameter is required when not using ProcessQueueOnly"
        exit 1
    }
    if (-not $PSBoundParameters.ContainsKey('IsFinalLap')) {
        Write-Error "IsFinalLap parameter is required when not using ProcessQueueOnly"
        exit 1
    }
    if (-not $RunNumber) {
        Write-Error "RunNumber parameter is required when not using ProcessQueueOnly"
        exit 1
    }
    if ([string]::IsNullOrWhiteSpace($Track)) {
        Write-Error "Track parameter is required when not using ProcessQueueOnly"
        exit 1
    }
    
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
    
    # Validate track name
    if ([string]::IsNullOrWhiteSpace($Track)) {
        Write-Error "Track name must be provided"
        exit 1
    }
    
    # Validate Coins and Shrooms
    $coinsInt = 0
    try {
        $coinsInt = [int]$Coins.Trim()
    }
    catch {
        Write-Error "Coins must be a valid integer"
        exit 1
    }
    
    if ($coinsInt -lt 0 -or $coinsInt -gt 20) {
        Write-Error "Coins must be between 0 and 20"
        exit 1
    }
    if ($PSBoundParameters.ContainsKey('Shrooms')) {
        if ($Shrooms -lt 0 -or $Shrooms -gt 3) {
            Write-Error "Shrooms must be between 0 and 3"
            exit 1
        }
    }
    
    # Handle Excel lock and queue behavior
    $excelFile = Get-ExcelFilePath -BasePath $BasePath
    if (Test-ExcelLocked -ExcelPath $excelFile) {
        Write-Warning "Excel file is currently open/locked. Queuing this lap submission for later."
        Add-QueuedSubmission -LapTime $LapTime -LapNumber $LapNumber -IsFinalLap $IsFinalLap -RunNumber $RunNumber -Track $Track -Coins $coinsInt -Shrooms $Shrooms -BasePath $BasePath
        Write-Host "Queued submission. It will be added next time the program runs when the file is available." -ForegroundColor Yellow
        Write-Host "Note: Existing queued items will be processed when Excel becomes available." -ForegroundColor Cyan
        if ($transcriptStarted) { try { Stop-Transcript | Out-Null } catch {} }
        exit 0
    }

    # Flush any queued items first
    Invoke-QueuedSubmissions -BasePath $BasePath

    # Save current submission to Excel
    Save-LapTimeToExcel -LapTime $LapTime -LapNumber $LapNumber -IsFinalLap $IsFinalLap -RunNumber $RunNumber -Track $Track -Coins $coinsInt -Shrooms $Shrooms -BasePath $BasePath
    
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    exit 1
}
finally {
    if ($transcriptStarted) { try { Stop-Transcript | Out-Null } catch {} }
}

# Usage examples:
# .\save_lap_time.ps1 -LapTime "1:23.456" -LapNumber 1 -IsFinalLap $false -RunNumber 1 -Track "Mario Circuit" -Coins 2 -Shrooms 0
# .\save_lap_time.ps1 -LapTime "1:20.123" -LapNumber 2 -IsFinalLap $true -RunNumber 1 -Track "Mario Circuit" -Coins 5 -Shrooms 1
# .\save_lap_time.ps1 -LapTime "1:18.789" -LapNumber 1 -IsFinalLap $false -RunNumber 2 -Track "Rainbow Road" -Coins 0 -Shrooms 0
# .\save_lap_time.ps1 -LapTime "1:15.234" -LapNumber 1 -IsFinalLap $false -RunNumber 1 -Track "Mario Circuit" -BasePath "C:\MyTimeTrials" -Coins 3 -Shrooms 2
# .\save_lap_time.ps1 -ProcessQueueOnly -BasePath "G:\OBS\Mario Kart World\time trials"  # Process queued items only
