# mkw-time-trial-tracker

A comprehensive OBS Studio script and macros for the Advanced Scene Switcher plugin that provides automatic track detection and lap time recording for Mario Kart World time trials.

![Macro Setup Guide](docs/Splits_Cheep_Cheep_Falls_Run.png)

## Quick setup

1. Install Advanced Scene Switcher:
   - Download from the plugin's GitHub and install, then restart OBS.
2. Download and install Python 3.10 from the [official website](https://www.python.org/downloads/).
3. Configure Advanced Scene Switcher to use Python 3.10
   - OBS → **Tools** → **Scripts** → **Python Settings** → enter the path to the Python 3.10 directory
4. [Download](https://github.com/getBoolean/mk-time-trial-tracker/releases/latest) the bundle, extract, and add this script to OBS:
   - OBS → **Tools** → **Scripts** → **+** → select `TimeTrialTracker.py`.
5. Import the provided macro:
   - OBS → **Tools** → **Advanced Scene Switcher** → Macros (⋯) → **Import** → choose `macros-export.json` from the extracted bundle
6. After import, adjust names/paths if needed (capture source name, project paths, save locations).
7. In Advanced Scene Switcher, open all the imported macros and ensure the correct settings are applied. See [Macro Setup Guide](#macro-setup-guide) for details.
8. Disable HDR in the Switch TV settings. The images included in the bundle were taken with HDR off.

> **For detailed setup instructions with visual guides, see the [Macro Setup Guide](#macro-setup-guide) section below.**

## Features

- **Track Autocorrect**: Automatically identifies and corrects track names from OCR text
- **Lap Time Recording**: Save lap times to CSV with automatic calculations
- **Lap Splits Image Generation**: Automatically create composite images showing all lap times overlaid on final screenshots
- **Fuzzy Matching**: Uses intelligent matching to handle OCR errors and variations
- **Cross-Platform**: Pure Python implementation works on Windows, macOS, and Linux (Currently only Windows is tested)
- **Queue System**: Automatic queuing when CSV files are locked, and an option to manually process the queue
- **Variable-Based Inputs**: Use Advanced Scene Switcher variables as inputs for the macro actions

## Table of Contents

- [mkw-time-trial-tracker](#mkw-time-trial-tracker)
  - [Quick setup](#quick-setup)
  - [Features](#features)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
    - [Step 0: Install Python 3.10](#step-0-install-python-310)
    - [Step 1: Download from Releases](#step-1-download-from-releases)
    - [Step 2: Enable the C++ backend](#step-2-enable-the-c-backend)
    - [Step 3: Install Advanced Scene Switcher](#step-3-install-advanced-scene-switcher)
    - [Step 4: Add the Python Script](#step-4-add-the-python-script)
  - [Usage](#usage)
    - [Quick start: import provided macros (recommended)](#quick-start-import-provided-macros-recommended)
    - [Available Actions](#available-actions)
      - [1. MKW Track Action](#1-mkw-track-action)
      - [2. MKW Save Lap Action](#2-mkw-save-lap-action)
      - [3. MKW Move Old Images Action](#3-mkw-move-old-images-action)
      - [4. MKW Generate Lap Splits Image Action](#4-mkw-generate-lap-splits-image-action)
  - [Macro Setup Guide](#macro-setup-guide)
    - [Overview of Macro System](#overview-of-macro-system)
    - [1. Game State Detection Macros](#1-game-state-detection-macros)
      - [Racing Status Detection](#racing-status-detection)
      - [Current Track Detection](#current-track-detection)
      - [Current Time Detection](#current-time-detection)
      - [Coins Detection](#coins-detection)
      - [Mushroom Usage Detection](#mushroom-usage-detection)
      - [Ghost Replay Detection](#ghost-replay-detection)
    - [2. Control Macros](#2-control-macros)
      - [Time Trial Start](#time-trial-start)
    - [3. Screenshot/Record Data Macros](#3-screenshotrecord-data-macros)
      - [Lap End](#lap-end)
      - [Time Trial Finish](#time-trial-finish)
    - [Configuration Tips](#configuration-tips)
      - [File Paths](#file-paths)
      - [Testing and Calibration](#testing-and-calibration)
    - [Troubleshooting Macro Issues](#troubleshooting-macro-issues)
    - [Data Output](#data-output)
      - [CSV File Structure](#csv-file-structure)
      - [Using Variables](#using-variables)
  - [Contributing](#contributing)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Debug Information](#debug-information)
  - [For Developers](#for-developers)


## Prerequisites

Before setting up this script, ensure you have:

1. **OBS Studio** (latest version recommended)
2. **Advanced Scene Switcher Plugin** - Download from [GitHub](https://github.com/WarmUpTill/SceneSwitcher)
3. **Python 3.10** - Download from [official website](https://www.python.org/downloads/)
   - Other versions have not been tested, I cannot guarantee it will compatible.

## Installation

### Step 0: Install Python 3.10

Download and install Python 3.10 from the [official website](https://www.python.org/downloads/).

### Step 1: Download from Releases

1. Go to the [Latest Release](https://github.com/getBoolean/mk-time-trial-tracker/releases/latest) and download the latest platform bundle for your OS.
   - Names look like: `bundle-windows-latest-py310.zip`, `bundle-ubuntu-latest-py310.zip`, `bundle-macos-latest-py310.zip`.
2. Extract the ZIP to your desired location (e.g., `C:\dev\mk-time-trial-tracker` or `~/mk-time-trial-tracker`).

### Step 2: Enable the C++ backend

This is highly recommended if you will be using the splits image generation feature, otherwise it will fallback to pure Python and take up to 30 seconds to generate a single splits image.

1. Open a terminal and navigate to the extracted folder.
1. Install the included binaries from the `wheelhouse/` folder for faster splits image generation (run these from the extracted folder).
   - Windows (PowerShell):

     ```powershell
     py -m pip install --upgrade pip
     py -m pip install (Resolve-Path wheelhouse\*.whl)
     ```

     CMD alternative:

     ```cmd
     py -m pip install --upgrade pip
     for %f in (wheelhouse\*.whl) do py -m pip install "%f"
     ```

   - macOS/Linux:

     ```bash
     python3 -m pip install --upgrade pip
     python3 -m pip install wheelhouse/*.whl
     ```

### Step 3: Install Advanced Scene Switcher

1. Download the Advanced Scene Switcher plugin from the [official repository](https://github.com/WarmUpTill/SceneSwitcher)
2. Install the plugin following the instructions in the repository
3. Restart OBS Studio after installation
4. Configure Advanced Scene Switcher to use Python 3.10
   - OBS → **Tools** → **Scripts** → **Python Settings** → enter the path to the Python 3.10 directory

### Step 4: Add the Python Script

1. Open OBS Studio
2. Go to **Tools** → **Scripts**
3. Click the **+** button to add a new script
4. Navigate to the extracted folder (or cloned repo) and select `TimeTrialTracker.py`
5. Click **OK** to load the script
6. Configure the script properties:
   - **Base Path**: Directory where CSV files will be saved (default: `G:\OBS\Mario Kart World\time trials`)
   - **Script Repo Path**: Path to this repository (optional, for future features)

## Usage

A number of custom Advanced Scene Switcher macros are provided and can integrate with your existing OBS setup.

### Quick start: import provided macros (recommended)

You can import a ready-made macro setup as a starting point:

1. In OBS, go to **Tools** → **Advanced Scene Switcher** → Macros.
2. Right click the Macros list → **Import** and select `macros-export.json` from this repo.
   - **Download**: [macros-export.json](./macros-export.json)

   ![Import Macros](docs/import-macro.png)

3. After import, adjust these items in all macros to match your setup:
   - **Capture source name**: Replace `AverMedia Live Gamer 4K 2.1` with your video capture source.
   - **File paths**: Update any `C:\dev\mk-time-trial-tracker\...` paths if your repo is saved elsewhere.
   - **Screenshot save paths**: Change `G:\OBS\Mario Kart World\...` to your desired location.
   - **OCR regions/colors**: The macros include example OCR areas and colors tuned to a 4K capture; tweak the areas and thresholds for your resolution/theme if needed.
   - **Script action**: Ensure the actions `MKW Track`, `MKW Save Lap`, and `MKW Move Old Images` are present and configured correctly.
   - **Adjust pixel selections**: The pixel positions for every "Perform check only in area` section are for 2160p (4K) resolution videos. If your capture card is not 4K, you will have to do a little math to get the approximate value.
      - 1080p: 4k pixels / 2
      - 1440p: 4k pixels / 3 * 2
      - Others: 4k pixels / (2160/width)

### Available Actions

The script provides four main Advanced Scene Switcher actions:

#### 1. MKW Track Action

Automatically identifies track names from OCR text.

- **OCR Text Variable Name**: Variable containing the OCR text to process
- **Output**: Sets `Identified Track` and `Identified Track (Filename Safe)` macro properties

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
- **Create Split Image after Final Lap**: Checkbox to indicate if a split image should be created after the final lap.
  - Only used if `Is Final Lap` is also checked.
  - Alternatively use [MKW Generate Lap Splits Image Action](#4-mkw-generate-lap-splits-image-action) to control it manually.

#### 3. MKW Move Old Images Action

Moves image files matching a pattern to a destination subfolder for file organization. This keeps only the current run's screenshots at the base directory.

**Direct Inputs:**

- **File Pattern**: Pattern to match files (default: `Lap-*.png`)
- **Destination Subfolder**: Subfolder name to move old lap screenshots to (default: `lap times`)

#### 4. MKW Generate Lap Splits Image Action

Generates a composite image showing all lap times for a specific run overlaid on a screenshot.

**Variable Inputs:**

- **Run Number Variable Name**: Variable containing the run number to generate image for
- **Screenshot Path Variable**: (Optional) Variable containing path to specific screenshot to use as base
  - If not provided, the screenshot with the run number in its name will be used.

**Features:**

- Automatically combines lap times with screenshot (generated from the final screenshot)
- Shows individual lap times and total time
- Shows shrooms used each lap (only accurate if you do not lose your shrooms to Lakitu)
- Shows coins collected each lap (only accurate if you do not lose coins during the race)
- Outputs file named `Splits_[Track]_Run-[X].png`
- Automatically triggered when final lap is saved with `Is Final Lap` and `Create Split Image after Final Lap` are checked

**Example output:**

![Lap Splits Image](docs/LapTimes_image.png)

## Macro Setup Guide

This section provides detailed setup instructions for each macro included in the system. The macros work together to automatically detect game state, capture screenshots, track lap times, and organize data.

### Overview of Macro System

The macro system consists of several interconnected macros that handle different aspects of time trial tracking:

1. **Detection Macros**: Monitor game state (racing status, ghost replay, track, time, coins, mushrooms)
2. **Control Macros**: Handle time trial start/end events
3. **Screenshot Macros**: Capture images at key moments (lap end, time trial end)

### 1. Game State Detection Macros

#### Racing Status Detection

Determines if a race is currently active, allowing more efficient use of resources when not racing.

![Racing Status](docs/is-racing-macro.png)

**Conditions**:

1. Configure the path to the `lapFlag.png` file
2. Configure the `Perform check only in area` section to the flag next to the lap counter
3. Ensure `Run macro in parallel to other macros` is disabled
4. Test the macro with `Show match`

#### Current Track Detection

Identifies the current track from OCR text and sets track variables.

**Conditions**:
![Current Track Conditions](docs/current-track-macro-conditions.png)

**Actions**:
![Current Track Actions](docs/current-track-macro-actions.png)

**Conditions Setup**:

1. Configure `Sees MKW Logo` path to the `mkLogo.png` file
1. Configure the `Perform check only in area` section to the MKW logo on the track loading screen screen
1. Configure the `Track Name` condition to the track name on the track loading screen.
   - Ensure it is wide enough for the longest track names, but not too wide or tall that it includes the background, which confuses the OCR detection.

**Actions Setup**:

1. Create variable `Current Track OCR` and have it set to the `OCR text` macro property
1. Create variable `Current Track` and have it set to the `Identified Track` macro property, ensure the variable has enabled `Save variable value`
1. Create variable `Current Track Filename Safe` and have it set to the `Identified Track (Filename Safe)` macro property, ensure the variable has enabled `Save variable value`

#### Current Time Detection

Detect the current race time, white for the normal timer and yellow for when finishing a lap:

**White Time Display**:
![Current Time White](docs/current-time-white-macro.png)

**Yellow Time Display**:
![Current Time Yellow](docs/current-time-yellow-macro.png)

- **Note:** Ensure `Perform actions only on condition change` is disabled for both macros.

**Conditions Setup**:

1. Configure the `Current Time` condition's `Perform check only in area` section to the race time display

**Actions Setup**:

1. Create variable `Current Lap Time OCR` and have it set to the `OCR text` macro property

#### Coins Detection

Tracks total coins collected during the race.

![Current Coins](docs/current-coins-macro.png)

**Conditions Setup**:

1. Configure `Sees Coins`'s path to the `coins.png` file
1. Configure `Sees Coins`'s `Perform check only in area` section to the coin icon next to the coin counter
1. Configure `Coin Count`'s `Perform check only in area` section to the coin counter

**Actions Setup**:

1. Create variable `CurrentCoins` and have it set to the `OCR text` macro property, ensure the variable has enabled `Save variable value`

#### Mushroom Usage Detection

The system tracks mushroom usage with separate macros for different counts:

**1 Mushroom Left**:
![1 Mushroom](docs/1shroom-macro.png)

**2 Mushrooms Left**:
![2 Mushrooms](docs/2shroom-macro.png)

**3 Mushrooms Left**:
![3 Mushrooms](docs/3shroom-macro.png)

**No Mushrooms Left**:
![0 Mushrooms](docs/0shroom-macro.png)

**Conditions Setup**:

1. For `1shroom`, `2shrooms`, and `3shrooms` macros:
   - Configure the `Perform check only in area` section to the items section
   - Configure the path to the corresponding `1shroom.png`, `2shrooms.png`, or `3shrooms.png` file
   - Ensure `Run macro in parallel to other macros` is disabled
1. No changes needed for the `0shrooms` macro

**Actions Setup**:

1. Create variable `UsedShrooms`, ensure the variable has enabled `Save variable value`
   - `1shroom` sets it to 2
   - `2shrooms` sets it to 1
   - `3shrooms` sets it to 0
   - `0shrooms` sets it to 3

#### Ghost Replay Detection

Determines if a ghost replay is currently active.

**Start Time Trial**:`
![Start Time Trial](docs/is-start-time-trial-macro.png)

**View Replay**:
![View Replay](docs/is-view-ghost-macro.png)

**Race Against Ghost**:
![Race Against Ghost](docs/is-race-against-ghost-selected-macro.png)

**Conditions Setup**:

1. For `Start Time Trial` and `View Replay` macros:
   - Configure the `Perform check only in area` section to the text above the `OK` button when starting a time trial or viewing a ghost replay
   - Configure the path to the corresponding `startTimeTrial.png` and `viewReplay.png` file
   - Enable the `Use alpha channel as mask for pattern` checkbox both macros
1. For `Race Against Ghost` macro:
   - Configure `Sees Race Against Ghost Selected` and `Sees Race Against Ghost Not Selected`'s `Perform check only in area` section to the button in the pause menu when racing against a ghost
   - Configure the path to the corresponding `raceAgainstGhostSelected.png` and `raceAgainstGhostNotSelected.png` files
   - Enable the `Use alpha channel as mask for pattern` checkbox for both video conditions

**Actions Setup**:

1. Create variable `IsGhost` (ensure the variable has enabled `Save variable value`)
   - `is-start-time-trial` and `is-race-against-ghost-selected` sets it to false
   - `is-view-ghost` sets it to true

### 2. Control Macros

#### Time Trial Start

Triggers when a time trial begins, initializing tracking variables.

**Conditions**:
![TT Start Conditions](docs/tt-start-macro-conditions.png)

**Actions**:
![TT Start Actions](docs/tt-start-macro-actions.png)

**Conditions Setup**:

1. Configure the `Perform check only in area` section to the time trial timer
1. Configure the path to the `time-zero.png` file
1. Enable the `Use alpha channel as mask for pattern` checkbox
1. Increase `Threshold` to `0.99999`, otherwise it will get false positives due to the transparent background

**Actions Setup**:

1. Create variable `Current TT Lap` and have it set to `1`, ensure the variable has enabled `Save variable value`
1. Create variable `Next TT Lap` and have it set to `2`, ensure the variable has enabled `Save variable value`
1. Create variable `TT Run Number` and have it increment by `1`, ensure the variable is set to `Save variable value`
1. In the `MKW Move Old Images` action
   - Configure the `File Pattern` to the naming pattern you use in the [Lap End](#lap-end) section, blob patterns are supported (e.g., `Lap-*.png`)
   - Configure the `Destination Subfolder` name for old lap images to be moved to in the base directory (e.g., `lap times`)

### 3. Screenshot/Record Data Macros

#### Lap End

Captures screenshots at the end of each lap and saves the lap time data.

**Conditions**:
![Lap End Conditions](docs/screenshot-lap-end-macro-conditions.png)

**Actions**:
![Lap End Actions](docs/screenshot-lap-end-macro-actions.png)

**Conditions Setup**:

1. Should only run if `IsGhost` is false
1. Configure `Current Lap is Next Lap` condition's `Perform check only in area` section to the lap counter

**Actions Setup**:

1. Optionally take a screenshot. This is not used by the script, it is for your own records and to double check the lap time data.
   - The name should follow a pattern like `Lap-*.png`
   - You can use variables in the file/folder path, e.g., `Lap-Screenshot_Track-${Current Track Filename Safe}_Run-${TT Run Number}_Lap-${Current TT Lap}.png`
1. Configure the `MKW Save Lap` action with the corresponding variables
   - Ensure `Is Final Lap` is set to `false`
1. `Current TT Lap` is set to `${Next TT Lap}`
1. `Next TT Lap` is set to `${Current TT Lap} + 1`

#### Time Trial Finish

Captures final screenshot when time trial completes.

**Conditions**:
![TT End Conditions](docs/screenshot-tt-end-macro-conditions.png)

**Actions**:
![TT End Actions](docs/screenshot-tt-end-macro-actions.png)

**Conditions Setup**:

1. Only runs if `Current TT Lap` is not `0` (prevents duplicate screenshots)
1. Configure `Is Results Screen` condition's `Perform check only in area` section to cover both time trail results boxes
1. Configure the path to the `tt-results.png` file

**Actions Setup**:

1. Take a screenshot for the splits image, ensure it ends with `-Final.png`
   - If you want it moved to the `lap times` subfolder with the `MKW Move Old Images` action from the [Time Trial Start](#time-trial-start) section, ensure it conforms to the naming pattern (e.g., starts with `Lap-` and ends with `.png`)
1. Configure the `MKW Save Lap` action with the corresponding variables
   - Ensure `Is Final Lap` is set to `true`
   - Enable `Create Split Image after Final Lap` for a sharable splits image.
   - **Note:** The split image generation will take a significant amount of time if you do not enable the C++ backend in the [Installation](#installation) section.
1. Sets `Current TT Lap` to `0`

### Configuration Tips

#### File Paths

1. **Screenshot Locations**: Organize screenshots by track using variables: `G:\OBS\Mario Kart World\${Current Track}\`
2. **CSV Output**: Configure base path in script properties for CSV file location
3. **Image Organization**: Use `MKW Move Old Images` action to keep screenshots organized

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

- `Identified Track`: Canonical track name from OCR
- `Identified Track (Filename Safe)`: Filesystem-safe version of track name

To use these elsewhere:

1. Add a **Variable** action after the `MKW Track` script action
2. Set **Variable name** to e.g. `Current Track`  
3. Set the value from **Macro properties** → select `Identified Track`

You can then reference variables in macros using `${Variable Name}`. Examples:

- File path: `C:\OBS\Mario Kart World\${Current Track}\`
- Text: `Current Track: ${Current Track}`

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

## For Developers

Clone the repository

```bash
git clone https://github.com/getBoolean/mk-time-trial-tracker
cd mk-time-trial-tracker
```

If changes are made to the C++ backend extention, you must rebuild the wheel:

Windows:

```powershell
py -m pip install --upgrade pip build
py -m build --wheel
py -m pip install dist\*.whl
```

macOS/Linux:

```bash
python3 -m pip install --upgrade pip build
python3 -m build --wheel
python3 -m pip install dist/*.whl
```
