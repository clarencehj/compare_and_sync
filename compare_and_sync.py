#!/usr/bin/env python3

import os
import shutil
import stat
import argparse
import filecmp
import pwd
import grp
import difflib
from datetime import datetime
import curses

LOGFILE = f"tomcat_conf_diff_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def copy_with_metadata(src, dst):
    shutil.copy2(src, dst)
    stat_info = os.stat(src)
    os.chown(dst, stat_info.st_uid, stat_info.st_gid)
    os.chmod(dst, stat_info.st_mode)

def get_owner_group(path):
    stat_info = os.stat(path)
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    return pwd.getpwuid(uid).pw_name, grp.getgrgid(gid).gr_name

def read_file_lines(path):
    try:
        with open(path, 'r') as f:
            return f.readlines()
    except Exception:
        return []

def log_diff(path, diff_lines):
    with open(LOGFILE, 'a') as log:
        log.write(f"\n--- {path} (old)\n+++ {path} (new)\n")
        log.writelines(diff_lines)

def compare_dirs(old_dir, new_dir):
    for root, _, files in os.walk(old_dir):
        for fname in files:
            old_path = os.path.join(root, fname)
            rel_path = os.path.relpath(old_path, old_dir)
            new_path = os.path.join(new_dir, rel_path)

            if not os.path.exists(new_path):
                yield rel_path, 'missing', old_path, new_path
            elif not filecmp.cmp(old_path, new_path, shallow=False):
                yield rel_path, 'different', old_path, new_path

def select_items_with_curses(choices):
    selected = set()

    def menu(stdscr):
        curses.curs_set(0)
        pos = 0

        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, "Select missing files to copy (SPACE to toggle, ENTER to confirm):")
            for i, choice in enumerate(choices):
                prefix = "[x]" if choice in selected else "[ ]"
                if i == pos:
                    stdscr.addstr(i + 1, 0, f"> {prefix} {choice}", curses.A_REVERSE)
                else:
                    stdscr.addstr(i + 1, 0, f"  {prefix} {choice}")
            key = stdscr.getch()

            if key in [curses.KEY_UP, ord('k')]:
                pos = (pos - 1) % len(choices)
            elif key in [curses.KEY_DOWN, ord('j')]:
                pos = (pos + 1) % len(choices)
            elif key in [ord(' '), ord('\t')]:
                choice = choices[pos]
                if choice in selected:
                    selected.remove(choice)
                else:
                    selected.add(choice)
            elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
                break

    curses.wrapper(menu)
    return list(selected)

def main():
    parser = argparse.ArgumentParser(description='Compare and sync user-specific files between Tomcat installations.')
    parser.add_argument('old_dir', help='Path to original/old Tomcat installation')
    parser.add_argument('new_dir', help='Path to new/destination Tomcat installation')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    args = parser.parse_args()
    verbose = args.verbose

    copied = 0
    updated = 0
    missing_files = []

    for rel_path, status, old_path, new_path in compare_dirs(args.old_dir, args.new_dir):
        if status == 'missing':
            missing_files.append((rel_path, old_path, new_path))
        elif status == 'different':
            if rel_path.startswith("conf" + os.sep) or os.sep + "conf" + os.sep in old_path:
                old_lines = read_file_lines(old_path)
                new_lines = read_file_lines(new_path)
                diff = list(difflib.unified_diff(old_lines, new_lines,
                                                 fromfile=f"{rel_path} (old)",
                                                 tofile=f"{rel_path} (new)",
                                                 lineterm=''))
                if diff:
                    if verbose:
                        print(f"\nChanges in {rel_path}:\n" + "".join(diff))
                    log_diff(rel_path, diff)

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            copy_with_metadata(old_path, new_path)
            updated += 1
            if verbose:
                owner, group = get_owner_group(old_path)
                mode = oct(os.stat(old_path).st_mode & 0o777)
                print(f"Overwritten {rel_path} with owner={owner}, group={group}, mode={mode}")

    # Prompt user for missing files to copy
    if missing_files:
        print("\nMissing files detected.")
        choices = [f[0] for f in missing_files]
        selected = select_items_with_curses(choices)

        for rel_path, old_path, new_path in missing_files:
            if rel_path in selected:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                copy_with_metadata(old_path, new_path)
                copied += 1
                if verbose:
                    owner, group = get_owner_group(old_path)
                    mode = oct(os.stat(old_path).st_mode & 0o777)
                    print(f"Copied {rel_path} with owner={owner}, group={group}, mode={mode}")

    print(f"\nSummary:")
    print(f"  Files copied (new):   {copied}")
    print(f"  Files updated (diff): {updated}")

    if updated > 0:
        print(f"\nSee diff details in: {LOGFILE}")

if __name__ == '__main__':
    main()

