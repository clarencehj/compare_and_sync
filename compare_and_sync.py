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

def update_metadata(src, dst, verbose=False):
    """Apply permissions and ownership from src to dst."""
    stat_info = os.stat(src)
    try:
        os.chown(dst, stat_info.st_uid, stat_info.st_gid)
    except PermissionError:
        print(f"Warning: Cannot change owner/group for {dst} (requires root).")
    os.chmod(dst, stat_info.st_mode)
    if verbose:
        owner = pwd.getpwuid(stat_info.st_uid).pw_name
        group = grp.getgrgid(stat_info.st_gid).gr_name
        mode = oct(stat_info.st_mode & 0o777)
        print(f"Applied metadata to {dst} → owner={owner}, group={group}, mode={mode}")

def copy_with_metadata(src, dst, is_dir=False, verbose=False):
    """Copy file or directory and apply source metadata."""
    if is_dir:
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    update_metadata(src, dst, verbose)

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
    for root, dirs, files in os.walk(old_dir):
        for entry in dirs + files:
            old_path = os.path.join(root, entry)
            rel_path = os.path.relpath(old_path, old_dir)
            new_path = os.path.join(new_dir, rel_path)

            if not os.path.exists(new_path):
                yield rel_path, 'missing', old_path, new_path
            else:
                yield rel_path, 'exists', old_path, new_path

def select_items_with_curses(choices):
    selected = set()

    def menu(stdscr):
        curses.curs_set(0)
        pos = 0

        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            max_visible = height - 2
            if len(choices) > max_visible:
                stdscr.addstr(0, 0, f"Terminal too small ({height} rows). Resize or reduce files.")
                stdscr.getch()
                return []

            stdscr.addstr(0, 0, "Select missing items to copy (SPACE to toggle, ENTER to confirm):")
            for i, choice in enumerate(choices):
                if i >= max_visible:
                    break
                prefix = "[x]" if choice in selected else "[ ]"
                line = f"> {prefix} {choice}" if i == pos else f"  {prefix} {choice}"
                try:
                    stdscr.addstr(i + 1, 0, line, curses.A_REVERSE if i == pos else 0)
                except curses.error:
                    pass
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
    parser = argparse.ArgumentParser(description='Compare and sync user-specific files and directories between Tomcat installations.')
    parser.add_argument('old_dir', help='Path to original/old Tomcat installation')
    parser.add_argument('new_dir', help='Path to new/destination Tomcat installation')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    args = parser.parse_args()
    verbose = args.verbose

    if not os.path.isdir(args.old_dir):
        print(f"Error: Source directory '{args.old_dir}' does not exist.")
        exit(1)
    if not os.path.isdir(args.new_dir):
        print(f"Error: Destination directory '{args.new_dir}' does not exist.")
        exit(1)

    copied = 0
    updated = 0
    missing_items = []

    for rel_path, status, old_path, new_path in compare_dirs(args.old_dir, args.new_dir):
        is_dir = os.path.isdir(old_path)
        if status == 'missing':
            missing_items.append((rel_path, old_path, new_path, is_dir))
        else:
            update_metadata(old_path, new_path, verbose=verbose)
            updated += 1

            # Only diff files inside conf/
            if not is_dir and (rel_path.startswith("conf" + os.sep) or os.sep + "conf" + os.sep in old_path):
                old_lines = read_file_lines(old_path)
                new_lines = read_file_lines(new_path)
                diff = list(difflib.unified_diff(
                    old_lines, new_lines,
                    fromfile=f"{rel_path} (old)",
                    tofile=f"{rel_path} (new)",
                    lineterm=''
                ))
                if diff:
                    if verbose:
                        print(f"\nChanges in {rel_path}:\n" + "".join(diff))
                    log_diff(rel_path, diff)

    if missing_items:
        print("\nMissing items detected.")
        choices = [f[0] for f in missing_items]
        selected = select_items_with_curses(choices)

        for rel_path, old_path, new_path, is_dir in missing_items:
            if rel_path in selected:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                copy_with_metadata(old_path, new_path, is_dir=is_dir, verbose=verbose)
                copied += 1

    print(f"\nSummary:")
    print(f"  Items copied (new):              {copied}")
    print(f"  Items updated (metadata only):   {updated}")

    if updated > 0:
        print(f"\nSee diff details in: {LOGFILE}")

if __name__ == '__main__':
    main()

