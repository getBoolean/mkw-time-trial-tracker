import obspython as obs

# Required by advss helpers
import threading
from typing import NamedTuple
import os
import json
import time
import csv

action_name = "MKW Track"

# New action for saving lap times
save_action_name = "MKW Save Lap"

# New action for moving old images
move_images_action_name = "MKW Move Old Images"

# Script-level settings (updated via script_update)
g_base_path = os.path.join("G:", "OBS", "Mario Kart World", "time trials")
g_repo_path = ""


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


def script_unload():
    global action_name
    advss_deregister_action(action_name)
    advss_deregister_action(save_action_name)
    advss_deregister_action(move_images_action_name)


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

    # Build new row
    new_row = {
        "Timestamp": now_ts,
        "RunNumber": str(int(run_number)),
        "LapNumber": str(int(lap_number)),
        "Time": last_lap_time if last_lap_time else str(lap_time),
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
            _save_lap_to_csv(
                base_path,
                str(it.get("LapTime", "")).strip(),
                int(it.get("LapNumber", 0)),
                bool(it.get("IsFinalLap", False)),
                int(it.get("RunNumber", 0)),
                it.get("Track", ""),
                int(it.get("Coins", 0)),
                int(it.get("Shrooms", 0)),
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
            _add_to_queue(
                g_base_path,
                {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "LapTime": lap_time,
                    "LapNumber": int(lap_number),
                    "IsFinalLap": bool(is_final_lap),
                    "RunNumber": int(run_number),
                    "Track": track,
                    "Coins": int(coins),
                    "Shrooms": int(shrooms),
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
        return True
    except Exception as e:
        # Fallback to queue if CSV write fails
        obs.script_log(obs.LOG_WARNING, f"Saving to CSV failed, queueing instead: {e}")
        try:
            _add_to_queue(
                g_base_path,
                {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "LapTime": lap_time,
                    "LapNumber": lap_number,
                    "IsFinalLap": is_final_lap,
                    "RunNumber": run_number,
                    "Track": track,
                    "Coins": coins,
                    "Shrooms": shrooms,
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
