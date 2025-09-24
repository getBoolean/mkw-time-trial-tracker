import obspython as obs

# Required by advss helpers
import threading
from typing import NamedTuple
import os
import json
import time
import csv

# Image processing with core Python libraries
import struct
import zlib

action_name = "MKW Track"

# New action for saving lap times
save_action_name = "MKW Save Lap"

# New action for moving old images
move_images_action_name = "MKW Move Old Images"

# New action for generating lap time images
generate_image_action_name = "MKW Generate Lap Times Image"

# Script-level settings (updated via script_update)
g_base_path = os.path.join("G:", "OBS", "Mario Kart World", "time trials")
g_repo_path = ""
g_lap_times_scale = 3.0  # Fixed scale factor for lap times box size

# Supported resolution configurations with hardcoded values
SUPPORTED_RESOLUTIONS = {
    "1080p": {
        "width": 1920,
        "height": 1080,
        "font_size": 16,
        "char_spacing": 13,
        "base_padding": 5,
        "line_spacing": 30,
        "margin": 30,
    },
    "1440p": {
        "width": 2560,
        "height": 1440,
        "font_size": 18,
        "char_spacing": 21,
        "base_padding": 7,
        "line_spacing": 33,
        "margin": 60,
    },
    "2160p": {
        "width": 3840,
        "height": 2160,
        "font_size": 24,
        "char_spacing": 27,
        "base_padding": 10,
        "line_spacing": 50,
        "margin": 80,
    },
}

# Optional fast C extension
try:
    import lapimg  # type: ignore
except Exception:
    lapimg = None


###############################################################################
# Macro action functions
###############################################################################


def run_action(data, instance_id):
    ocr_text_variable = obs.obs_data_get_string(data, "ocr_text")
    ocr_text = advss_get_variable_value(ocr_text_variable)
    if ocr_text is None:
        obs.script_log(obs.LOG_WARNING, "OCR text variable not found")
        return
    ocr_text = ocr_text.strip()
    identified_track = find_closest_track(ocr_text)
    if identified_track is None:
        obs.script_log(obs.LOG_WARNING, "No track found for OCR text: " + ocr_text)
        return

    obs.script_log(
        obs.LOG_INFO,
        "OCR text: " + ocr_text + " - Identified track: " + identified_track,
    )
    # Set macro properties: canonical name and a filesystem-safe variant
    advss_set_temp_var_value("identified_track", identified_track, instance_id)
    advss_set_temp_var_value(
        "identified_track_safe", make_filesystem_safe(identified_track), instance_id
    )


def find_closest_track(ocr_text):
    # Normalize helper
    def _normalize(name: str) -> str:
        s = name.lower()
        replacers = {
            "'": "",
            "’": "",
            "?": "question",
            "-": " ",
            ",": " ",
            ".": " ",
            "&": " and ",
        }
        for k, v in replacers.items():
            s = s.replace(k, v)
        # Collapse whitespace
        s = " ".join(s.split())
        return s

    # Canonical track list (unique, deduped)
    tracks = [
        "Mario Bros. Circuit",
        "Crown City",
        "Whistlestop Summit",
        "DK Spaceport",
        "Desert Hills",
        "Shy Guy Bazaar",
        "Wario Stadium",
        "Airship Fortress",
        "DK Pass",
        "Starview Peak",
        "Sky-High Sundae",
        "Wario Shipyard",
        "Koopa Troopa Beach",
        "Faraway Oasis",
        "Peach Stadium",
        "Peach Beach",
        "Salty Salty Speedway",
        "Dino Dino Jungle",
        "Great ? Block Ruins",
        "Cheep Cheep Falls",
        "Dandelion Depths",
        "Boo Cinema",
        "Dry Bones Burnout",
        "Moo Moo Meadows",
        "Choco Mountain",
        "Toad's Factory",
        "Bowser's Castle",
        "Acorn Heights",
        "Mario Circuit",
        "Rainbow Road",
    ]

    # Regional/alias mappings -> canonical
    alias_to_canonical = {
        # Wario Shipyard
        "warios galleon": "Wario Shipyard",
        "wario galleon": "Wario Shipyard",
        "warios shipyard": "Wario Shipyard",
        # Great ? Block Ruins
        "great question block ruins": "Great ? Block Ruins",
        "great block ruins": "Great ? Block Ruins",
        # Sky-High Sundae
        "sky high sundae": "Sky-High Sundae",
        # Toad's Factory
        "toads factory": "Toad's Factory",
        # Cheep Cheep Falls common OCR
        "cheap cheap falls": "Cheep Cheep Falls",
        "cheep-cheep falls": "Cheep Cheep Falls",
        # Moo Moo Meadows
        "moomoo meadows": "Moo Moo Meadows",
        # Mario Circuit variants
        "mario bros circuit": "Mario Bros. Circuit",
        "mario brothers circuit": "Mario Bros. Circuit",
        # Peach Stadium
        "peach stadium": "Peach Stadium",
        # Bowser's Castle
        "bowsers castle": "Bowser's Castle",
        # Koopa Troopa Beach
        "koopa beach": "Koopa Troopa Beach",
        # DK prefixed
        "donkey kong spaceport": "DK Spaceport",
        "donkey kong pass": "DK Pass",
        # Shy Guy Bazaar
        "shyguy bazaar": "Shy Guy Bazaar",
        # Wario Stadium
        "wariostadium": "Wario Stadium",
    }

    # Precompute normalized names
    normalized_to_canonical = {}
    for t in tracks:
        normalized_to_canonical[_normalize(t)] = t

    # Try direct/alias resolution first
    norm_ocr = _normalize(ocr_text)
    if norm_ocr in normalized_to_canonical:
        return normalized_to_canonical[norm_ocr]
    if norm_ocr in alias_to_canonical:
        return alias_to_canonical[norm_ocr]

    # Try contains-based alias (for partial OCRs)
    for alias, canon in alias_to_canonical.items():
        if alias in norm_ocr:
            return canon

    # Fallback: fuzzy match using difflib
    import difflib

    best_match = None
    best_score = -1.0
    for norm_name, canon in normalized_to_canonical.items():
        score = difflib.SequenceMatcher(None, norm_ocr, norm_name).ratio()
        # Token sort partial similarity to be more robust
        if score < 0.92:
            tokens_ocr = sorted(norm_ocr.split())
            tokens_name = sorted(norm_name.split())
            token_score = difflib.SequenceMatcher(
                None, " ".join(tokens_ocr), " ".join(tokens_name)
            ).ratio()
            score = max(score, token_score)
        if score > best_score:
            best_score = score
            best_match = canon

    # If score is very low, just return the original text to avoid wrong mapping
    if best_score < 0.6 or best_match is None:
        return None
    return best_match


def make_filesystem_safe(name: str) -> str:
    """Create a file path safe version of the track name.

    - Remove characters invalid on Windows file systems: <>:"/\|?*
    - Remove punctuation commonly problematic in paths: ' , .
    - Collapse whitespace to single spaces and trim
    """
    import re

    s = name
    # Remove Windows invalid filename characters
    s = re.sub(r'[<>:"/\\|?*]', "", s)
    # Remove specific punctuation mentioned and common ones
    s = s.replace("'", "").replace(",", "").replace(".", "")
    # Collapse whitespace
    s = " ".join(s.split())
    # Optionally, limit overly long names
    return s[:100]


def get_action_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(
        props, "ocr_text", "OCR Text Variable Name", obs.OBS_TEXT_DEFAULT
    )
    return props


def get_action_defaults():
    default_settings = obs.obs_data_create()
    obs.obs_data_set_default_string(default_settings, "ocr_text", "Current Track OCR")
    return default_settings


def get_action_macro_properties():
    return [
        MacroProperty(
            "identified_track", "Identified Track", "Identified Track for MKW"
        ),
        MacroProperty(
            "identified_track_safe",
            "Identified Track (Filename Safe)",
            "File path safe version of Identified Track",
        ),
    ]


###############################################################################
# Script settings and description
###############################################################################


def script_description():
    return f'Adds the macro action "{action_name}" for the advanced scene switcher'


def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_path(
        props,
        "base_path",
        "Base Path",
        obs.OBS_PATH_DIRECTORY,
        None,
        None,
    )
    obs.obs_properties_add_path(
        props,
        "repo_path",
        "Script Repo Path",
        obs.OBS_PATH_DIRECTORY,
        None,
        None,
    )
    obs.obs_properties_add_button(
        props,
        "process_queue_btn",
        "Process Queue Now",
        _on_process_queue_button,
    )
    obs.obs_properties_add_button(
        props,
        "create_last_image_btn",
        "Create Image for Last Final Lap",
        _on_create_last_image_button,
    )
    return props


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "base_path", g_base_path)
    obs.obs_data_set_default_string(settings, "repo_path", g_repo_path)


def script_update(settings):
    global g_base_path, g_repo_path
    base_path_val = obs.obs_data_get_string(settings, "base_path")
    repo_path_val = obs.obs_data_get_string(settings, "repo_path")
    if base_path_val:
        g_base_path = base_path_val
    if repo_path_val:
        g_repo_path = repo_path_val


###############################################################################
# Main script entry point
###############################################################################


def script_load(settings):
    global action_name
    obs.script_log(obs.LOG_INFO, "=== SCRIPT LOAD DEBUG ===")
    obs.script_log(
        obs.LOG_INFO,
        f"SUPPORTED_RESOLUTIONS during script load: {SUPPORTED_RESOLUTIONS}",
    )
    obs.script_log(
        obs.LOG_INFO, f"g_lap_times_scale during script load: {g_lap_times_scale}"
    )
    obs.script_log(obs.LOG_INFO, "=== END SCRIPT LOAD DEBUG ===")
    advss_register_action(
        action_name,
        run_action,
        get_action_properties,
        get_action_defaults(),
        get_action_macro_properties(),
    )
    # Register Save Lap Time action
    advss_register_action(
        save_action_name,
        run_action_save_lap,
        get_save_action_properties,
        get_save_action_defaults(),
        None,
    )
    # Register Move Old Images action
    advss_register_action(
        move_images_action_name,
        run_action_move_images,
        get_move_images_action_properties,
        get_move_images_action_defaults(),
        None,
    )
    # Register Generate Lap Times Image action
    advss_register_action(
        generate_image_action_name,
        run_action_generate_image,
        get_generate_image_action_properties,
        get_generate_image_action_defaults(),
        None,
    )


def script_unload():
    global action_name
    advss_deregister_action(action_name)
    advss_deregister_action(save_action_name)
    advss_deregister_action(move_images_action_name)
    advss_deregister_action(generate_image_action_name)


###############################################################################

# Advanced Scene Switcher helper functions below:
# Usually you should not have to modify this code.
# Simply copy paste it into your scripts.


###############################################################################
# Actions
###############################################################################


# The advss_register_action() function is used to register custom actions
# It takes the following arguments:
# 1. The name of the new action type.
# 2. The function callback which should run when the action is executed.
# 3. The optional function callback which return the properties to display the
#    settings of this action type.
# 4. The optional default_settings pointer used to set the default settings of
#    newly created actions.
#    The pointer must not be freed within this script.
# 5. The optional list of macro properties associated with this action type.
#    You can set values using advss_set_temp_var_value().


def advss_register_action(
    name,
    callback,
    get_properties=None,
    default_settings=None,
    macro_properties=None,
):
    advss_register_segment_type(
        True, name, callback, get_properties, default_settings, macro_properties
    )


def advss_deregister_action(name):
    advss_deregister_segment(True, name)


###############################################################################
# Conditions
###############################################################################


# The advss_register_condition() function is used to register custom conditions
# It takes the following arguments:
# 1. The name of the new condition type.
# 2. The function callback which should run when the condition is executed.
# 3. The optional function callback which return the properties to display the
#    settings of this condition type.
# 4. The optional default_settings pointer used to set the default settings of
#    newly created condition.
#    The pointer must not be freed within this script.
# 5. The optional list of macro properties associated with this condition type.
#    You can set values using advss_set_temp_var_value().
def advss_register_condition(
    name,
    callback,
    get_properties=None,
    default_settings=None,
    macro_properties=None,
):
    advss_register_segment_type(
        False, name, callback, get_properties, default_settings, macro_properties
    )


def advss_deregister_condition(name):
    advss_deregister_segment(False, name)


###############################################################################
# (De)register helpers
###############################################################################


def advss_register_segment_type(
    is_action, name, callback, get_properties, default_settings, macro_properties
):
    proc_handler = obs.obs_get_proc_handler()
    data = obs.calldata_create()

    obs.calldata_set_string(data, "name", name)
    obs.calldata_set_ptr(data, "default_settings", default_settings)

    register_proc = (
        "advss_register_script_action"
        if is_action
        else "advss_register_script_condition"
    )
    obs.proc_handler_call(proc_handler, register_proc, data)

    success = obs.calldata_bool(data, "success")
    if success is False:
        segment_type = "action" if is_action else "condition"
        log_msg = f'failed to register custom {segment_type} "{name}"'
        obs.script_log(obs.LOG_WARNING, log_msg)
        obs.calldata_destroy(data)
        return

    # Run in separate thread to avoid blocking main OBS signal handler.
    # Operation completion will be indicated via signal completion_signal_name.
    def run_helper(data):
        completion_signal_name = obs.calldata_string(data, "completion_signal_name")
        completion_id = obs.calldata_int(data, "completion_id")
        instance_id = obs.calldata_int(data, "instance_id")

        def thread_func(settings):
            settings = obs.obs_data_create_from_json(
                obs.calldata_string(data, "settings")
            )
            callback_result = callback(settings, instance_id)
            if is_action:
                callback_result = True

            reply_data = obs.calldata_create()
            obs.calldata_set_int(reply_data, "completion_id", completion_id)
            obs.calldata_set_bool(reply_data, "result", callback_result)
            signal_handler = obs.obs_get_signal_handler()
            obs.signal_handler_signal(
                signal_handler, completion_signal_name, reply_data
            )
            obs.obs_data_release(settings)
            obs.calldata_destroy(reply_data)

        threading.Thread(target=thread_func, args={data}).start()

    def properties_helper(data):
        if get_properties is not None:
            properties = get_properties()
        else:
            properties = None
        obs.calldata_set_ptr(data, "properties", properties)

    # Helper to register the macro properties every time a new instance of the
    # macro segment is created.
    def register_temp_vars_helper(data):
        id = obs.calldata_int(data, "instance_id")
        proc_handler = obs.obs_get_proc_handler()
        data = obs.calldata_create()
        for prop in macro_properties:
            obs.calldata_set_string(data, "temp_var_id", prop.id)
            obs.calldata_set_string(data, "temp_var_name", prop.name)
            obs.calldata_set_string(data, "temp_var_help", prop.description)
            obs.calldata_set_int(data, "instance_id", id)

            obs.proc_handler_call(proc_handler, "advss_register_temp_var", data)

            success = obs.calldata_bool(data, "success")
            if success is False:
                segment_type = "action" if is_action else "condition"
                log_msg = f'failed to register macro property {prop.id} for {segment_type} "{name}"'
                obs.script_log(obs.LOG_WARNING, log_msg)
        obs.calldata_destroy(data)

    trigger_signal_name = obs.calldata_string(data, "trigger_signal_name")
    property_signal_name = obs.calldata_string(data, "properties_signal_name")
    new_instance_signal_name = obs.calldata_string(data, "new_instance_signal_name")

    signal_handler = obs.obs_get_signal_handler()
    obs.signal_handler_connect(signal_handler, trigger_signal_name, run_helper)
    obs.signal_handler_connect(signal_handler, property_signal_name, properties_helper)
    if isinstance(macro_properties, list):
        obs.signal_handler_connect(
            signal_handler, new_instance_signal_name, register_temp_vars_helper
        )
    obs.calldata_destroy(data)


def advss_deregister_segment(is_action, name):
    proc_handler = obs.obs_get_proc_handler()
    data = obs.calldata_create()

    obs.calldata_set_string(data, "name", name)

    deregister_proc = (
        "advss_deregister_script_action"
        if is_action
        else "advss_deregister_script_condition"
    )

    obs.proc_handler_call(proc_handler, deregister_proc, data)

    success = obs.calldata_bool(data, "success")
    if success is False:
        segment_type = "action" if is_action else "condition"
        log_msg = f'failed to deregister custom {segment_type} "{name}"'
        obs.script_log(obs.LOG_WARNING, log_msg)

    obs.calldata_destroy(data)


###############################################################################
# Macro properties (temporary variables)
###############################################################################


class MacroProperty(NamedTuple):
    id: str  # Internal identifier used by advss_set_temp_var_value()
    name: str  # User facing name
    description: str  # User facing description


def advss_set_temp_var_value(temp_var_id, value, instance_id):
    proc_handler = obs.obs_get_proc_handler()
    data = obs.calldata_create()

    obs.calldata_set_string(data, "temp_var_id", str(temp_var_id))
    obs.calldata_set_string(data, "value", str(value))
    obs.calldata_set_int(data, "instance_id", int(instance_id))
    obs.proc_handler_call(proc_handler, "advss_set_temp_var_value", data)

    success = obs.calldata_bool(data, "success")
    if success is False:
        obs.script_log(
            obs.LOG_WARNING, f'failed to set value for macro property "{temp_var_id}"'
        )

    obs.calldata_destroy(data)


###############################################################################
# Variables
###############################################################################


# The advss_get_variable_value() function can be used to query the value of a
# variable with a given name.
# None is returned in case the variable does not exist.
def advss_get_variable_value(name):
    proc_handler = obs.obs_get_proc_handler()
    data = obs.calldata_create()

    obs.calldata_set_string(data, "name", name)
    obs.proc_handler_call(proc_handler, "advss_get_variable_value", data)

    success = obs.calldata_bool(data, "success")
    if success is False:
        obs.script_log(obs.LOG_WARNING, f'failed to get value for variable "{name}"')
        obs.calldata_destroy(data)
        return None

    value = obs.calldata_string(data, "value")

    obs.calldata_destroy(data)
    return value


# The advss_set_variable_value() function can be used to set the value of a
# variable with a given name.
# True is returned if the operation was successful.
def advss_set_variable_value(name, value):
    proc_handler = obs.obs_get_proc_handler()
    data = obs.calldata_create()

    obs.calldata_set_string(data, "name", name)
    obs.calldata_set_string(data, "value", value)
    obs.proc_handler_call(proc_handler, "advss_set_variable_value", data)

    success = obs.calldata_bool(data, "success")
    if success is False:
        obs.script_log(obs.LOG_WARNING, f'failed to set value for variable "{name}"')

    obs.calldata_destroy(data)
    return success


###############################################################################
# Lap time saving functionality (cross-platform, CSV files)
###############################################################################


def _csv_file_path(base_path):
    return os.path.join(base_path, "lap_times.csv")


def _queue_file_path(base_path):
    return os.path.join(base_path, "lap_times_queue.json")


def _ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _test_csv_locked(path):
    try:
        # Try a lightweight open to detect sharing violations (mostly on Windows)
        f = open(path, "a+b")
        try:
            if hasattr(os, "fsync"):
                os.fsync(f.fileno())
        finally:
            f.close()
        return False
    except Exception:
        return True


def _read_queue(base_path):
    qpath = _queue_file_path(base_path)
    if not os.path.exists(qpath):
        return []
    try:
        with open(qpath, "r", encoding="utf-8") as f:
            raw = f.read()
            if not raw.strip():
                return []
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            else:
                return [data]
    except Exception as e:
        try:
            backup = qpath + ".bak_" + time.strftime("%Y%m%d%H%M%S")
            try:
                with open(qpath, "rb") as src, open(backup, "wb") as dst:
                    dst.write(src.read())
            except Exception:
                pass
            os.remove(qpath)
        except Exception:
            pass
        obs.script_log(obs.LOG_WARNING, f"Queue file corrupt, cleared: {e}")
        return []


def _write_queue(base_path, items):
    qpath = _queue_file_path(base_path)
    _ensure_dir(os.path.dirname(qpath))
    with open(qpath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _add_to_queue(base_path, submission):
    items = _read_queue(base_path)
    items.append(submission)
    _write_queue(base_path, items)


def _convert_laptime_to_seconds(time_str):
    if time_str is None:
        return 0.0
    s = str(time_str).strip()
    parts = s.split(":", 1)
    minutes = int(parts[0])
    seconds = float(parts[1])
    return minutes * 60.0 + seconds


def _convert_seconds_to_laptime(seconds_val):
    minutes = int(seconds_val // 60)
    remaining = seconds_val % 60.0
    return f"{minutes}:{remaining:06.3f}"


def _normalize_laptime_format(time_str):
    """Normalize lap time string to always show 3 decimal places (m:ss.mmm format)"""
    if not time_str:
        return "0:00.000"

    original_time = str(time_str).strip()

    # Convert to seconds and back to ensure consistent formatting
    try:
        seconds_val = _convert_laptime_to_seconds(time_str)
        normalized = _convert_seconds_to_laptime(seconds_val)
        obs.script_log(
            obs.LOG_INFO,
            f"Normalized '{original_time}' -> '{normalized}' (via seconds conversion)",
        )
        return normalized
    except (ValueError, TypeError):
        obs.script_log(
            obs.LOG_INFO,
            f"Seconds conversion failed for '{original_time}', trying manual formatting",
        )
        # If conversion fails, try to fix common formatting issues
        time_str = str(time_str).strip()

        # Handle format like "25.4" -> "0:25.400"
        if ":" not in time_str and "." in time_str:
            parts = time_str.split(".")
            if len(parts) == 2:
                seconds = int(parts[0])
                decimal = parts[1].ljust(3, "0")[:3]  # Pad to 3 decimals
                minutes = seconds // 60
                seconds = seconds % 60
                result = f"{minutes}:{seconds:02d}.{decimal}"
                obs.script_log(
                    obs.LOG_INFO, f"Manual format 1: '{original_time}' -> '{result}'"
                )
                return result

        # Handle format like "0:25.4" -> "0:25.400"
        if ":" in time_str and "." in time_str:
            time_parts = time_str.split(":")
            if len(time_parts) == 2:
                minutes = int(time_parts[0])
                sec_parts = time_parts[1].split(".")
                if len(sec_parts) == 2:
                    seconds = int(sec_parts[0])
                    decimal = sec_parts[1].ljust(3, "0")[:3]  # Pad to 3 decimals
                    result = f"{minutes}:{seconds:02d}.{decimal}"
                    obs.script_log(
                        obs.LOG_INFO,
                        f"Manual format 2: '{original_time}' -> '{result}'",
                    )
                    return result

        # Fallback
        obs.script_log(
            obs.LOG_WARNING,
            f"Could not normalize lap time '{original_time}', using fallback",
        )
        return "0:00.000"


def _get_closest_supported_resolution(width, height):
    """Determine the closest supported resolution for given dimensions.

    Returns tuple of (resolution_name, config_dict)
    """
    obs.script_log(obs.LOG_INFO, "=== RESOLUTION DETECTION DEBUG ===")
    obs.script_log(obs.LOG_INFO, f"Input dimensions: {width}x{height}")
    obs.script_log(
        obs.LOG_INFO, f"Available resolutions: {list(SUPPORTED_RESOLUTIONS.keys())}"
    )

    current_aspect_ratio = width / height if height > 0 else 16 / 9
    obs.script_log(obs.LOG_INFO, f"Input aspect ratio: {current_aspect_ratio:.3f}")

    best_match = None
    best_distance = float("inf")

    for res_name, config in SUPPORTED_RESOLUTIONS.items():
        target_aspect_ratio = config["width"] / config["height"]
        # Calculate distance considering both size and aspect ratio
        size_distance = abs((config["width"] * config["height"]) - (width * height))
        aspect_distance = (
            abs(target_aspect_ratio - current_aspect_ratio) * 1000000
        )  # Weight aspect ratio heavily
        total_distance = size_distance + aspect_distance

        obs.script_log(
            obs.LOG_INFO,
            f"  {res_name}: {config['width']}x{config['height']}, aspect={target_aspect_ratio:.3f}, size_dist={size_distance}, aspect_dist={aspect_distance:.0f}, total={total_distance:.0f}",
        )

        if total_distance < best_distance:
            best_distance = total_distance
            best_match = (res_name, config)

    obs.script_log(obs.LOG_INFO, f"SELECTED: {best_match[0]} -> {best_match[1]}")
    obs.script_log(obs.LOG_INFO, "=== END RESOLUTION DETECTION ===")
    return best_match


def _resize_image_pixels(pixels, old_width, old_height, new_width, new_height):
    """Resize image using simple nearest neighbor interpolation.

    Args:
        pixels: List of bytes rows (RGB format)
        old_width, old_height: Original dimensions
        new_width, new_height: Target dimensions

    Returns:
        List of bytes rows at new size
    """
    if old_width == new_width and old_height == new_height:
        return pixels

    try:
        # Try fast C extension first if available
        if lapimg is not None and hasattr(lapimg, "resize_image_rgb"):
            # Convert pixels to contiguous bytes
            rgb_data = b"".join(pixels)
            resized_rgb = lapimg.resize_image_rgb(
                rgb_data, old_width, old_height, new_width, new_height
            )
            # Convert back to list of row bytes
            row_bytes = new_width * 3
            return [
                bytes(resized_rgb[i * row_bytes : (i + 1) * row_bytes])
                for i in range(new_height)
            ]
    except Exception as e:
        obs.script_log(
            obs.LOG_WARNING, f"C extension resize failed: {e}, falling back to Python"
        )

    # Python fallback - simple nearest neighbor
    new_pixels = []
    x_ratio = old_width / new_width
    y_ratio = old_height / new_height

    for new_y in range(new_height):
        old_y = min(int(new_y * y_ratio), old_height - 1)
        old_row = pixels[old_y]
        new_row = bytearray()

        for new_x in range(new_width):
            old_x = min(int(new_x * x_ratio), old_width - 1)
            pixel_offset = old_x * 3
            if pixel_offset + 2 < len(old_row):
                new_row.extend(old_row[pixel_offset : pixel_offset + 3])
            else:
                new_row.extend([0, 0, 0])  # Black pixel fallback

        new_pixels.append(bytes(new_row))

    obs.script_log(
        obs.LOG_INFO,
        f"Resized image from {old_width}x{old_height} to {new_width}x{new_height} using Python",
    )
    return new_pixels


def _validate_inputs(
    lap_time, lap_number, is_final_lap, run_number, track, coins, shrooms
):
    # Lap time format m:ss.mmm
    import re

    if not lap_time or not re.match(r"^\d+:\d{2}\.\d{3}$", str(lap_time).strip()):
        raise ValueError("Invalid lap time format. Expected 0:00.000")
    if int(lap_number) < 1:
        raise ValueError("Lap number must be greater than 0")
    if int(run_number) < 1:
        raise ValueError("Run number must be greater than 0")
    if not str(track).strip():
        raise ValueError("Track name must be provided")
    c = int(coins)
    if c < 0 or c > 20:
        raise ValueError("Coins must be between 0 and 20")
    s = int(shrooms)
    if s < 0 or s > 3:
        raise ValueError("Shrooms must be between 0 and 3")


def _read_csv_data(csv_path):
    """Read existing CSV data and return headers and rows as dictionaries"""
    if not os.path.exists(csv_path):
        return [], []

    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
            return headers, rows
    except Exception:
        return [], []


def _write_csv_data(csv_path, headers, rows):
    """Write CSV data with given headers and rows"""
    _ensure_dir(os.path.dirname(csv_path))
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _save_lap_to_csv(
    base_path, lap_time, lap_number, is_final_lap, run_number, track, coins, shrooms
):
    _ensure_dir(base_path)
    csv_path = _csv_file_path(base_path)

    if os.path.exists(csv_path) and _test_csv_locked(csv_path):
        raise PermissionError("CSV file is locked")

    # Read existing data
    headers, existing = _read_csv_data(csv_path)

    # Define required headers
    required_headers = [
        "Timestamp",
        "RunNumber",
        "LapNumber",
        "Time",
        "LapTimeSeconds",
        "IsFinalLap",
        "Track",
        "Coins",
        "Shrooms",
    ]

    # Ensure all required headers are present
    for header in required_headers:
        if header not in headers:
            headers.append(header)

    # Calculate last lap and per-lap coins/shrooms
    now_ts = time.strftime("%Y-%m-%d %H:%M:%S")
    current_seconds = _convert_laptime_to_seconds(lap_time)

    # Previous laps for this run (non-final)
    prev_laps_same_run = [
        r
        for r in existing
        if str(r.get("RunNumber")) == str(run_number)
        and str(r.get("IsFinalLap", "")).lower() in ("false", "0", "none", "")
    ]
    prev_sum_seconds = 0.0
    for r in prev_laps_same_run:
        try:
            prev_sum_seconds += float(r.get("LapTimeSeconds", 0) or 0.0)
        except Exception:
            pass

    last_lap_time = ""
    last_lap_seconds = ""
    if str(is_final_lap).lower() in ("true", "1"):
        if prev_sum_seconds > 0.0:
            last_lap_val = max(0.0, current_seconds - prev_sum_seconds)
            last_lap_time = _convert_seconds_to_laptime(last_lap_val)
            last_lap_seconds = last_lap_val

    # Coins/shrooms per lap
    prev_same_run = [r for r in existing if str(r.get("RunNumber")) == str(run_number)]
    prev_coins = 0
    prev_shrooms = 0
    for r in prev_same_run:
        try:
            prev_coins += int(r.get("Coins", 0) or 0)
        except Exception:
            pass
        try:
            prev_shrooms += int(r.get("Shrooms", 0) or 0)
        except Exception:
            pass

    coins_to_save = int(coins) - int(prev_coins)
    shrooms_to_save = int(shrooms) - int(prev_shrooms)

    # Normalize the lap time to ensure consistent 3-decimal formatting
    if last_lap_time:
        # Final lap - already properly formatted
        time_to_save = last_lap_time
        obs.script_log(obs.LOG_INFO, f"Saving final lap time: '{time_to_save}'")
    else:
        # Regular lap - normalize the input lap_time to ensure proper formatting
        time_to_save = _normalize_laptime_format(lap_time)
        obs.script_log(
            obs.LOG_INFO, f"Saving regular lap time: '{lap_time}' -> '{time_to_save}'"
        )

    # Build new row
    new_row = {
        "Timestamp": now_ts,
        "RunNumber": str(int(run_number)),
        "LapNumber": str(int(lap_number)),
        "Time": time_to_save,
        "LapTimeSeconds": str(last_lap_seconds if last_lap_time else current_seconds),
        "IsFinalLap": str(bool(is_final_lap)),
        "Track": str(track),
        "Coins": str(coins_to_save),
        "Shrooms": str(shrooms_to_save),
    }

    # Add new row to existing data
    existing.append(new_row)

    # Write back to CSV
    _write_csv_data(csv_path, headers, existing)


def _flush_queue(base_path):
    csv_path = _csv_file_path(base_path)
    if os.path.exists(csv_path) and _test_csv_locked(csv_path):
        obs.script_log(obs.LOG_INFO, "CSV locked; skipping queue flush")
        return
    items = _read_queue(base_path)
    if not items:
        return
    failed = []
    for it in items:
        try:
            lap_time = str(it.get("LapTime", "")).strip()
            lap_number = int(it.get("LapNumber", 0))
            is_final_lap = bool(it.get("IsFinalLap", False))
            run_number = int(it.get("RunNumber", 0))
            track = it.get("Track", "")
            coins = int(it.get("Coins", 0))
            shrooms = int(it.get("Shrooms", 0))
            enable_auto_image = bool(it.get("EnableAutoImage", True))

            _save_lap_to_csv(
                base_path,
                lap_time,
                lap_number,
                is_final_lap,
                run_number,
                track,
                coins,
                shrooms,
            )

            # If this is the final lap from queue, create the lap times image (if enabled)
            if is_final_lap and enable_auto_image:
                try:
                    _create_lap_times_image(base_path, run_number)
                except Exception as e:
                    obs.script_log(
                        obs.LOG_WARNING,
                        f"Failed to create lap times image from queue: {e}",
                    )
        except Exception as e:
            obs.script_log(obs.LOG_WARNING, f"Failed to flush a queued item: {e}")
            failed.append(it)
            break
        if os.path.exists(csv_path) and _test_csv_locked(csv_path):
            # Keep remainder
            idx = items.index(it)
            failed.extend(items[idx + 1 :])
            break
    if failed:
        _write_queue(base_path, failed)
    else:
        qpath = _queue_file_path(base_path)
        try:
            if os.path.exists(qpath):
                os.remove(qpath)
        except Exception:
            pass


def _on_process_queue_button(props, prop):
    def worker():
        try:
            _flush_queue(g_base_path)
        except Exception as e:
            obs.script_log(obs.LOG_WARNING, f"Process queue failed: {e}")

    threading.Thread(target=worker, args=()).start()
    return True


def _get_last_final_lap(base_path):
    """Get information about the most recent final lap from CSV data"""
    csv_path = _csv_file_path(base_path)
    if not os.path.exists(csv_path):
        return None

    try:
        headers, existing = _read_csv_data(csv_path)

        # Find all final laps
        final_laps = [
            r for r in existing if str(r.get("IsFinalLap", "")).lower() in ("true", "1")
        ]

        if not final_laps:
            return None

        # Pick the highest run number among final laps
        def _to_int(v):
            try:
                return int(str(v).strip())
            except Exception:
                return -1

        highest_run = max((_to_int(r.get("RunNumber")) for r in final_laps), default=-1)
        if highest_run < 0:
            return None

        # From those with the highest run number, pick the latest by timestamp
        candidates = [
            r for r in final_laps if _to_int(r.get("RunNumber")) == highest_run
        ]
        # Timestamps are in '%Y-%m-%d %H:%M:%S' which are lexicographically sortable
        candidates.sort(key=lambda x: x.get("Timestamp", ""), reverse=True)
        last_final_lap = candidates[0]

        return {
            "run_number": highest_run,
            "track": last_final_lap.get("Track", ""),
            "timestamp": last_final_lap.get("Timestamp", ""),
        }

    except Exception as e:
        obs.script_log(obs.LOG_WARNING, f"Error reading last final lap: {e}")
        return None


def _on_create_last_image_button(props, prop):
    def worker():
        try:
            # Add debug logging
            obs.script_log(obs.LOG_INFO, "=== CREATE LAST IMAGE DEBUG ===")
            obs.script_log(
                obs.LOG_INFO, f"Current SUPPORTED_RESOLUTIONS: {SUPPORTED_RESOLUTIONS}"
            )
            obs.script_log(
                obs.LOG_INFO, f"Current g_lap_times_scale: {g_lap_times_scale}"
            )

            last_final_lap = _get_last_final_lap(g_base_path)
            if last_final_lap is None:
                obs.script_log(obs.LOG_WARNING, "No final lap found in CSV data")
                return

            run_number = last_final_lap["run_number"]
            track = last_final_lap["track"]
            timestamp = last_final_lap["timestamp"]

            obs.script_log(
                obs.LOG_INFO,
                f"Creating image for Run {run_number} on {track} (completed at {timestamp})",
            )

            result = _create_lap_times_image(g_base_path, run_number)
            if result:
                obs.script_log(
                    obs.LOG_INFO,
                    f"Successfully created lap times image: {os.path.basename(result)}",
                )
            else:
                obs.script_log(obs.LOG_WARNING, "Failed to create lap times image")

        except Exception as e:
            obs.script_log(obs.LOG_WARNING, f"Create last image failed: {e}")

    threading.Thread(target=worker, args=()).start()
    return True


###############################################################################
# Lap times image generation (Pure Python)
###############################################################################


def _get_best_worst_lap_times(base_path, track_name, shrooms_count, run_number):
    """Calculate best and worst lap times for each lap number on a specific track with specific shroom count."""
    csv_path = _csv_file_path(base_path)
    if not os.path.exists(csv_path):
        return {}, {}

    try:
        headers, existing = _read_csv_data(csv_path)

        # Filter for the specific track and shroom count (include all laps, including final laps)
        track_laps = [
            r
            for r in existing
            if str(r.get("Track", "")).strip() == track_name
            and str(r.get("Shrooms", "")).strip() == str(shrooms_count)
            and str(r.get("RunNumber", "")).strip() != str(run_number)
        ]

        # Group by lap number
        lap_times_by_number = {}
        for lap in track_laps:
            try:
                lap_num = int(lap.get("LapNumber", 0))
                lap_time_seconds = lap.get("LapTimeSeconds", "")
                if lap_time_seconds:
                    seconds_val = float(lap_time_seconds)
                    if lap_num not in lap_times_by_number:
                        lap_times_by_number[lap_num] = []
                    lap_times_by_number[lap_num].append(seconds_val)
            except (ValueError, TypeError):
                continue

        # Calculate best and worst for each lap number
        best_times = {}
        worst_times = {}
        for lap_num, times in lap_times_by_number.items():
            if times:
                best_times[lap_num] = min(times)
                worst_times[lap_num] = max(times)

        for lap in track_laps:
            lap_num = int(lap.get("LapNumber", 0))
            obs.script_log(
                obs.LOG_INFO,
                f"Best lap times for {track_name} Lap {lap_num} with {shrooms_count} shrooms: {best_times[lap_num]}",
            )
            obs.script_log(
                obs.LOG_INFO,
                f"Worst lap times for {track_name} Lap {lap_num} with {shrooms_count} shrooms: {worst_times[lap_num]}",
            )

        return best_times, worst_times
    except Exception as e:
        obs.script_log(obs.LOG_WARNING, f"Error calculating best/worst lap times: {e}")
        return {}, {}


def _get_best_worst_total_times(base_path, track_name, shrooms_count, run_number):
    """Calculate best and worst total times for a specific track with specific shroom count."""
    csv_path = _csv_file_path(base_path)
    if not os.path.exists(csv_path):
        return None, None

    try:
        headers, existing = _read_csv_data(csv_path)

        # Group runs by run number for the specific track and shroom count (excluding current run)
        track_runs = {}
        for r in existing:
            if (
                str(r.get("Track", "")).strip() == track_name
                and str(r.get("Shrooms", "")).strip() == str(shrooms_count)
                and str(r.get("RunNumber", "")).strip() != str(run_number)
            ):
                current_run = str(r.get("RunNumber", ""))
                if current_run not in track_runs:
                    track_runs[current_run] = []
                track_runs[current_run].append(r)

        # Calculate total time for each run
        run_totals = []
        for run_number_key, run_laps in track_runs.items():
            total_seconds = 0.0
            valid_run = True

            for lap in run_laps:
                lap_time_seconds = lap.get("LapTimeSeconds", "")
                if lap_time_seconds:
                    try:
                        seconds_val = float(lap_time_seconds)
                        total_seconds += seconds_val
                    except (ValueError, TypeError):
                        valid_run = False
                        break
                else:
                    valid_run = False
                    break

            if valid_run and total_seconds > 0:
                run_totals.append(total_seconds)

        # Calculate best and worst
        if run_totals:
            best_total = min(run_totals)
            worst_total = max(run_totals)
            obs.script_log(
                obs.LOG_INFO,
                f"Best total time for {track_name} with {shrooms_count} shrooms: {best_total}s",
            )
            obs.script_log(
                obs.LOG_INFO,
                f"Worst total time for {track_name} with {shrooms_count} shrooms: {worst_total}s",
            )
            return best_total, worst_total
        else:
            return None, None

    except Exception as e:
        obs.script_log(
            obs.LOG_WARNING, f"Error calculating best/worst total times: {e}"
        )
        return None, None


def _get_total_time_color(current_total_seconds, best_total, worst_total):
    """Determine the color for a total time based on best/worst performance."""
    # If we don't have best/worst data, use normal green color
    if best_total is None or worst_total is None:
        return (100, 255, 100)  # normal green

    try:
        current_time = float(current_total_seconds)

        # Check if this is the best time (within a small tolerance)
        if abs(current_time - best_total) < 0.001:
            return (100, 255, 100)  # bright green (new best!)

        # Check if this is the worst time (within a small tolerance)
        if abs(current_time - worst_total) > 0.001:
            return (255, 100, 100)  # red (worst time)

        # Check if this is close to the best time (within 0.3 seconds)
        if current_time > best_total and current_time <= best_total + 0.3:
            return (255, 255, 100)  # yellow (close to best)

        # Otherwise, use normal white
        return (255, 255, 255)  # normal white

    except (ValueError, TypeError):
        return (255, 255, 255)  # normal white (fallback)


def _get_lap_color(
    lap_time_seconds, lap_number, best_times, worst_times, is_final=False
):
    """Determine the color for a lap time based on best/worst performance."""
    # Get best and worst times for this lap number
    best_time = best_times.get(lap_number)
    worst_time = worst_times.get(lap_number)

    # If we don't have best/worst data for this lap number, use white (normal)
    if best_time is None or worst_time is None:
        return (100, 255, 100)  # green

    try:
        current_time = float(lap_time_seconds)

        # Check if this is the best time (within a small tolerance for floating point comparison)
        if abs(current_time - best_time) < 0.001:
            return (100, 255, 100)  # green

        # Check if this is the worst time (within a small tolerance for floating point comparison)
        if abs(current_time - worst_time) > 0.001:
            return (255, 100, 100)  # red

        # Check if this is close to the best time (within 0.1 seconds but not the best)
        if current_time > best_time and current_time <= best_time + 0.1:
            return (255, 255, 100)  # yellow (almost best)

        # Otherwise, use white (normal)
        return (255, 255, 255)  # white

    except (ValueError, TypeError):
        return (255, 255, 255)  # white (fallback)


def _get_lap_times_for_run(base_path, run_number):
    """Get all lap times for a specific run from CSV data and return (laps, track)."""
    csv_path = _csv_file_path(base_path)
    if not os.path.exists(csv_path):
        obs.script_log(obs.LOG_WARNING, f"CSV file not found: {csv_path}")
        return [], None

    try:
        headers, existing = _read_csv_data(csv_path)

        # Debug: Show available run numbers and tracks
        available_runs = set()
        available_tracks = set()
        for row in existing:
            if row.get("RunNumber"):
                available_runs.add(str(row.get("RunNumber")))
            if row.get("Track"):
                available_tracks.add(str(row.get("Track")))

        obs.script_log(obs.LOG_INFO, f"Looking for run {run_number}")
        obs.script_log(obs.LOG_INFO, f"Available run numbers: {sorted(available_runs)}")
        obs.script_log(obs.LOG_INFO, f"Available tracks: {sorted(available_tracks)}")

        # Get all laps for this run (ignore track)
        run_laps = [r for r in existing if str(r.get("RunNumber")) == str(run_number)]

        obs.script_log(obs.LOG_INFO, f"Found {len(run_laps)} laps for run {run_number}")

        # Determine track name from CSV rows for this run
        track_from_csv = None
        if run_laps:
            # Prefer the most frequent track value among the run rows
            track_counts = {}
            for r in run_laps:
                t = str(r.get("Track", "")).strip()
                if not t:
                    continue
                track_counts[t] = track_counts.get(t, 0) + 1
            if track_counts:
                track_from_csv = max(track_counts.items(), key=lambda kv: kv[1])[0]

        # Sort by lap number
        run_laps.sort(key=lambda x: int(x.get("LapNumber", 0)))

        lap_times = []
        for lap in run_laps:
            lap_num = int(lap.get("LapNumber", 0))
            lap_time_seconds = lap.get("LapTimeSeconds", "")
            is_final = str(lap.get("IsFinalLap", "")).lower() in ("true", "1")

            if lap_time_seconds:
                try:
                    # Convert from seconds to display format for consistency
                    seconds_val = float(lap_time_seconds)
                    display_time = _convert_seconds_to_laptime(seconds_val)
                    obs.script_log(
                        obs.LOG_INFO,
                        f"Using accurate seconds for lap {lap_num}: {lap_time_seconds}s -> '{display_time}'",
                    )
                    lap_times.append(
                        {
                            "lap_number": lap_num,
                            "time": display_time,
                            "is_final": is_final,
                            "seconds": seconds_val,
                        }
                    )
                except (ValueError, TypeError):
                    # Fallback to string time if seconds conversion fails
                    lap_time_str = lap.get("Time", "")
                    if lap_time_str:
                        obs.script_log(
                            obs.LOG_WARNING,
                            f"Fallback to string time for lap {lap_num}: '{lap_time_str}'",
                        )
                        lap_times.append(
                            {
                                "lap_number": lap_num,
                                "time": lap_time_str,
                                "is_final": is_final,
                                "seconds": None,  # No seconds data available
                            }
                        )

        return lap_times, track_from_csv

    except Exception as e:
        obs.script_log(
            obs.LOG_WARNING, f"Error reading lap times for image generation: {e}"
        )
        return [], None


def _read_png_file(filename):
    """Read a PNG file and return pixel data and dimensions"""
    try:
        with open(filename, "rb") as f:
            # Check PNG signature
            signature = f.read(8)
            if signature != b"\x89PNG\r\n\x1a\n":
                obs.script_log(obs.LOG_WARNING, f"Invalid PNG signature in {filename}")
                return None, 0, 0

            width = height = bit_depth = color_type = 0
            image_data = b""

            while True:
                # Read chunk length
                length_data = f.read(4)
                if len(length_data) != 4:
                    break
                length = struct.unpack(">I", length_data)[0]

                # Read chunk type
                chunk_type = f.read(4)
                if len(chunk_type) != 4:
                    break

                # Read chunk data
                chunk_data = f.read(length)
                if len(chunk_data) != length:
                    break

                # Read CRC (but don't verify it for simplicity)
                crc = f.read(4)
                if len(crc) != 4:
                    break

                if chunk_type == b"IHDR":
                    if length >= 13:
                        width, height, bit_depth, color_type = struct.unpack(
                            ">IIBB", chunk_data[:10]
                        )
                        obs.script_log(
                            obs.LOG_INFO,
                            f"PNG: {width}x{height}, {bit_depth}bit, type {color_type}",
                        )
                elif chunk_type == b"IDAT":
                    image_data += chunk_data
                elif chunk_type == b"IEND":
                    break

            if not image_data or width == 0 or height == 0:
                obs.script_log(obs.LOG_WARNING, f"No image data found in {filename}")
                return None, 0, 0

            # Decompress image data
            try:
                decompressed = zlib.decompress(image_data)
                obs.script_log(obs.LOG_INFO, f"Decompressed {len(decompressed)} bytes")
            except zlib.error as e:
                obs.script_log(obs.LOG_WARNING, f"Failed to decompress PNG data: {e}")
                return None, 0, 0

            # Determine bytes per pixel based on color type
            if color_type == 0:  # Grayscale
                channels = 1
            elif color_type == 2:  # RGB
                channels = 3
            elif color_type == 3:  # Palette - not supported
                obs.script_log(obs.LOG_WARNING, "Palette PNG not supported")
                return None, 0, 0
            elif color_type == 4:  # Grayscale + Alpha
                channels = 2
            elif color_type == 6:  # RGBA
                channels = 4
            else:
                obs.script_log(obs.LOG_WARNING, f"Unsupported color type: {color_type}")
                return None, 0, 0

            bytes_per_pixel = (
                channels * (bit_depth // 8) if bit_depth >= 8 else channels
            )
            scanline_length = width * bytes_per_pixel

            # Process each scanline (row)
            pixels = []
            prev_row = [0] * scanline_length

            for y in range(height):
                # Each scanline starts with a filter byte
                scanline_start = y * (scanline_length + 1)
                if scanline_start + scanline_length + 1 > len(decompressed):
                    obs.script_log(obs.LOG_WARNING, f"Incomplete scanline at row {y}")
                    return None, 0, 0

                filter_type = decompressed[scanline_start]
                scanline = list(
                    decompressed[
                        scanline_start + 1 : scanline_start + scanline_length + 1
                    ]
                )

                # Apply PNG filter
                if filter_type == 0:  # None
                    pass
                elif filter_type == 1:  # Sub
                    for i in range(bytes_per_pixel, len(scanline)):
                        scanline[i] = (
                            scanline[i] + scanline[i - bytes_per_pixel]
                        ) & 0xFF
                elif filter_type == 2:  # Up
                    for i in range(len(scanline)):
                        scanline[i] = (scanline[i] + prev_row[i]) & 0xFF
                elif filter_type == 3:  # Average
                    for i in range(len(scanline)):
                        left = (
                            scanline[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                        )
                        up = prev_row[i]
                        scanline[i] = (scanline[i] + ((left + up) // 2)) & 0xFF
                elif filter_type == 4:  # Paeth
                    for i in range(len(scanline)):
                        left = (
                            scanline[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                        )
                        up = prev_row[i]
                        up_left = (
                            prev_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                        )

                        # Paeth predictor
                        p = left + up - up_left
                        pa = abs(p - left)
                        pb = abs(p - up)
                        pc = abs(p - up_left)

                        if pa <= pb and pa <= pc:
                            predictor = left
                        elif pb <= pc:
                            predictor = up
                        else:
                            predictor = up_left

                        scanline[i] = (scanline[i] + predictor) & 0xFF
                else:
                    obs.script_log(
                        obs.LOG_WARNING, f"Unknown filter type {filter_type} at row {y}"
                    )

                prev_row = scanline[:]

                # Convert to RGB format
                if color_type == 2 and bit_depth == 8:  # RGB
                    pixels.append(bytes(scanline))
                elif color_type == 6 and bit_depth == 8:  # RGBA -> RGB
                    rgb_row = []
                    for i in range(0, len(scanline), 4):
                        rgb_row.extend(scanline[i : i + 3])  # Skip alpha
                    pixels.append(bytes(rgb_row))
                elif color_type == 0:  # Grayscale -> RGB
                    rgb_row = []
                    step = bit_depth // 8 if bit_depth >= 8 else 1
                    for i in range(0, len(scanline), step):
                        gray = scanline[i]
                        rgb_row.extend([gray, gray, gray])
                    pixels.append(bytes(rgb_row))
                else:
                    obs.script_log(
                        obs.LOG_WARNING,
                        f"Unsupported format conversion: type {color_type}, depth {bit_depth}",
                    )
                    return None, 0, 0

            obs.script_log(obs.LOG_INFO, f"Successfully loaded PNG: {width}x{height}")
            return pixels, width, height

    except Exception as e:
        obs.script_log(obs.LOG_WARNING, f"Error reading PNG file {filename}: {e}")
        return None, 0, 0


def _create_png_image(width, height, bg_color=(30, 30, 30)):
    """Create a simple PNG image data structure"""
    # Create pixel data (RGB format)
    pixels = []
    for _ in range(height):
        row = []
        for _ in range(width):
            row.extend(bg_color)  # RGB values
        pixels.append(bytes(row))

    return pixels


def _draw_filled_rect(pixels, width, height, x1, y1, x2, y2, color):
    """Draw a filled rectangle on the pixel data with optional transparency"""
    # Clamp coordinates
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width - 1, x2), min(height - 1, y2)

    # Handle both RGB and RGBA colors
    if len(color) == 4:
        # RGBA with alpha blending
        r, g, b, alpha = color
        alpha_ratio = alpha / 255.0
        inv_alpha = 1.0 - alpha_ratio
    else:
        # RGB - solid color
        r, g, b = color
        alpha_ratio = 1.0
        inv_alpha = 0.0

    for y in range(y1, y2 + 1):
        if 0 <= y < height:
            for x in range(x1, x2 + 1):
                if 0 <= x < width:
                    # Each pixel is 3 bytes (RGB)
                    pixel_offset = x * 3
                    if pixel_offset + 2 < len(pixels[y]):
                        row = bytearray(pixels[y])

                        if alpha_ratio < 1.0:
                            # Alpha blending with existing pixel
                            bg_r, bg_g, bg_b = row[pixel_offset : pixel_offset + 3]
                            new_r = int(r * alpha_ratio + bg_r * inv_alpha)
                            new_g = int(g * alpha_ratio + bg_g * inv_alpha)
                            new_b = int(b * alpha_ratio + bg_b * inv_alpha)
                            row[pixel_offset : pixel_offset + 3] = [new_r, new_g, new_b]
                        else:
                            # Solid color
                            row[pixel_offset : pixel_offset + 3] = [r, g, b]

                        pixels[y] = bytes(row)


def _draw_text_with_background(
    pixels,
    width,
    height,
    x,
    y,
    text,
    text_color=(255, 255, 255),
    bg_color=(0, 0, 0),
    scale=1.0,
    padding=5,
):
    """Draw text with individual background rectangle for better readability"""
    # Calculate text dimensions
    font_height = max(1, int(8 * scale * 3))
    char_spacing = max(1, int(9 * scale * 3))
    text_width = len(text) * char_spacing

    # Draw background rectangle with padding
    bg_x1 = max(0, x - padding)
    bg_y1 = max(0, y - padding)
    bg_x2 = min(width, x + text_width + padding)
    bg_y2 = min(height, y + font_height + padding)

    _draw_filled_rect(pixels, width, height, bg_x1, bg_y1, bg_x2, bg_y2, bg_color)

    # Draw the text on top
    _draw_text_bitmap(pixels, width, height, x, y, text, text_color, scale)


def _draw_text_bitmap(
    pixels, width, height, x, y, text, color=(255, 255, 255), scale=1.0
):
    """Draw text using a comprehensive 8x8 bitmap font with scaling support"""
    # Complete 8x8 bitmap font for ASCII characters
    # Includes numbers, letters (upper/lowercase), and common symbols
    # Scale parameter allows font size scaling
    char_patterns = {
        # Numbers for lap times (0-9)
        "0": [
            0b01111100,
            0b10000010,
            0b10000110,
            0b10001010,
            0b10010010,
            0b10100010,
            0b10000010,
            0b01111100,
        ],
        "1": [
            0b00001000,
            0b00011000,
            0b00001000,
            0b00001000,
            0b00001000,
            0b00001000,
            0b00001000,
            0b00111110,
        ],
        "2": [
            0b01111100,
            0b10000010,
            0b00000010,
            0b00111100,
            0b01000000,
            0b10000000,
            0b10000000,
            0b11111110,
        ],
        "3": [
            0b01111100,
            0b10000010,
            0b00000010,
            0b00111100,
            0b00000010,
            0b00000010,
            0b10000010,
            0b01111100,
        ],
        "4": [
            0b10000010,
            0b10000010,
            0b10000010,
            0b11111110,
            0b00000010,
            0b00000010,
            0b00000010,
            0b00000010,
        ],
        "5": [
            0b11111110,
            0b10000000,
            0b10000000,
            0b11111100,
            0b00000010,
            0b00000010,
            0b10000010,
            0b01111100,
        ],
        "6": [
            0b01111100,
            0b10000010,
            0b10000000,
            0b11111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111100,
        ],
        "7": [
            0b11111110,
            0b00000010,
            0b00000010,
            0b00000100,
            0b00001000,
            0b00010000,
            0b00100000,
            0b01000000,
        ],
        "8": [
            0b01111100,
            0b10000010,
            0b10000010,
            0b01111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111100,
        ],
        "9": [
            0b01111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111110,
            0b00000010,
            0b10000010,
            0b01111100,
        ],
        # Special characters for time display
        " ": [
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        ":": [
            0b00000000,
            0b00000000,
            0b00011000,
            0b00011000,
            0b00000000,
            0b00011000,
            0b00011000,
            0b00000000,
        ],
        ".": [
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00011000,
            0b00011000,
        ],
        # Complete alphabet - Uppercase letters
        "A": [
            0b01111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b11111110,
            0b10000010,
            0b10000010,
            0b10000010,
        ],
        "B": [
            0b11111100,
            0b10000010,
            0b10000010,
            0b11111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b11111100,
        ],
        "C": [
            0b01111100,
            0b10000010,
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000010,
            0b01111100,
        ],
        "D": [
            0b11111000,
            0b10000100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000100,
            0b11111000,
        ],
        "E": [
            0b11111110,
            0b10000000,
            0b10000000,
            0b11111100,
            0b10000000,
            0b10000000,
            0b10000000,
            0b11111110,
        ],
        "F": [
            0b11111110,
            0b10000000,
            0b10000000,
            0b11111100,
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000000,
        ],
        "G": [
            0b01111100,
            0b10000010,
            0b10000000,
            0b10001110,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111100,
        ],
        "H": [
            0b10000010,
            0b10000010,
            0b10000010,
            0b11111110,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
        ],
        "I": [
            0b01111100,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b01111100,
        ],
        "J": [
            0b00111110,
            0b00000010,
            0b00000010,
            0b00000010,
            0b00000010,
            0b10000010,
            0b10000010,
            0b01111100,
        ],
        "K": [
            0b10000010,
            0b10000100,
            0b10001000,
            0b10110000,
            0b11001000,
            0b10000100,
            0b10000010,
            0b10000001,
        ],
        "L": [
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000000,
            0b11111110,
        ],
        "M": [
            0b10000010,
            0b11000110,
            0b10101010,
            0b10010010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
        ],
        "N": [
            0b10000010,
            0b11000010,
            0b10100010,
            0b10010010,
            0b10001010,
            0b10000110,
            0b10000010,
            0b10000010,
        ],
        "O": [
            0b01111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111100,
        ],
        "P": [
            0b11111100,
            0b10000010,
            0b10000010,
            0b11111100,
            0b10000000,
            0b10000000,
            0b10000000,
            0b10000000,
        ],
        "Q": [
            0b01111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10001010,
            0b10000100,
            0b01111010,
            0b00000001,
        ],
        "R": [
            0b11111100,
            0b10000010,
            0b10000010,
            0b11111100,
            0b10010000,
            0b10001000,
            0b10000100,
            0b10000010,
        ],
        "S": [
            0b01111100,
            0b10000010,
            0b10000000,
            0b01111100,
            0b00000010,
            0b00000010,
            0b10000010,
            0b01111100,
        ],
        "T": [
            0b11111110,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
        "U": [
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111100,
        ],
        "V": [
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01000100,
            0b00111000,
        ],
        "W": [
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10010010,
            0b10101010,
            0b11000110,
            0b10000010,
        ],
        "X": [
            0b10000010,
            0b01000100,
            0b00101000,
            0b00010000,
            0b00101000,
            0b01000100,
            0b10000010,
            0b10000010,
        ],
        "Y": [
            0b10000010,
            0b01000100,
            0b00101000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
        ],
        "Z": [
            0b11111110,
            0b00000010,
            0b00000100,
            0b00001000,
            0b00010000,
            0b00100000,
            0b01000000,
            0b11111110,
        ],
        # Complete alphabet - Lowercase letters
        "a": [
            0b00000000,
            0b00000000,
            0b01111100,
            0b00000010,
            0b01111110,
            0b10000010,
            0b01111110,
            0b00000000,
        ],
        "b": [
            0b10000000,
            0b10000000,
            0b11111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b11111100,
            0b00000000,
        ],
        "c": [
            0b00000000,
            0b00000000,
            0b01111100,
            0b10000010,
            0b10000000,
            0b10000010,
            0b01111100,
            0b00000000,
        ],
        "d": [
            0b00000010,
            0b00000010,
            0b01111110,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111110,
            0b00000000,
        ],
        "e": [
            0b00000000,
            0b00000000,
            0b01111100,
            0b10000010,
            0b11111110,
            0b10000000,
            0b01111100,
            0b00000000,
        ],
        "f": [
            0b00111100,
            0b01000010,
            0b01000000,
            0b11111000,
            0b01000000,
            0b01000000,
            0b01000000,
            0b01000000,
        ],
        "g": [
            0b00000000,
            0b00000000,
            0b01111110,
            0b10000010,
            0b01111110,
            0b00000010,
            0b01111100,
            0b00000000,
        ],
        "h": [
            0b10000000,
            0b10000000,
            0b11111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b00000000,
        ],
        "i": [
            0b00010000,
            0b00000000,
            0b00110000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00111000,
            0b00000000,
        ],
        "j": [
            0b00000100,
            0b00000000,
            0b00001100,
            0b00000100,
            0b00000100,
            0b10000100,
            0b01111000,
            0b00000000,
        ],
        "k": [
            0b10000000,
            0b10000000,
            0b10000100,
            0b10001000,
            0b10110000,
            0b11001000,
            0b10000100,
            0b00000000,
        ],
        "l": [
            0b00110000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00010000,
            0b00111000,
            0b00000000,
        ],
        "m": [
            0b00000000,
            0b00000000,
            0b11010100,
            0b10101010,
            0b10101010,
            0b10101010,
            0b10101010,
            0b00000000,
        ],
        "n": [
            0b00000000,
            0b00000000,
            0b11111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000010,
            0b00000000,
        ],
        "o": [
            0b00000000,
            0b00000000,
            0b01111100,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01111100,
            0b00000000,
        ],
        "p": [
            0b00000000,
            0b00000000,
            0b11111100,
            0b10000010,
            0b11111100,
            0b10000000,
            0b10000000,
            0b00000000,
        ],
        "q": [
            0b00000000,
            0b00000000,
            0b01111110,
            0b10000010,
            0b01111110,
            0b00000010,
            0b00000010,
            0b00000000,
        ],
        "r": [
            0b00000000,
            0b00000000,
            0b10111100,
            0b11000000,
            0b10000000,
            0b10000000,
            0b10000000,
            0b00000000,
        ],
        "s": [
            0b00000000,
            0b00000000,
            0b01111110,
            0b10000000,
            0b01111100,
            0b00000010,
            0b11111100,
            0b00000000,
        ],
        "t": [
            0b00010000,
            0b00010000,
            0b01111100,
            0b00010000,
            0b00010000,
            0b00010010,
            0b00001100,
            0b00000000,
        ],
        "u": [
            0b00000000,
            0b00000000,
            0b10000010,
            0b10000010,
            0b10000010,
            0b10000110,
            0b01111010,
            0b00000000,
        ],
        "v": [
            0b00000000,
            0b00000000,
            0b10000010,
            0b10000010,
            0b10000010,
            0b01000100,
            0b00111000,
            0b00000000,
        ],
        "w": [
            0b00000000,
            0b00000000,
            0b10000010,
            0b10010010,
            0b10101010,
            0b11000110,
            0b10000010,
            0b00000000,
        ],
        "x": [
            0b00000000,
            0b00000000,
            0b10000010,
            0b01000100,
            0b00111000,
            0b01000100,
            0b10000010,
            0b00000000,
        ],
        "y": [
            0b00000000,
            0b00000000,
            0b10000010,
            0b10000010,
            0b01111110,
            0b00000010,
            0b01111100,
            0b00000000,
        ],
        "z": [
            0b00000000,
            0b00000000,
            0b11111110,
            0b00000100,
            0b00111000,
            0b01000000,
            0b11111110,
            0b00000000,
        ],
        # Additional useful characters
        "-": [
            0b00000000,
            0b00000000,
            0b00000000,
            0b11111110,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
        ],
        "_": [
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b11111110,
        ],
        "(": [
            0b00001100,
            0b00011000,
            0b00110000,
            0b00110000,
            0b00110000,
            0b00110000,
            0b00011000,
            0b00001100,
        ],
        ")": [
            0b00110000,
            0b00011000,
            0b00001100,
            0b00001100,
            0b00001100,
            0b00001100,
            0b00011000,
            0b00110000,
        ],
        "/": [
            0b00000010,
            0b00000100,
            0b00001000,
            0b00010000,
            0b00100000,
            0b01000000,
            0b10000000,
            0b00000000,
        ],
        "\\": [
            0b10000000,
            0b01000000,
            0b00100000,
            0b00010000,
            0b00001000,
            0b00000100,
            0b00000010,
            0b00000000,
        ],
        ",": [
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00000000,
            0b00011000,
            0b00011000,
            0b00110000,
        ],
        "!": [
            0b00011000,
            0b00011000,
            0b00011000,
            0b00011000,
            0b00011000,
            0b00000000,
            0b00011000,
            0b00000000,
        ],
        "?": [
            0b01111100,
            0b10000010,
            0b00000010,
            0b00001100,
            0b00010000,
            0b00000000,
            0b00010000,
            0b00000000,
        ],
    }

    current_x = x
    char_spacing = max(1, int(9 * scale * 3))

    for char in text:
        if char in char_patterns:
            pattern = char_patterns[char]
            for row_idx, row_pattern in enumerate(pattern):
                for bit_idx in range(8):
                    if row_pattern & (1 << (7 - bit_idx)):
                        # Draw scaled pixels (scale x scale x 3 block for each original pixel)
                        pixel_scale = max(1, int(scale * 3))
                        for sy in range(pixel_scale):
                            for sx in range(pixel_scale):
                                char_y = y + (row_idx * pixel_scale) + sy
                                char_x = current_x + (bit_idx * pixel_scale) + sx
                                if 0 <= char_x < width and 0 <= char_y < height:
                                    pixel_offset = char_x * 3
                                    if pixel_offset + 2 < len(pixels[char_y]):
                                        row = bytearray(pixels[char_y])
                                        row[pixel_offset : pixel_offset + 3] = color
                                        pixels[char_y] = bytes(row)
        current_x += char_spacing


def _save_png_file(pixels, width, height, filename):
    """Save pixel data as a PNG file using pure Python"""

    def write_png_chunk(chunk_type, data):
        """Write a PNG chunk"""
        chunk_data = chunk_type + data
        crc = zlib.crc32(chunk_data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_data + struct.pack(">I", crc)

    # PNG file signature
    png_signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = write_png_chunk(b"IHDR", ihdr_data)

    # Prepare image data
    image_data = b""
    for row in pixels:
        # Add filter byte (0 = None filter)
        image_data += b"\x00" + row

    # Compress image data
    compressed_data = zlib.compress(image_data)
    idat_chunk = write_png_chunk(b"IDAT", compressed_data)

    # IEND chunk
    iend_chunk = write_png_chunk(b"IEND", b"")

    # Write PNG file
    with open(filename, "wb") as f:
        f.write(png_signature)
        f.write(ihdr_chunk)
        f.write(idat_chunk)
        f.write(iend_chunk)


def _extract_run_number_from_filename(filename):
    """Extract run number from screenshot filename"""
    import re

    # Extract just the basename without path
    basename = os.path.basename(filename)

    # Look for pattern "Run-97" in filename like "Lap-Screenshot_Track-DK Spaceport_Run-97_Lap-6-Final.png"
    pattern = r"[Rr]un-(\d+)"
    match = re.search(pattern, basename)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            pass

    return None


def _find_screenshot_for_run(base_path, run_number):
    """Find screenshot that matches the run number, or most recent if no match.

    Searches common locations and supports recursive discovery. Matches files like
    "Lap-Screenshot_..._Run-97_...-Final.png" (PNG/JPG/JPEG).
    """
    import glob

    base_dir = base_path
    parent_dir = os.path.dirname(base_path)
    grandparent_dir = os.path.dirname(parent_dir)

    # Try various screenshot patterns and locations (PNG/JPG/JPEG)
    search_patterns = [
        # In base directory (non-recursive)
        os.path.join(base_dir, "*-Final.png"),
        os.path.join(base_dir, "*-Final.jpg"),
        os.path.join(base_dir, "*-Final.jpeg"),
        os.path.join(base_dir, "*Final.png"),
        os.path.join(base_dir, "*Final.jpg"),
        os.path.join(base_dir, "*Final.jpeg"),
        # In base directory recursively
        os.path.join(base_dir, "**", "*-Final.png"),
        os.path.join(base_dir, "**", "*-Final.jpg"),
        os.path.join(base_dir, "**", "*-Final.jpeg"),
        os.path.join(base_dir, "**", "*Final.png"),
        os.path.join(base_dir, "**", "*Final.jpg"),
        os.path.join(base_dir, "**", "*Final.jpeg"),
        # In parent directory recursively
        os.path.join(parent_dir, "**", "*-Final.png"),
        os.path.join(parent_dir, "**", "*-Final.jpg"),
        os.path.join(parent_dir, "**", "*-Final.jpeg"),
        os.path.join(parent_dir, "**", "*Final.png"),
        os.path.join(parent_dir, "**", "*Final.jpg"),
        os.path.join(parent_dir, "**", "*Final.jpeg"),
        # In grandparent directory recursively (common "G:/OBS" root)
        os.path.join(grandparent_dir, "**", "*-Final.png"),
        os.path.join(grandparent_dir, "**", "*-Final.jpg"),
        os.path.join(grandparent_dir, "**", "*-Final.jpeg"),
        os.path.join(grandparent_dir, "**", "*Final.png"),
        os.path.join(grandparent_dir, "**", "*Final.jpg"),
        os.path.join(grandparent_dir, "**", "*Final.jpeg"),
    ]

    all_screenshots = []
    for pattern in search_patterns:
        try:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                all_screenshots.extend(matches)
                obs.script_log(
                    obs.LOG_INFO,
                    f"Search pattern matched {len(matches)} files: {pattern}",
                )
        except (OSError, IOError):
            continue

    if not all_screenshots:
        obs.script_log(obs.LOG_INFO, "No *-Final.(png|jpg|jpeg) screenshots found")
        return None, None

    # First, try to find a screenshot that matches the run number
    for screenshot in all_screenshots:
        extracted_run = _extract_run_number_from_filename(screenshot)
        if extracted_run == run_number:
            obs.script_log(
                obs.LOG_INFO,
                f"Found matching screenshot for run {run_number}: {screenshot}",
            )
            return screenshot, extracted_run
        else:
            if extracted_run is not None:
                obs.script_log(
                    obs.LOG_INFO,
                    f"Candidate not used (Run-{extracted_run}): {screenshot}",
                )

    # If no exact match, sort by modification time and use the most recent
    all_screenshots.sort(key=os.path.getmtime, reverse=True)
    most_recent = all_screenshots[0]
    extracted_run = _extract_run_number_from_filename(most_recent)

    if extracted_run:
        obs.script_log(
            obs.LOG_INFO,
            f"Using most recent screenshot with run {extracted_run}: {most_recent}",
        )
    else:
        obs.script_log(
            obs.LOG_INFO,
            f"Using most recent screenshot (no run number detected): {most_recent}",
        )

    return most_recent, extracted_run


def _create_lap_times_image(base_path, run_number, final_screenshot_path=None):
    """Create lap times image using fast C extension when available, else Python."""
    obs.script_log(obs.LOG_INFO, "=== CREATE LAP TIMES IMAGE STARTED ===")
    obs.script_log(
        obs.LOG_INFO,
        f"run_number={run_number}, final_screenshot_path={final_screenshot_path}",
    )
    obs.script_log(
        obs.LOG_INFO,
        f"SUPPORTED_RESOLUTIONS keys: {list(SUPPORTED_RESOLUTIONS.keys())}",
    )
    try:
        # Try to find and extract run number from screenshot first
        screenshot_path = final_screenshot_path
        extracted_run_number = None

        if not screenshot_path:
            screenshot_path, extracted_run_number = _find_screenshot_for_run(
                base_path, run_number
            )
        obs.script_log(obs.LOG_INFO, f"Screenshot path: {screenshot_path}")

        # Use extracted run number if available, otherwise fall back to provided run_number
        actual_run_number = (
            extracted_run_number if extracted_run_number is not None else run_number
        )
        obs.script_log(obs.LOG_INFO, f"Extracted run number: {actual_run_number}")

        # Get lap times and track (from CSV) for the actual run number
        lap_times, track_from_csv = _get_lap_times_for_run(base_path, actual_run_number)
        if not lap_times:
            obs.script_log(
                obs.LOG_WARNING, f"No lap times found for run {actual_run_number}"
            )
            return None

        # Also get the raw run data for accurate total calculation
        csv_path = _csv_file_path(base_path)
        _, existing = _read_csv_data(csv_path)
        run_laps = [
            r for r in existing if str(r.get("RunNumber")) == str(actual_run_number)
        ]

        # Determine shroom count for this run (use the most common value from run laps)
        shrooms_count = 0
        if run_laps:
            shroom_counts = {}
            for r in run_laps:
                shrooms = str(r.get("Shrooms", "0")).strip()
                try:
                    shrooms_val = int(shrooms) if shrooms else 0
                    shroom_counts[shrooms_val] = shroom_counts.get(shrooms_val, 0) + 1
                except (ValueError, TypeError):
                    shroom_counts[0] = shroom_counts.get(0, 0) + 1
            if shroom_counts:
                shrooms_count = max(shroom_counts.items(), key=lambda kv: kv[1])[0]

        # Calculate best and worst lap times for this track with the same shroom count
        best_times, worst_times = (
            _get_best_worst_lap_times(
                base_path, track_from_csv, shrooms_count, actual_run_number
            )
            if track_from_csv
            else ({}, {})
        )

        # Calculate best and worst total times for this track with the same shroom count
        best_total, worst_total = (
            _get_best_worst_total_times(
                base_path, track_from_csv, shrooms_count, actual_run_number
            )
            if track_from_csv
            else (None, None)
        )

        # Load background image if available (prefer C loader on Windows)
        background_pixels, bg_width, bg_height = None, 0, 0
        if screenshot_path and os.path.exists(screenshot_path):
            obs.script_log(
                obs.LOG_INFO,
                f"Loading screenshot background: {os.path.basename(screenshot_path)}",
            )
            used_loader = "python"
            if lapimg is not None and hasattr(lapimg, "load_image_rgb"):
                try:
                    rgb, w, h = lapimg.load_image_rgb(screenshot_path)
                    row_bytes = w * 3
                    background_pixels = [
                        bytes(rgb[i * row_bytes : (i + 1) * row_bytes])
                        for i in range(h)
                    ]
                    bg_width, bg_height = w, h
                    used_loader = "c-gdiplus"
                except Exception as e:
                    obs.script_log(
                        obs.LOG_WARNING,
                        f"Fast PNG loader failed ({e}); falling back to Python",
                    )
            if background_pixels is None:
                background_pixels, bg_width, bg_height = _read_png_file(screenshot_path)
                used_loader = "python"
            obs.script_log(obs.LOG_INFO, f"Background loader used: {used_loader}")
            if background_pixels is None:
                obs.script_log(
                    obs.LOG_WARNING,
                    f"Failed to load screenshot {os.path.basename(screenshot_path)}, using default background",
                )

        # Determine target resolution and resize if needed
        input_width = bg_width if background_pixels and bg_width > 0 else 3840
        input_height = bg_height if background_pixels and bg_height > 0 else 2160

        # Get closest supported resolution
        target_res_name, target_res_config = _get_closest_supported_resolution(
            input_width, input_height
        )
        target_width = target_res_config["width"]
        target_height = target_res_config["height"]

        # Resize background if needed
        if background_pixels and bg_width > 0 and bg_height > 0:
            if bg_width != target_width or bg_height != target_height:
                obs.script_log(
                    obs.LOG_INFO,
                    f"Resizing background from {bg_width}x{bg_height} to {target_width}x{target_height} ({target_res_name})",
                )
                background_pixels = _resize_image_pixels(
                    background_pixels, bg_width, bg_height, target_width, target_height
                )
            else:
                obs.script_log(
                    obs.LOG_INFO,
                    f"Background already at target resolution {target_width}x{target_height} ({target_res_name})",
                )
        else:
            obs.script_log(
                obs.LOG_INFO,
                f"Using default background at {target_width}x{target_height} ({target_res_name})",
            )

        # Set final dimensions
        width, height = target_width, target_height

        # Draw semi-transparent background for text area
        # Position text in bottom-right corner for better visibility
        # Make size and position relative to image dimensions for consistency

        # Use hardcoded resolution-specific values, optionally scaled by user preference
        obs.script_log(obs.LOG_INFO, "=== TEXT SCALING DEBUG ===")
        obs.script_log(obs.LOG_INFO, f"Target resolution config: {target_res_config}")
        obs.script_log(obs.LOG_INFO, f"g_lap_times_scale: {g_lap_times_scale}")

        font_size = target_res_config["font_size"]
        char_spacing = target_res_config["char_spacing"]
        base_padding = target_res_config["base_padding"]
        line_spacing = target_res_config["line_spacing"]
        margin = target_res_config["margin"]

        obs.script_log(
            obs.LOG_INFO,
            f"Base values: font={font_size}, char_spacing={char_spacing}, padding={base_padding}, line_spacing={line_spacing}, margin={margin}",
        )

        # Apply user scaling if desired (g_lap_times_scale still available for fine-tuning)
        if g_lap_times_scale != 1.0:
            obs.script_log(
                obs.LOG_INFO, f"Applying user scaling factor: {g_lap_times_scale}"
            )
            font_size = int(font_size * g_lap_times_scale)
            char_spacing = int(char_spacing * g_lap_times_scale)
            base_padding = int(base_padding * g_lap_times_scale)
            line_spacing = int(line_spacing * g_lap_times_scale)
            margin = int(margin * g_lap_times_scale)

        obs.script_log(
            obs.LOG_INFO,
            f"Final values: font={font_size}, char_spacing={char_spacing}, padding={base_padding}, line_spacing={line_spacing}, margin={margin}",
        )
        obs.script_log(obs.LOG_INFO, "=== END TEXT SCALING DEBUG ===")

        obs.script_log(
            obs.LOG_INFO,
            f"Lap times overlay ({target_res_name}): font={font_size}px, padding={base_padding}px, spacing={line_spacing}px",
        )

        # Position in top-left corner with resolution-appropriate margin
        margin_x = margin
        margin_y = margin
        text_x = margin_x
        text_y = margin_y

        # Calculate total time using accurate seconds from CSV (using the same data as above)
        total_seconds = 0.0
        for lap in run_laps:
            lap_time_seconds = lap.get("LapTimeSeconds", "")
            if lap_time_seconds:
                try:
                    seconds_val = float(lap_time_seconds)
                    total_seconds += seconds_val
                    obs.script_log(
                        obs.LOG_INFO,
                        f"Adding lap {lap.get('LapNumber', '?')} to total: {seconds_val}s",
                    )
                except (ValueError, TypeError):
                    pass

        total_time_str = _convert_seconds_to_laptime(total_seconds)
        obs.script_log(
            obs.LOG_INFO,
            f"Total time calculated from accurate seconds: {total_seconds}s -> '{total_time_str}'",
        )

        current_y = text_y + base_padding

        use_fast = lapimg is not None

        if use_fast and not (background_pixels and bg_width > 0 and bg_height > 0):
            obs.script_log(
                obs.LOG_INFO,
                "Lap times image: using fast C implementation (solid background)",
            )
            # Compose whole image in C fast path (solid bg)
            texts = []
            # Convert font_size to scale factor for C extension (C extension expects scale, not pixel size)
            c_scale = max(
                1, font_size // 24
            )  # 24px is base size (8*3), so scale accordingly
            obs.script_log(obs.LOG_INFO, "=== C EXTENSION TEXT DEBUG ===")
            obs.script_log(
                obs.LOG_INFO,
                f"font_size={font_size}, c_scale={c_scale}, base_padding={base_padding}",
            )
            obs.script_log(
                obs.LOG_INFO,
                f"text_x={text_x}, current_y={current_y}, line_spacing={line_spacing}",
            )
            texts.append(
                (
                    text_x + base_padding,
                    current_y,
                    f"Track: {track_from_csv[:50]}",
                    (255, 255, 255),
                    c_scale,
                    base_padding,
                    (0, 0, 0, 220),
                )
            )
            current_y += line_spacing * 2
            for lap in lap_times:
                lap_text = f"Lap {lap['lap_number']}: {lap['time']}"
                color = _get_lap_color(
                    lap.get("seconds"),
                    lap["lap_number"],
                    best_times,
                    worst_times,
                    lap["is_final"],
                )
                texts.append(
                    (
                        text_x + base_padding,
                        current_y,
                        lap_text[:50],
                        color,
                        c_scale,
                        base_padding,
                        (0, 0, 0, 220),
                    )
                )
                current_y += line_spacing
            current_y += line_spacing
            total_color = _get_total_time_color(total_seconds, best_total, worst_total)
            texts.append(
                (
                    text_x + base_padding,
                    current_y,
                    f"Total: {total_time_str}",
                    total_color,
                    c_scale,
                    base_padding,
                    (0, 0, 0, 220),
                )
            )

            # Call C extension to compose RGB buffer
            rgb = lapimg.compose_lap_image(
                width=width,
                height=height,
                bg_rgb=(30, 30, 30),
                texts=texts,
            )
            # Convert to pixels list[bytes] rows
            row_bytes = width * 3
            pixels = [
                bytes(rgb[i * row_bytes : (i + 1) * row_bytes]) for i in range(height)
            ]
        else:
            # Fallback or background present
            if lapimg is None:
                obs.script_log(
                    obs.LOG_INFO,
                    "Lap times image: using Python implementation (C extension not available)",
                )
            elif background_pixels and bg_width > 0 and bg_height > 0:
                obs.script_log(
                    obs.LOG_INFO,
                    "Lap times image: using fast C overlay on screenshot",
                )
            # Prepare overlay texts
            texts = []
            # Convert font_size to scale factor for C extension (C extension expects scale, not pixel size)
            c_scale = max(
                1, font_size // 24
            )  # 24px is base size (8*3), so scale accordingly
            obs.script_log(obs.LOG_INFO, "=== OVERLAY TEXT DEBUG ===")
            obs.script_log(
                obs.LOG_INFO,
                f"font_size={font_size}, c_scale={c_scale}, base_padding={base_padding}",
            )
            obs.script_log(
                obs.LOG_INFO,
                f"text_x={text_x}, current_y={current_y}, line_spacing={line_spacing}",
            )
            texts.append(
                (
                    text_x + base_padding,
                    current_y,
                    f"Track: {track_from_csv[:50]}",
                    (255, 255, 255),
                    c_scale,
                    base_padding,
                    (0, 0, 0, 220),
                )
            )
            current_y += line_spacing * 2
            for lap in lap_times:
                lap_text = f"Lap {lap['lap_number']}: {lap['time']}"
                color = _get_lap_color(
                    lap.get("seconds"),
                    lap["lap_number"],
                    best_times,
                    worst_times,
                    lap["is_final"],
                )
                texts.append(
                    (
                        text_x + base_padding,
                        current_y,
                        lap_text[:50],
                        color,
                        c_scale,
                        base_padding,
                        (0, 0, 0, 220),
                    )
                )
                current_y += line_spacing
            current_y += line_spacing
            total_color = _get_total_time_color(total_seconds, best_total, worst_total)
            texts.append(
                (
                    text_x + base_padding,
                    current_y,
                    f"Total: {total_time_str}",
                    total_color,
                    c_scale,
                    base_padding,
                    (0, 0, 0, 220),
                )
            )

            if (
                background_pixels
                and bg_width > 0
                and bg_height > 0
                and lapimg is not None
                and hasattr(lapimg, "draw_overlay_on_rgb")
            ):
                # Convert pixels list[bytes] to contiguous bytes
                rgb = b"".join(background_pixels)
                rgb2 = lapimg.draw_overlay_on_rgb(rgb, width, height, texts)
                row_bytes = width * 3
                pixels = [
                    bytes(rgb2[i * row_bytes : (i + 1) * row_bytes])
                    for i in range(height)
                ]
            else:
                # Python fallback
                if background_pixels and bg_width > 0 and bg_height > 0:
                    pixels = background_pixels
                else:
                    pixels = _create_png_image(width, height, bg_color=(30, 30, 30))
                # Draw using Python - convert from C extension format to Python format
                obs.script_log(obs.LOG_INFO, "=== PYTHON FALLBACK TEXT DEBUG ===")
                obs.script_log(
                    obs.LOG_INFO, f"font_size={font_size}, texts count={len(texts)}"
                )
                for entry in texts:
                    # entry format: (x, y, text, color, scale, padding, bg_color)
                    # _draw_text_with_background expects: (pixels, width, height, x, y, text, text_color, bg_color, scale, padding)
                    python_scale = (
                        font_size / 24.0
                    )  # Convert pixel size back to scale for Python renderer
                    obs.script_log(
                        obs.LOG_INFO,
                        f"  Drawing text: '{entry[2]}' at ({entry[0]}, {entry[1]}) with python_scale={python_scale:.2f}",
                    )
                    _draw_text_with_background(
                        pixels,
                        width,
                        height,
                        entry[0],  # x
                        entry[1],  # y
                        entry[2],  # text
                        entry[3],  # text_color
                        entry[6],  # bg_color (RGBA)
                        python_scale,  # scale
                        entry[5],  # padding
                    )

        # Generate output filename
        safe_track = make_filesystem_safe(track_from_csv)
        output_filename = f"Splits_{safe_track}_Run-{actual_run_number}.png"
        output_path = os.path.join(base_path, output_filename)

        # Save the image (prefer fast C saver)
        try:
            if lapimg is not None and hasattr(lapimg, "save_png"):
                rgb = b"".join(pixels)
                if lapimg.save_png(output_path, rgb, width, height):
                    obs.script_log(
                        obs.LOG_INFO,
                        f"Created lap times image (C saver): {output_filename}",
                    )
                else:
                    _save_png_file(pixels, width, height, output_path)
                    obs.script_log(
                        obs.LOG_INFO,
                        f"Created lap times image (Python saver): {output_filename}",
                    )
            else:
                _save_png_file(pixels, width, height, output_path)
                obs.script_log(
                    obs.LOG_INFO,
                    f"Created lap times image (Python saver): {output_filename}",
                )
        except Exception:
            _save_png_file(pixels, width, height, output_path)
            obs.script_log(
                obs.LOG_INFO,
                f"Created lap times image (Python saver fallback): {output_filename}",
            )

        return output_path

    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"Error creating lap times image: {e}")
        return None


###############################################################################
# Move Old Images functionality
###############################################################################


def _move_old_images(base_path, pattern="Lap-*.png", destination_subfolder="lap times"):
    """Move old image files matching pattern to a subfolder"""
    import glob

    if not os.path.exists(base_path):
        obs.script_log(obs.LOG_WARNING, f"Base path does not exist: {base_path}")
        return False

    # Create destination folder
    dest_folder = os.path.join(base_path, destination_subfolder)
    try:
        os.makedirs(dest_folder, exist_ok=True)
        obs.script_log(obs.LOG_INFO, f"Ensured directory exists: {dest_folder}")
    except Exception as e:
        obs.script_log(
            obs.LOG_WARNING, f"Failed to create directory {dest_folder}: {e}"
        )
        return False

    # Find files matching pattern
    search_pattern = os.path.join(base_path, pattern)
    files_to_move = glob.glob(search_pattern)

    if not files_to_move:
        obs.script_log(obs.LOG_INFO, f"No files found matching pattern: {pattern}")
        return True

    moved_count = 0
    failed_count = 0

    for file_path in files_to_move:
        try:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(dest_folder, filename)

            # Move the file
            if os.path.exists(dest_path):
                # If destination exists, try to remove it first
                try:
                    os.remove(dest_path)
                except Exception:
                    pass

            os.rename(file_path, dest_path)
            obs.script_log(obs.LOG_INFO, f"Moved {filename} to {destination_subfolder}")
            moved_count += 1

        except Exception as e:
            obs.script_log(
                obs.LOG_WARNING, f"Failed to move {os.path.basename(file_path)}: {e}"
            )
            failed_count += 1

    obs.script_log(
        obs.LOG_INFO,
        f"Move operation complete: {moved_count} moved, {failed_count} failed",
    )
    return failed_count == 0


###############################################################################
# Save Lap Time action definitions
###############################################################################


def get_save_action_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(
        props, "lap_time_var", "Lap Time Variable Name", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_text(
        props, "lap_number_var", "Lap Number Variable Name", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_text(
        props, "run_number_var", "Run Number Variable Name", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_text(
        props, "track_var", "Track Variable Name", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_text(
        props, "coins_var", "Coins Variable Name", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_text(
        props, "shrooms_var", "Shrooms Variable Name", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_bool(props, "is_final_lap", "Is Final Lap")
    obs.obs_properties_add_bool(
        props, "enable_auto_image", "Create Split Image after Final Lap"
    )
    return props


def get_save_action_defaults():
    defaults = obs.obs_data_create()
    obs.obs_data_set_default_string(defaults, "lap_time_var", "Current Lap Time OCR")
    obs.obs_data_set_default_string(defaults, "lap_number_var", "Current TT Lap")
    obs.obs_data_set_default_string(defaults, "run_number_var", "TT Run Number")
    obs.obs_data_set_default_string(defaults, "track_var", "Current Track")
    obs.obs_data_set_default_string(defaults, "coins_var", "CurrentCoins")
    obs.obs_data_set_default_string(defaults, "shrooms_var", "UsedShrooms")
    obs.obs_data_set_default_bool(defaults, "is_final_lap", False)
    obs.obs_data_set_default_bool(defaults, "enable_auto_image", True)
    return defaults


def run_action_save_lap(data, instance_id):
    try:
        # Get variable names from action settings
        lap_time_var = obs.obs_data_get_string(data, "lap_time_var")
        lap_number_var = obs.obs_data_get_string(data, "lap_number_var")
        run_number_var = obs.obs_data_get_string(data, "run_number_var")
        track_var = obs.obs_data_get_string(data, "track_var")
        coins_var = obs.obs_data_get_string(data, "coins_var")
        shrooms_var = obs.obs_data_get_string(data, "shrooms_var")
        is_final_lap = obs.obs_data_get_bool(data, "is_final_lap")
        enable_auto_image = obs.obs_data_get_bool(data, "enable_auto_image")

        # Get values from variables
        lap_time = advss_get_variable_value(lap_time_var)
        lap_number_str = advss_get_variable_value(lap_number_var)
        run_number_str = advss_get_variable_value(run_number_var)
        track = advss_get_variable_value(track_var)
        coins_str = advss_get_variable_value(coins_var)
        shrooms_str = advss_get_variable_value(shrooms_var)

        # Validate that all required variables exist
        if lap_time is None:
            obs.script_log(
                obs.LOG_WARNING, f"Lap time variable '{lap_time_var}' not found"
            )
            return False
        if lap_number_str is None:
            obs.script_log(
                obs.LOG_WARNING, f"Lap number variable '{lap_number_var}' not found"
            )
            return False
        if run_number_str is None:
            obs.script_log(
                obs.LOG_WARNING, f"Run number variable '{run_number_var}' not found"
            )
            return False
        if track is None:
            obs.script_log(obs.LOG_WARNING, f"Track variable '{track_var}' not found")
            return False

        # Convert string values to appropriate types
        lap_time = lap_time.strip()
        lap_number = int(lap_number_str.strip())
        run_number = int(run_number_str.strip())
        track = track.strip()
        coins = int(coins_str.strip()) if coins_str else 0
        shrooms = int(shrooms_str.strip()) if shrooms_str else 0

        _validate_inputs(
            lap_time, lap_number, is_final_lap, run_number, track, coins, shrooms
        )

        csv_path = _csv_file_path(g_base_path)
        if os.path.exists(csv_path) and _test_csv_locked(csv_path):
            obs.script_log(obs.LOG_INFO, "CSV is locked; queueing submission")
            # Normalize lap time before queueing
            normalized_lap_time = _normalize_laptime_format(lap_time)
            obs.script_log(
                obs.LOG_INFO,
                f"Queueing lap time: '{lap_time}' -> '{normalized_lap_time}'",
            )
            _add_to_queue(
                g_base_path,
                {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "LapTime": normalized_lap_time,
                    "LapNumber": int(lap_number),
                    "IsFinalLap": bool(is_final_lap),
                    "RunNumber": int(run_number),
                    "Track": track,
                    "Coins": int(coins),
                    "Shrooms": int(shrooms),
                    "EnableAutoImage": bool(enable_auto_image),
                },
            )
            return True

        # Try flushing queue first
        _flush_queue(g_base_path)

        # Save current submission
        _save_lap_to_csv(
            g_base_path,
            lap_time,
            lap_number,
            is_final_lap,
            run_number,
            track,
            coins,
            shrooms,
        )

        # If this is the final lap, create the lap times image (if enabled)
        if is_final_lap and enable_auto_image:
            try:
                _create_lap_times_image(g_base_path, run_number)
            except Exception as e:
                obs.script_log(
                    obs.LOG_WARNING, f"Failed to create lap times image: {e}"
                )

        return True
    except Exception as e:
        # Fallback to queue if CSV write fails
        obs.script_log(obs.LOG_WARNING, f"Saving to CSV failed, queueing instead: {e}")
        try:
            # Normalize lap time before queueing in fallback case too
            normalized_lap_time = _normalize_laptime_format(lap_time)
            obs.script_log(
                obs.LOG_INFO,
                f"Fallback queueing lap time: '{lap_time}' -> '{normalized_lap_time}'",
            )
            _add_to_queue(
                g_base_path,
                {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "LapTime": normalized_lap_time,
                    "LapNumber": lap_number,
                    "IsFinalLap": is_final_lap,
                    "RunNumber": run_number,
                    "Track": track,
                    "Coins": coins,
                    "Shrooms": shrooms,
                    "EnableAutoImage": enable_auto_image,
                },
            )
        except Exception as e2:
            obs.script_log(obs.LOG_WARNING, f"Failed to queue submission: {e2}")
        return False


###############################################################################
# Move Old Images action definitions
###############################################################################


def get_move_images_action_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(
        props, "file_pattern", "File Pattern", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_text(
        props, "destination_folder", "Destination Subfolder", obs.OBS_TEXT_DEFAULT
    )
    return props


def get_move_images_action_defaults():
    defaults = obs.obs_data_create()
    obs.obs_data_set_default_string(defaults, "file_pattern", "Lap-*.png")
    obs.obs_data_set_default_string(defaults, "destination_folder", "lap times")
    return defaults


def run_action_move_images(data, instance_id):
    try:
        file_pattern = obs.obs_data_get_string(data, "file_pattern").strip()
        destination_folder = obs.obs_data_get_string(data, "destination_folder").strip()

        # Use defaults if empty
        if not file_pattern:
            file_pattern = "Lap-*.png"
        if not destination_folder:
            destination_folder = "lap times"

        success = _move_old_images(g_base_path, file_pattern, destination_folder)
        return success

    except Exception as e:
        obs.script_log(obs.LOG_WARNING, f"Move images action failed: {e}")
        return False


###############################################################################
# Generate Lap Times Image action definitions
###############################################################################


def get_generate_image_action_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(
        props, "run_number_var", "Run Number Variable Name", obs.OBS_TEXT_DEFAULT
    )
    obs.obs_properties_add_text(
        props,
        "screenshot_path_var",
        "Screenshot Path Variable (optional)",
        obs.OBS_TEXT_DEFAULT,
    )
    return props


def get_generate_image_action_defaults():
    defaults = obs.obs_data_create()
    obs.obs_data_set_default_string(defaults, "run_number_var", "TT Run Number")
    obs.obs_data_set_default_string(defaults, "screenshot_path_var", "")
    return defaults


def run_action_generate_image(data, instance_id):
    try:
        # Get variable names from action settings
        run_number_var = obs.obs_data_get_string(data, "run_number_var")
        screenshot_path_var = obs.obs_data_get_string(data, "screenshot_path_var")

        # Get values from variables
        run_number_str = advss_get_variable_value(run_number_var)
        screenshot_path = (
            advss_get_variable_value(screenshot_path_var)
            if screenshot_path_var
            else None
        )

        # Validate that required variables exist
        if run_number_str is None:
            obs.script_log(
                obs.LOG_WARNING, f"Run number variable '{run_number_var}' not found"
            )
            return False

        # Convert string values to appropriate types
        run_number = int(run_number_str.strip())

        # Generate the image
        result = _create_lap_times_image(g_base_path, run_number, screenshot_path)

        if result:
            obs.script_log(
                obs.LOG_INFO,
                f"Successfully generated lap times image: {os.path.basename(result)}",
            )
            return True
        else:
            obs.script_log(obs.LOG_WARNING, "Failed to generate lap times image")
            return False

    except Exception as e:
        obs.script_log(obs.LOG_WARNING, f"Generate image action failed: {e}")
        return False
