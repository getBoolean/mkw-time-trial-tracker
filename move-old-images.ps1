function Move-OldImages {
    $sourceFolder = "G:\OBS\Mario Kart World\time trials"
    $oldFolder = Join-Path $sourceFolder "lap times"
    
    # Create old folder if it doesn't exist
    if (-not (Test-Path $oldFolder)) {
        New-Item -ItemType Directory -Path $oldFolder -Force
        Write-Host "Created directory: $oldFolder"
    }
    
    # Get all files in the source folder
    $files = Get-ChildItem -Path $sourceFolder -File
    
    foreach ($file in $files) {
        if ($file.Name -like "Lap-*.png") {
            $sourcePath = $file.FullName
            $destinationPath = Join-Path $oldFolder $file.Name
            
            try {
                Move-Item -Path $sourcePath -Destination $destinationPath -Force
                Write-Host "Moved $($file.Name) to $oldFolder"
            }
            catch {
                Write-Error "Failed to move $($file.Name): $($_.Exception.Message)"
            }
        }
        else {
            Write-Host "Skipping $($file.Name)"
        }
    }
    
    return $true
}

# Call the function
Move-OldImages
