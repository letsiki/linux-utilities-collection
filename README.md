# Linux Utilities Collection

A collection of Python-based command-line utilities for Linux system administration and file management. Each tool is designed to be standalone, portable, and follow Unix conventions.

## Tools Overview

### 1. filesize - File and Directory Size Reporter
**Purpose**: Reports file sizes and directory contents with optional verbose output

**Features**:
- Reports file sizes in bytes
- Counts files and directories within directories  
- Supports multiple paths as arguments
- Reads from stdin when no arguments provided
- Verbose mode shows absolute paths
- Proper exit codes for script integration

**Usage**:
```bash
filesize file1.txt /home/user/documents
filesize --verbose *.py
find . -name "*.txt" | ./filesize
```

**Installation**:
```bash
chmod +x filesize.py
ln -s $(pwd)/filesize.py ~/.local/bin/filesize
```

### 2. loganalyzer - Log Analysis Tool
**Purpose**: Analyzes log files to count and report log level occurrences

**Features**:
- Supports multiple log file formats with flexible regex pattern matching
- Counts log levels (INFO, WARNING, ERROR, DEBUG, etc.)
- Outputs in human-readable text or JSON format
- Directory expansion option to process all files in directories
- Binary file filtering to avoid processing non-text files
- Stdin support for pipeline integration
- File and console output options

**Usage**:
```bash
loganalyzer access.log error.log
loganalyzer --json --output report.json *.log
loganalyzer --expand-dir /var/log/
cat /var/log/apache2/access.log | ./loganalyzer
```

**Output Formats**:
- **Text**: Human-readable summary with totals and file list
- **JSON**: Structured data for integration with other tools

### 3. backup - Incremental Backup Manager
**Purpose**: Creates and manages compressed backups with incremental strategy

**Features**:
- **Incremental backups**: Only backs up new or modified files
- **Automatic strategy detection**: First backup is full, subsequent are incremental
- **Chain restoration**: Restores complete state by applying backup chain
- **Backup indexing**: JSON metadata tracking all backups
- **Multiple directory support**: Auto-splits into separate backup chains
- **Backup management**: List, restore, and remove backups
- **Proper logging**: Configurable verbosity levels

**Usage**:
```bash
# Create backups
backup create /home/user/documents /etc/config

# List all backups
backup list

# Restore specific backup
backup restore a1b2c3d4

# Remove backups
backup rm a1b2c3d4
backup rm --all a1b2c3d4  # Remove all backups for same directory

# Custom backup location
backup --output /media/backups create /home/user/docs
```

**Backup Strategy**:
- First backup of any directory is always full
- Subsequent backups are incremental (only changed files)
- Each directory gets its own backup chain
- Restoration applies full backup + all incrementals in chronological order

## Installation

### Prerequisites
- Python 3.8+ with standard library
- Linux/Unix environment
- Write permissions for backup locations

### Quick Install
```bash
# Clone or download the utilities
git clone git@github.com:letsiki/linux-utilities-collection.git
cd linux-utilities

# Make executable
chmod +x *.py

# Install to local bin
mkdir ~/.local
ln -s $(pwd)/filesize.py ~/.local/bin/filesize
ln -s $(pwd)/loganalyzer.py ~/.local/bin/loganalyzer  
ln -s $(pwd)/backup.py ~/.local/bin/backup

# Ensure ~/.local/bin is in PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Common Usage Patterns

### System Administration
```bash
# Analyze system logs
loganalyzer --expand-dir /var/log/ --json --output system-report.json

# Check disk usage of large directories
find /home -type d -size +1G | filesize --verbose

# Backup critical system configurations
backup create /etc /home/user/.config
```

### Development Workflow
```bash
# Monitor project directory sizes
filesize --verbose projects/*/

# Analyze application logs
loganalyzer --expand-dir app/logs/ --json

# Backup development projects
backup create ~/projects/important-app
```

### Automated Scripts
```bash
#!/bin/bash
# Daily backup script
backup --verbose create /home/user/documents 2>&1 | logger -t backup

# Log analysis cron job  
loganalyzer /var/log/app.log --json --output /tmp/daily-report.json
```

## Design Philosophy

These utilities follow Unix principles:

- **Do one thing well**: Each tool has a focused purpose
- **Work together**: Tools can be piped and combined
- **Text interfaces**: Clean command-line interfaces with standard options
- **Robust error handling**: Proper exit codes and error messages
- **Configuration through arguments**: No hidden config files
- **Portable**: Pure Python with only standard library dependencies

## Technical Details

### Error Handling
- Non-zero exit codes on errors for script integration
- Graceful handling of missing files, permission errors
- Partial operation support (continue on individual file errors)
