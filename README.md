# mk-time-trial-tracker

A comprehensive OBS Studio script for the Advanced Scene Switcher plugin that provides automatic track name correction and lap time recording for Mario Kart Wii time trials.

## Quick setup

1. Install Advanced Scene Switcher:
   - Download from the plugin's GitHub and install, then restart OBS.
2. Add this script to OBS:
   - OBS → **Tools** → **Scripts** → **+** → select `TimeTrialTracker.py`.
3. Import the provided macro:
   - OBS → **Tools** → **Advanced Scene Switcher** → Macros (⋯) → **Import** → choose `macros-export.json`.
   - **Download**: [macros-export.json](./macros-export.json)
4. After import, adjust names/paths if needed (capture source name, project paths, save locations).
5. In Advanced Scene Switcher, open the imported `current-track` macro and ensure the `MKW Track` action's setting **OCR Text Variable Name** matches your OCR variable (default: `Current Track OCR`).

> **For detailed setup instructions with visual guides, see the [Macro Setup Guide](#macro-setup-guide) section below.**

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
   - **Download**: [macros-export.json](./macros-export.json)
3. After import, adjust these items in all macros to match your setup:
   - **Capture source name**: Replace `AverMedia Live Gamer 4K 2.1` with your video capture source.
   - **File paths**: Update any `C:\dev\mk-time-trial-tracker\...` paths if your repo is saved elsewhere.
   - **Screenshot save paths**: Change `G:\OBS\Mario Kart World\...` to your desired location.
   - **OCR regions/colors**: The macros include example OCR areas and colors tuned to a 4K capture; tweak the areas and thresholds for your resolution/theme if needed.
   - **Script action**: Ensure the actions `MKW Track`, `MKW Save Lap`, and `MKW Move Old Images` are present and configured correctly.

## Macro Setup Guide

This section provides detailed setup instructions for each macro included in the system. The macros work together to automatically detect game state, capture screenshots, track lap times, and organize data.

### Overview of Macro System

The macro system consists of several interconnected macros that handle different aspects of time trial tracking:

1. **Detection Macros**: Monitor game state (racing status, track, time, coins, mushrooms)
2. **Control Macros**: Handle time trial start/end events
3. **Screenshot Macros**: Capture images at key moments (lap end, time trial end)

### 1. Game State Detection Macros

#### Current Track Detection

**Purpose**: Identifies the current track from OCR text and sets track variables.

![Current Track Conditions](docs/current-track-macro-conditions.png)
![Current Track Actions](docs/current-track-macro-actions.png)

**Setup Steps**:

1. Configure OCR conditions to detect track name area
2. Set up the MKW Track script action with proper variable names
3. Ensure output variables are set for other macros to use

**Key Settings**:

- OCR region should cover the track name display area
- OCR Text Variable Name: `Current Track OCR` (default)
- Output variables: `identified_track` and `identified_track_safe`

#### Current Time Detection

The system includes macros to detect the current race time, with different configurations for different time display colors:

**White Time Display**:
![Current Time White](docs/current-time-white-macro.png)

**Yellow Time Display**:
![Current Time Yellow](docs/current-time-yellow-macro.png)

**Setup Steps**:

1. Configure OCR to detect the time display area
2. Set up different macros for different time colors (white/yellow)
3. Adjust OCR thresholds for your game's time display

#### Coins Detection

**Purpose**: Tracks total coins collected during the race.

![Current Coins](docs/current-coins-macro.png)

**Setup Steps**:

1. Set OCR region to cover the coin counter
2. Configure OCR to recognize coin count numbers
3. Store result in `Current Coins` variable

#### Mushroom Usage Detection

The system tracks mushroom usage with separate macros for different counts:

**No Mushrooms (0)**:
![0 Mushrooms](docs/0shroom-macro.png)

**1 Mushroom Used**:
![1 Mushroom](docs/1shroom-macro.png)

**2 Mushrooms Used**:
![2 Mushrooms](docs/2shroom-macro.png)

**3 Mushrooms Used**:
![3 Mushrooms](docs/3shroom-macro.png)

**Setup Steps**:

1. Configure each macro to detect the corresponding mushroom count display
2. Set appropriate OCR regions and thresholds
3. Update mushroom counter variables accordingly

#### Racing Status Detection

**Purpose**: Determines if a race is currently active.

![Racing Status](docs/is-racing-macro.png)

**Setup Steps**:

1. Configure conditions to detect racing UI elements
2. Set up boolean variable to track racing state
3. Use this as a condition for other race-dependent macros

### 2. Control Macros

#### Time Trial Start

**Purpose**: Triggers when a time trial begins, initializing tracking variables.

![TT Start Conditions](docs/tt-start-macro-conditions.png)
![TT Start Actions](docs/tt-start-macro-actions.png)

**Setup Steps**:

1. Configure conditions to detect time trial start (e.g., timer starting)
2. Set up actions to initialize run variables
3. Reset lap counters and other tracking variables

**Key Actions**:

- Initialize run number counter
- Reset lap counter to 1
- Clear previous lap time data
- Set up initial screenshot if needed

### 3. Screenshot Macros

#### Lap End Screenshots

**Purpose**: Captures screenshots at the end of each lap with lap time data.

![Lap End Conditions](docs/screenshot-lap-end-macro-conditions.png)
![Lap End Actions](docs/screenshot-lap-end-macro-actions.png)

**Setup Steps**:

1. Configure conditions to detect lap completion
2. Set up screenshot action with proper file naming
3. Configure MKW Save Lap script action for data recording

**Key Settings**:

- Screenshot path: Include lap number and timestamp in filename
- MKW Save Lap action: Configure all required variable inputs
- File organization: Use MKW Move Old Images if needed

#### Time Trial End Screenshots

**Purpose**: Captures final screenshot when time trial completes.

![TT End Conditions](docs/screenshot-tt-end-macro-conditions.png)
![TT End Actions](docs/screenshot-tt-end-macro-actions.png)

**Setup Steps**:

1. Configure conditions to detect time trial completion
2. Set up final screenshot capture
3. Process final lap data and organize files

**Key Actions**:

- Capture final results screenshot
- Save final lap time with MKW Save Lap action (with "Is Final Lap" checked)
- Move/organize screenshot files using MKW Move Old Images

### Configuration Tips

#### OCR Settings

1. **Resolution**: The provided macros are configured for 4K capture. Adjust OCR regions proportionally for other resolutions.
2. **Color Thresholds**: Adjust color matching thresholds based on your game's theme and capture settings.
3. **Text Recognition**: Fine-tune OCR settings for better accuracy with your specific setup.

#### Variable Management

1. **Consistent Naming**: Ensure variable names match between macros (e.g., `Current Track`, `Current Coins`)
2. **Counter Setup**: Configure counters in Advanced Scene Switcher for run numbers and lap numbers
3. **Temporary Variables**: The script uses temporary variables that don't persist between OBS sessions

#### File Paths

1. **Screenshot Locations**: Organize screenshots by track using variables: `G:\OBS\Mario Kart World\${Current Track}\`
2. **CSV Output**: Configure base path in script properties for CSV file location
3. **Image Organization**: Use MKW Move Old Images action to keep screenshots organized

#### Testing and Calibration

1. **Test Each Macro**: Run through a complete time trial to ensure all macros trigger correctly
2. **Check OCR Accuracy**: Verify that text recognition works reliably with your setup
3. **Validate Data Output**: Confirm that lap times and other data are recorded accurately in CSV files

### Troubleshooting Macro Issues

1. **OCR Not Triggering**: Check OCR region positioning and color thresholds
2. **Variables Not Found**: Verify variable names match exactly between macros and script actions
3. **Screenshots Not Capturing**: Confirm source names and file paths are correct
4. **Data Not Recording**: Check that MKW script actions are properly configured with variable inputs

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
