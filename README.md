# Tomcat Directory Compare and Sync Tool

This tool helps you compare and synchronize user-specific files between two Apache Tomcat installations — typically during an upgrade. It ensures file permissions, ownership, and content are preserved when needed, and highlights differences in configuration files for review.

## Features

- Compares old and new Tomcat directories.
- Copies missing files (with interactive selection).
- Overwrites differing files and preserves metadata.
- Logs all changes to configuration files (conf directory).
- Displays summary statistics of copied/updated files.
- Scrollable file selector with arrow keys and spacebar (no external dependencies).
- Quiet by default, verbose mode available.

## Requirements

- Python 3.6+
- Works without external libraries (uses standard Python modules).
- Terminal that supports curses (most Unix-based systems).

## Installation

Clone the repository:

    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    chmod +x compare_and_sync.py

## Usage

    ./compare_and_sync.py <OLD_TOMCAT_DIR> <NEW_TOMCAT_DIR> [--verbose]

Example:

    ./compare_and_sync.py apache-tomcat-9.0.69 apache-tomcat-9.0.105 --verbose

- Arrow keys (↑ ↓): Navigate file list
- Space: Select/deselect files to copy
- Enter: Start copy process

## Output

- Summary of copied and updated files
- Diff log saved to a file like: tomcat_conf_diff_log_YYYYMMDD_HHMMSS.txt

## License

MIT

