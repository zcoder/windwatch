#!/usr/bin/env python3


import subprocess
import time
from datetime import datetime, timedelta
import pytz
import logging
import json
import argparse
from typing import Optional, Union
from collections import defaultdict
import sys
import re
import os
import pwd

Debug = 0
REAL_TERMINATE=0


def load_config(config_path):
    with open(config_path, 'r') as config_file:
        return json.load(config_file)


def detect_display(username: Optional[str] = None, config_display: Optional[str] = None, default_display: str = ':0'):
    try:
        # Выполняем команду `who -s` и парсим результат
        who_output = subprocess.check_output(['who', '-s'], text=True).strip().splitlines()
        for line in who_output:
            parts = line.split()
            if len(parts) >= 3 and parts[1].startswith(':'):
                if username is not None and parts[0] != username:
                    continue
                if config_display is None:
                    return parts[1]
                if config_display is not None and parts[1] != config_display:
                    continue
                return config_display
        else:
            return default_display
    except Exception as e:
        print(f"Failed to detect DISPLAY: {e}")



def compile_patterns(settings):
    compiled_patterns = {}
    for key, value in settings.items():
        try:
            # Попытка компиляции ключа как регулярного выражения
            pattern = re.compile(key)
            compiled_patterns[pattern] = value
        except re.error:
            # Если ключ не является корректным регулярным выражением, используем как строку
            compiled_patterns[re.compile(re.escape(key))] = value
    return compiled_patterns


def find_window_setting(win_name, short_win_name, patterns):
    matched_keys_win_name = []
    matched_keys_short = []

    for pattern in patterns:
        if pattern.match(win_name):
            matched_keys_win_name.append(pattern)
        elif pattern.match(short_win_name):
            matched_keys_short.append(pattern)
        for matches in (matched_keys_win_name, matched_keys_short):
            if len(matches) > 1:
                raise ValueError(
                    f"Multiple matches found for window '{win_name}' and short name '{short_win_name}': {matches}")

    for matches in (matched_keys_win_name, matched_keys_short):
        if len(matches) == 1:
            print(f'Window settings found for window {win_name=} {short_win_name=}. {matches[0]=}')
            return matches[0]

    if Debug: print(f'No settings found for window {win_name=} {short_win_name=}.')
    return None


def get_active_window_wid():
    try:
        result = subprocess.run(['xdotool', 'getactivewindow'], stdout=subprocess.PIPE, check=True)
        return int(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting active window: {e}")
        return None


def get_fields_from_window_ids(window_ids, required_fields: list) -> defaultdict:
    _required_fields = dict.fromkeys(required_fields)
    _required_fields['_NET_WM_PID'] = None
    result_dict = defaultdict(dict)

    for window_id in window_ids:
        result = subprocess.run(['xprop', '-notype', '-id', str(window_id), *list(_required_fields.keys())],
                                stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8').strip()

        for line in output.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key == '_NET_WM_PID':
                    result_dict[window_id][key] = int(value)
                elif key == 'WM_CLASS':
                    value = value.split(',')
                    result_dict[window_id][key] = [v.strip().strip('"') for v in value]
                else:
                    value = value.strip()
                    result_dict[window_id][key] = value.strip().strip('"')
    return result_dict


def close_application(window_pid, comment: Optional[str] = None) -> None:
    if window_pid and isinstance(window_pid, int) and window_pid > 1000:
        if (REAL_TERMINATE):
            subprocess.run(['kill', str(window_pid)], check=True)
        if Debug: print(f"[Debug] Process with PID {window_pid} has been terminated (actually not). {comment=}")
    else:
        if Debug: print(f"Wrong window PID {window_pid}.")


def log_activity(*, start_time: datetime, current_time: datetime, last_active_window: datetime, duration: int, wid: int,
                 window_pid: str, window_name: str, window_class: list[str], window_machine: str,
                 short_current_window: str) -> None:
    log_entry = {
        "start_time_human": start_time.isoformat(),
        "start_time_unix": start_time.timestamp(),
        "current_time_human": current_time.isoformat(),
        "current_time_unix": current_time.timestamp(),
        "last_active_window_human": last_active_window.isoformat(),
        "last_active_window_unix": last_active_window.timestamp(),
        "active_seconds": duration,
        'wid': wid,
        'window_pid': window_pid,
        "window_name": window_name,
        'window_class': window_class,
        'window_machine': window_machine,
        "short_current_window": short_current_window,
    }
    logging.info(json.dumps(log_entry))


def switch_user(user: Union[str, int]):
    try:
        if isinstance(user, int):
            user_info = pwd.getpwuid(user)
        elif isinstance(user, str):
            user_info = pwd.getpwnam(user)
        else:
            raise ValueError("USER must be a string(username) or an integer(uid).")
        if os.geteuid() == 0:  # Только если скрипт запущен от имени root
            os.setgid(user_info.pw_gid)
            os.setuid(user_info.pw_uid)
            os.environ['HOME'] = user_info.pw_dir
            os.environ['USER'] = user_info.pw_name
        return user_info.pw_name
    except KeyError:
        print(f"USER {user} does not exist.")


def load_app_config(config):
    win_config = config.get('WINDOWS_SETTINGS', {})
    return compile_patterns(win_config)


def main(config_path: str):
    config = load_config(config_path)
    log_fname = config.get('LOG_FILE')

    if log_fname is not None:
        _handlers = [logging.FileHandler(log_fname)]
    else:
        _handlers = [logging.StreamHandler()]

    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=_handlers
    )

    user = config.get('USER', 1000)
    username = switch_user(user)

    os.environ['DISPLAY'] = detect_display(username=username, config_display=config.get('DISPLAY', None), default_display=config.get('DISPLAY', ':0'))

    check_interval = int(config.get('CHECK_INTERVAL', 1))
    records_ttl_check_interval = int(config.get('RECORDS_TTL_CHECK_INTERVAL', 300))
    ttl = timedelta(seconds=config.get('RECORDS_TTL', 86400))
    global Debug
    Debug = config.get('DEBUG', 1)
    global REAL_TERMINATE
    REAL_TERMINATE = config.get('REAL_TERMINATE', 0)

    wids_map = {}
    active_windows = {}
    last_active = {}
    win_settings = {}
    last_ttl_check = None

    patterns_appconfig = load_app_config(load_config(config_path))

    while True:
        current_time = datetime.now(tz=pytz.utc)
        last_ttl_check = current_time if last_ttl_check is None else last_ttl_check

        current_window__wid = get_active_window_wid()
        if current_window__wid is not None:

            _all_wids_fields = get_fields_from_window_ids([current_window__wid],
                                                          ['WM_CLASS', '_NET_WM_PID', '_NET_WM_NAME', 'WM_CLIENT_MACHINE'])
            _fields = _all_wids_fields.get(current_window__wid, {})

            _win_class = _fields.get('WM_CLASS')
            _win_pid = _fields.get('_NET_WM_PID')
            _win_name = _fields.get('_NET_WM_NAME')
            _win_machine = _fields.get('WM_CLIENT_MACHINE')

            if _win_pid is None:
                if Debug: print(
                    f"No PID found for window {current_window__wid=} {_win_name=} {_win_class=} on machine {_win_machine=}.")

            short_current_window = _win_class[0] if _win_class else ""

            tmp_win_key = f"{current_window__wid}__{_win_pid}__{_win_name}"
            if tmp_win_key not in wids_map:
                settings_key = find_window_setting(_win_name, short_current_window, patterns_appconfig)
                if settings_key is not None:
                    wids_map[tmp_win_key] = settings_key
                    win_key = settings_key
                    win_settings[win_key] = patterns_appconfig.get(settings_key)
                else:
                    win_key = tmp_win_key
            else:
                win_key = wids_map[tmp_win_key]

            last_active_window_time = last_active.get(win_key, None)

            if last_active_window_time is None or (
                    current_time - last_active_window_time).total_seconds() > 1.5:  # focus changed or new window
                active_windows[win_key] = current_time
                if Debug: print(
                    f'Window {win_key=} {_win_class=} activated. Time: {active_windows[win_key].strftime("%Y-%m-%d %H:%M:%S")}')
            if True:
                duration = int((current_time - active_windows[win_key]).total_seconds())
                last_active[win_key] = current_time
                log_activity(**{
                    'start_time': active_windows[win_key],
                    'current_time': current_time,
                    'last_active_window': last_active_window_time if last_active_window_time is not None else current_time,
                    'duration': duration,
                    'wid': current_window__wid,
                    'window_pid': _win_pid,
                    'window_name': _win_name,
                    'window_class': _win_class,
                    'window_machine': _win_machine,
                    'short_current_window': short_current_window
                })

                # Получаем время до завершения для текущего окна
                active_win_settings = win_settings.get(win_key)
                if active_win_settings is not None:
                    _timeout_seconds = int(active_win_settings)
                    if Debug: print(
                        f"Window {win_key=} {_win_class=} {active_win_settings=}, {duration=} {_timeout_seconds=}")
                    if _timeout_seconds != -1 and duration > _timeout_seconds:
                        if _win_pid:
                            close_application(_win_pid, comment=_win_name)
                        else:
                            raise ValueError(f"No PID found for window {_win_name=} {short_current_window=}")
                        for _run_dict in [active_windows, last_active, wids_map]:
                            if win_key in _run_dict: del _run_dict[win_key]

            if (current_time - last_ttl_check).total_seconds() > records_ttl_check_interval:
                last_ttl_check = current_time
                windows_to_remove = [window for window, last_time in last_active.items() if
                                     (current_time - last_time) > ttl]
                for window in windows_to_remove:
                    if Debug: print(f"Removing inactive window '{window}' due to TTL expiration.")
                    for _run_dict in [active_windows, last_active, wids_map]:
                        if win_key in _run_dict: del _run_dict[window]

                # reload app config
                print(f"Reloading app config...")
                patterns_appconfig = load_app_config(load_config(config_path))

        time.sleep(check_interval)


def run():
    def_conf_fname = '/etc/windwatch/windwatch.json'

    try:
        ipython_env = get_ipython()
    except NameError:
        ipython_env = None

    if ipython_env is None: # prog="WindWatch",
        parser = argparse.ArgumentParser(description="WindWatch. A tool for monitoring and managing active windows, and help prevent wind inside mind (~.~)")
        parser.add_argument('--config', default=def_conf_fname, type=str, help='Path to the config file')

        args = parser.parse_args()
        config_path = args.config
    else:
        config_path = def_conf_fname

    main(config_path)


# Run the main function if this script is being run directly.
if __name__ == "__main__":
    run()
