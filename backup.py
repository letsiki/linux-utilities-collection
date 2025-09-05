#! /usr/bin/env python3

"""
Backup Utility
"""

import argparse
import pathlib
from pathlib import Path
import shutil
from  datetime import datetime, timezone as Tz, timedelta
import json
import  time
import zipfile
import logging

DEFAULT_OUTOUT_DIR = Path().home() / ".backup"

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Raw formatter makes sure module docstring format (new lines in particular) is preserved
parser = argparse.ArgumentParser(__name__, add_help=True, 
                                 description=__doc__, 
                                 formatter_class=argparse.RawDescriptionHelpFormatter
                                 )

# ---------------------- ADD SUBCOMMANDS ---------------------- #

subcommands = parser.add_subparsers(dest="command")

create_command = subcommands.add_parser("create", help="create backups")
list_command = subcommands.add_parser("list", help="list backups")
restore_command = subcommands.add_parser("restore", help="restore backups")

# ----------------------- MAIN COMMAND ------------------------ #

parser.add_argument("-v", "--verbose", action="store_true", help="turn verbose output on")
parser.add_argument("-o", "--output", default=DEFAULT_OUTOUT_DIR, help=f"set output  directory, default: {DEFAULT_OUTOUT_DIR}")

# --------------------- CREATE SUBCOMMAND --------------------- #

# Positional arguments have their dest equal to their name automatically. Explicitly setting dest will raise error
create_command.add_argument("create_dir_path", nargs="+", help="provide one or  more directories to be backed up")

# --------------------- LIST SUBCOMMAND --------------------- #

# Positional arguments have their dest equal to their name automatically. Explicitly setting dest will raise error
#

class Metadata:
    def __init__(self, meta_dir: Path):
        self._meta_dir = meta_dir.absolute()
        self._entries: list[MetaEntry] =  []
        try:
            with open(self._meta_dir / ".meta.json") as f:
                entries: list[dict] = json.load(f)
        except FileNotFoundError as e:
            Path(self._meta_dir).mkdir(exist_ok=True, parents=True)
            with open(self._meta_dir / ".meta.json", "w") as f:
                f.write("[]")
            return
        for entry in entries:
            self._entries.append(MetaEntry(entry))

    def get_backup_chain(self, bak_dir: Path):
        # sort all backup entries of a given directory chronologically
        return sorted(filter(lambda x: getattr(x, "_path") == bak_dir, self._entries), key=lambda x: getattr(x, "_timestamp"))

    def get_last_backup_ts(self, bak_dir: Path) -> int:
        if (bak_chain := self.get_backup_chain(bak_dir)):
            return getattr(bak_chain[-1], "_timestamp")
        return 0

    def get_all_file_paths(self, bak_dir: Path) -> list[Path]:
        return [file for file in bak_dir.rglob("*") if file.is_file()]

    def filter_updated_paths(self, bak_dir: Path):
        last_ts = self.get_last_backup_ts(bak_dir)
        current_files = self.get_all_file_paths(bak_dir)
        return list(filter(lambda x: x.stat().st_mtime > last_ts, current_files))
    
    @staticmethod
    def compress(filepaths: list[Path], zip_filepath: Path, bak_dir: Path):
        with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            for filepath in filepaths:
                rel_path = filepath.relative_to(bak_dir)
                zipf.write(filepath, rel_path)
    
    def backup(self, bak_dir: Path):
        """
        this is our public interface for backing up a folder
        the function makes sure the folder path is converted to absolute before
        getting passed to internal functions
        """
        bak_dir = bak_dir.absolute()
        files = self.filter_updated_paths(bak_dir)
        if files:
            meta_entry = self.create_meta_entry(bak_dir, len(files))
            self.compress(files, self._meta_dir / (str(meta_entry) + ".zip"), bak_dir)
            self._entries.append(meta_entry)
            self._to_json()
        else:
            logging.info("No files have been added or updated, exiting")

    def _to_json(self):
        with open(self._meta_dir / ".meta.json", "w") as f:
            json.dump([meta_entry.to_dict() for meta_entry in self._entries], f)

    def create_meta_entry(self, bak_dir: Path, file_count):
        data = {
            "path": bak_dir,
            "timestamp": time.time(),
            "file_count": file_count
        }
        return MetaEntry(data)
    
    def format_backup_list(self):
        # meta_header_lines = [
        #     f"Backup Directory: {self._meta_dir}",
        #     f"Total Backups: {len(self._entries)}",
        #     ""
        # ]
        if not self._entries:
            return "No backups found"
        
        # Define column widths
        id_width = 10
        dir_width = 60
        date_width = 20
        
        # Header
        header = f"{'BACKUP ID':<{id_width}} {'DIRECTORY':<{dir_width}} {'DATE':<{date_width}}"
        separator = "-" * (id_width + dir_width + date_width + 2)
        
        lines = [header, separator]
        
        # Data rows
        for entry in self._entries:
            backup_id = entry.id_
            directory = str(entry._path)
            date_str = entry.datetime
            
            # Truncate if too long
            if len(directory) > dir_width:
                directory =  "..." + directory[-dir_width+3:]
                
            row = f"{backup_id:<{id_width}} {directory:<{dir_width}} {date_str:<{date_width}}"
            lines.append(row)
        
        return "\n".join(lines)
    
class MetaEntry:
    def __init__(self, data: dict):
        # json stores Path as string, need to convert back
        self._path = Path(data["path"])
        self._timestamp = data["timestamp"]
        self._file_count = data["file_count"]

    @property
    def id_(self):
        return hex(hash(self))[2:10]  
    
    @property
    def datetime(self):
        return datetime.strftime(datetime.fromtimestamp(self._timestamp), "'%Y-%m-%d %H:%M:%S'")[1:-1]

    def __hash__(self):
        return abs(hash((self._timestamp, str(self._path))))
    
    def __str__(self):
        return f"{self._path.stem}_{self._timestamp}"
    
    def to_dict(self):
        return {
            # need(?) to convert to string prior to storing to json
            "path": str(self._path),
            "timestamp": self._timestamp,
            "file_count": self._file_count
        }

if __name__ == "__main__":
    args = parser.parse_args()
    setup_logging(args.verbose)
    output_dir = Path(args.output)
    if args.command == "create":    
        metadata = Metadata(output_dir)

        for source_path in args.create_dir_path:
            bak_dir = Path(source_path)
            metadata.backup(bak_dir)
    elif args.command == "list":
        metadata = Metadata(output_dir)
        print(metadata.format_backup_list())

# BUG:
#   It does work but not incrementally
#   Fixed: When Loading from JSON we need to convert back to Path

#  TODO
#   Implement restore
#   zipfile extractall will overwrite automatically

