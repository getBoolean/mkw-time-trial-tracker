# mk-time-trial-tracker

A comprehensive OBS Studio script for the Advanced Scene Switcher plugin that provides automatic track name correction and lap time recording for Mario Kart Wii time trials.

## Quick setup

1. Install Advanced Scene Switcher:
   - Download from the plugin's GitHub and install, then restart OBS.
2. Add this script to OBS:
   - OBS → **Tools** → **Scripts** → **+** → select `TimeTrialTracker.py`.
3. Import the provided macro:
   - OBS → **Tools** → **Advanced Scene Switcher** → Macros (⋯) → **Import** → choose `macros-export.json`.
4. After import, adjust names/paths if needed (capture source name, project paths, save locations).
5. In Advanced Scene Switcher, open the imported `current-track` macro and ensure the `MKW Track` action's setting **OCR Text Variable Name** matches your OCR variable (default: `Current Track OCR`).

## Features

- **Track Autocorrect**: Automatically identifies and corrects track names from OCR text
- **Lap Time Recording**: Save lap times to CSV with automatic calculations
- **Fuzzy Matching**: Uses intelligent matching to handle OCR errors and variations
- **Cross-Platform**: Pure Python implementation works on Windows, macOS, and Linux
- **Queue System**: Automatic queuing when CSV files are locked, with manual processing option
- **Advanced Scene Switcher Integration**: Works seamlessly with OBS macros and scene switching
- **Variable-Based Inputs**: Use OCR variables, counters, or any Advanced Scene Switcher variable as input

## Prerequisites

Before setting up this script, ensure you have:

1. **OBS Studio** (latest version recommended)
2. **Advanced Scene Switcher Plugin** - Download from [GitHub](https://github.com/WarmUpTill/SceneSwitcher)

## Installation

### Step 1: Install Advanced Scene Switcher

1. Download the Advanced Scene Switcher plugin from the [official repository](https://github.com/WarmUpTill/SceneSwitcher)
2. Install the plugin following the instructions in the repository
3. Restart OBS Studio after installation

### Step 2: Add the Script

1. Open OBS Studio
2. Go to **Tools** → **Scripts**
3. Click the **+** button to add a new script
4. Navigate to and select `TimeTrialTracker.py`
5. Click **OK** to load the script
6. Configure the script properties:
   - **Base Path**: Directory where CSV files will be saved (default: `G:\OBS\Mario Kart World\time trials`)
   - **Script Repo Path**: Path to this repository (optional, for future features)

## Usage

### Available Actions

The script provides three main Advanced Scene Switcher actions:

#### 1. MKW Track Action

Automatically identifies track names from OCR text.

- **OCR Text Variable Name**: Variable containing the OCR text to process
- **Output**: Sets `identified_track` and `identified_track_safe` temporary variables

#### 2. MKW Save Lap Action  

Records lap times to CSV with automatic calculations.

**Variable Inputs:**

- **Lap Time Variable Name**: Variable containing lap time (format: `m:ss.mmm`)
- **Lap Number Variable Name**: Variable containing current lap number
- **Run Number Variable Name**: Variable containing current run number  
- **Track Variable Name**: Variable containing track name
- **Coins Variable Name**: Variable containing total coins collected
- **Shrooms Variable Name**: Variable containing total mushrooms used

**Direct Input:**

- **Is Final Lap**: Checkbox to indicate if this is the final lap of the run

#### 3. MKW Move Old Images Action

Moves image files matching a pattern to a destination subfolder for organization.

**Direct Inputs:**

- **File Pattern**: Pattern to match files (default: `Lap-*.png`)
- **Destination Subfolder**: Subfolder name to move files to (default: `lap times`)

### Quick start: import provided macros (recommended)

You can import a ready-made macro setup as a starting point:

1. In OBS, go to **Tools** → **Advanced Scene Switcher** → Macros.
2. Open the Macros menu (⋯) → **Import** and select `macros-export.json` from this repo.
3. After import, adjust these items in all macros to match your setup:
   - **Capture source name**: Replace `AverMedia Live Gamer 4K 2.1` with your video capture source.
   - **File paths**: Update any `C:\dev\mk-time-trial-tracker\...` paths if your repo is saved elsewhere.
   - **Screenshot save paths**: Change `G:\OBS\Mario Kart World\...` to your desired location.
   - **OCR regions/colors**: The macros include example OCR areas and colors tuned to a 4K capture; tweak the areas and thresholds for your resolution/theme if needed.
   - **Script action**: Ensure the actions `MKW Track`, `MKW Save Lap`, and `MKW Move Old Images` are present and configured correctly.

### Data Output

#### CSV File Structure

Lap times are saved to `lap_times.csv` in your configured base path with these columns:

- **Timestamp**: When the lap was recorded
- **RunNumber**: Time trial run number  
- **LapNumber**: Lap number within the run
- **Time**: Lap time (individual lap time for final laps, cumulative for others)
- **LapTimeSeconds**: Time converted to seconds for calculations
- **IsFinalLap**: Whether this was the final lap of the run
- **Track**: Track name
- **Coins**: Coins collected this lap (calculated as difference from previous laps)
- **Shrooms**: Mushrooms used this lap (calculated as difference from previous laps)

#### Using Variables

The script exposes macro properties (temporary variables) that can be used in other actions:

- `identified_track`: Canonical track name from OCR
- `identified_track_safe`: Filesystem-safe version of track name

To use these elsewhere:

1. Add a **Variable** action after the `MKW Track` script action
2. Set **Variable name** to e.g. `Current Track`  
3. Set the value from **Temp variable** → select `identified_track`

You can then reference variables in macros using `${Variable Name}`. Examples:

- File path: `C:\OBS\Mario Kart World\${Current Track}\`
- Text: `Current Track: ${Current Track}`

## Advanced Configuration

### Custom Track Names

If you need to add custom track names or aliases, you can modify the `alias_to_canonical` dictionary in the script:

```python
alias_to_canonical = {
    "your custom name": "Canonical Track Name",
    # ... existing aliases
}
```

### Queue System

The lap time recording system includes automatic queuing:

- **When CSV is locked**: Lap times are automatically queued to `lap_times_queue.json`
- **Manual processing**: Use the "Process Queue Now" button in script properties
- **Auto-processing**: The script attempts to flush the queue before each new save

This ensures no lap times are lost even if the CSV file is open in Excel or another program.

## Contributing

If you find issues or want to add support for additional tracks/OCR variations, feel free to submit a pull request or open an issue.

## Troubleshooting

### Common Issues

1. **Variables not found**: Ensure your OCR and counter variables are properly set up in Advanced Scene Switcher
2. **CSV file locked**: Use the "Process Queue Now" button to manually process queued lap times
3. **Track not recognized**: Check the OCR text output and consider adding custom aliases to the script
4. **Path issues**: Verify the base path is correctly set in the script properties

### Debug Information

The script logs detailed information to the OBS Script Log:

- Track identification results
- Variable resolution status  
- CSV write operations
- Queue processing activities

Access logs via **Tools** → **Scripts** → **Script Log** in OBS.
