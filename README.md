# mk-time-trial-tracker

An OBS Studio script for the Advanced Scene Switcher plugin that provides automatic track name correction for Mario Kart Wii time trials.

## Quick setup

1. Install Advanced Scene Switcher:
   - Download from the plugin's GitHub and install, then restart OBS.
2. Add this script to OBS:
   - OBS → **Tools** → **Scripts** → **+** → select `track_autocorrect.py`.
3. Import the provided macro:
   - OBS → **Tools** → **Advanced Scene Switcher** → Macros (⋯) → **Import** → choose `macros-export.json`.
4. After import, adjust names/paths if needed (capture source name, project paths, save locations).
5. In Advanced Scene Switcher, open the imported `current-track` macro and ensure the `MKW Track` action's setting **OCR Text Variable Name** matches your OCR variable (default: `Current Track OCR`).

## Features

- **Track Autocorrect**: Automatically identifies and corrects track names from OCR text
- **Fuzzy Matching**: Uses intelligent matching to handle OCR errors and variations
- **Advanced Scene Switcher Integration**: Works seamlessly with OBS macros and scene switching

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
4. Navigate to and select `track_autocorrect.py`
5. Click **OK** to load the script

### Step 3: Configure OCR Source

You'll need an OCR source that can read the track name from your game. This could be:

- A text source with OCR enabled
- A browser source with OCR capabilities
- Any other OCR solution that can provide text to OBS

## Usage

### Quick start: import provided macros (recommended)

You can import a ready-made macro setup as a starting point:

1. In OBS, go to **Tools** → **Advanced Scene Switcher** → Macros.
2. Open the Macros menu (⋯) → **Import** and select `macros-export.json` from this repo.
3. After import, adjust these items in all macros to match your setup:
   - **Capture source name**: Replace `AverMedia Live Gamer 4K 2.1` with your video capture source.
   - **File paths**: Update any `C:\dev\mk-time-trial-tracker\...` paths if your repo is saved elsewhere.
   - **Screenshot save paths**: Change `G:\OBS\Mario Kart World\...` to your desired location.
   - **OCR regions/colors**: The macros include example OCR areas and colors tuned to a 4K capture; tweak the areas and thresholds for your resolution/theme if needed.
   - **Script action**: Ensure the action named `MKW Track` is present (loaded via this script) and the setting `OCR Text Variable Name` matches your OCR variable (default: `Current Track OCR`).
   - **PowerShell actions**: If you use the provided scripts, confirm `move-old-images.ps1` and `save_lap_time.ps1` paths match your system.

### Using the Identified Track

The script exposes a macro property (temporary variable) named `identified_track`.

To use it elsewhere, first assign it to an Advanced Scene Switcher variable:

1. Add a **Variable** action after the `MKW Track` script action.
2. Set **Variable name** to e.g. `Current Track`.
3. Set the value from **Temp variable** → select `identified_track`.

You can then reference that variable in macros and supported fields using `${Current Track}`. Examples:

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

## Contributing

If you find issues or want to add support for additional tracks/OCR variations, feel free to submit a pull request or open an issue.
