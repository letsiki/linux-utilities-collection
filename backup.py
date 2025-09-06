#! /usr/bin/env python3

"""
Backup Utility
- Compresses directories to zip format
- Proper listing of all backup metadata and history stored in json
- Default .backup folder
- May restore any backup older backup
- Uses incremental backup strategy:
    - Only backups up new files, does not delete anything
    - Restores backup files, overwriting existing ones, but without deleting local files not found in the backup chain
"""

import argparse
from pathlib import Path
from datetime import datetime, timezone
import json
import time
import zipfile
import logging

DEFAULT_OUTOUT_DIR = Path().home() / ".backup"


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# Raw formatter makes sure module docstring format (new lines in particular) is preserved
parser = argparse.ArgumentParser(
    "backup",
    add_help=True,
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)

# ---------------------- ADD SUBCOMMANDS ---------------------- #

subcommands = parser.add_subparsers(dest="command")

create_command = subcommands.add_parser("create", help="create backups")
list_command = subcommands.add_parser("list", help="list backups")
restore_command = subcommands.add_parser("restore", help="restore backups")
remove_command = subcommands.add_parser("rm", help="remove backups")

# ----------------------- MAIN COMMAND ------------------------ #
parser.add_argument(
    "-v", "--verbose", action="store_true", help="turn verbose output on"
)
parser.add_argument(
    "-o",
    "--output",
    default=DEFAULT_OUTOUT_DIR,
    help=f"set output  directory, default: {DEFAULT_OUTOUT_DIR}",
)

# --------------------- CREATE SUBCOMMAND --------------------- #

# Positional arguments have their dest equal to their name automatically. Explicitly setting dest will raise error
create_command.add_argument(
    "create_dir_paths",
    nargs="+",
    help="provide one or  more directories to be backed up",
)

# --------------------- RESTORE SUBCOMMAND --------------------- #
restore_command.add_argument(
    "restore_bak_ids",
    nargs="+",
    help="provide one or  more backup id's to be restored",
)

# --------------------- REMOVE SUBCOMMAND --------------------- #
remove_command.add_argument(
    "rm_bak_ids",
    nargs="+",
    help="provide one or  more backup id's to be removed",
)
remove_command.add_argument(
    "-a",
    "--all",
    dest="rm_all",
    action="store_true",
    help="remove all backups of the directory",
)
# Positional arguments have their dest equal to their name automatically. Explicitly setting dest will raise error
#


class MetaEntry:
    def __init__(self, data: dict):
        # json stores Path as string, need to convert back
        self._path = Path(data["path"])
        self._timestamp: int = data["timestamp"]
        self._file_count: int = data["file_count"]
        # We need to explicitly repr as the print and logging modules use str by default
        logging.debug(f"created {repr(self)}")

    @property
    def id_(self):
        return hex(hash(self))[2:10]

    @property
    def datetime(self):
        return datetime.strftime(
            datetime.fromtimestamp(self._timestamp), "'%Y-%m-%d %H:%M:%S'"
        )[1:-1]

    def __hash__(self):
        return abs(hash(self._timestamp))

    def __repr__(self):
        return f"{self.__class__.__qualname__}('{self._path}', {self._timestamp}, {self._file_count})"

    def __str__(self):
        "String representation of the meta entry. Can be used as a filename"
        return f"{self._path.stem}_{self._timestamp}"

    def __eq__(self, other: object) -> bool:
        """
        Not currently  utilized. Was initially build for the rm subcommand
        """
        if not isinstance(other, MetaEntry):
            return NotImplemented
        return self.id_ == other.id_

    def to_dict(self):
        return {
            # need(?) to convert to string prior to storing to json
            "path": str(self._path),
            "timestamp": self._timestamp,
            "file_count": self._file_count,
        }


class Metadata:
    def __init__(self, meta_dir: Path):
        self._meta_dir = meta_dir.absolute()
        self._entries: list[MetaEntry] = []
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

    def _get_backup_chain(self, bak_dir: Path):
        # sort all backup entries of a given directory chronologically
        bak_chain = sorted(
            filter(lambda x: getattr(x, "_path") == bak_dir, self._entries),
            key=lambda x: getattr(x, "_timestamp"),
        )
        if bak_chain:
            logging.info(f"got back up chain for dir {bak_dir}")
            # MetaEntries are nested inside the bakchain list therefore
            # MetaEntry.__repr__ will be used despite calling the logging module
            # The logging module only affects the higher level element
            logging.info(bak_chain)
        return bak_chain

    def _get_last_backup_ts(self, bak_dir: Path) -> int:
        if bak_chain := self._get_backup_chain(bak_dir):
            return getattr(bak_chain[-1], "_timestamp")
        return 0

    def _get_all_file_paths(self, bak_dir: Path) -> list[Path]:
        """retrieve all non-dir filepaths from scanning a dir recursively"""
        return [file for file in bak_dir.rglob("*") if file.is_file()]

    def _filter_updated_paths(self, bak_dir: Path):
        """filters in all file paths that are new or updated"""
        last_ts = self._get_last_backup_ts(bak_dir)
        current_files = self._get_all_file_paths(bak_dir)
        return list(filter(lambda x: x.stat().st_mtime > last_ts, current_files))

    @staticmethod
    def _compress(filepaths: list[Path], zip_filepath: Path, bak_dir: Path):
        with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            for filepath in filepaths:
                rel_path = filepath.relative_to(bak_dir)
                zipf.write(filepath, rel_path)

    def backup(self, bak_dirs: list[Path]):
        """
        this is our public interface for backing up  folders
        the function makes sure each folder path is converted to absolute before
        getting passed to internal functions
        """
        for bak_dir in bak_dirs:
            bak_dir = Path(bak_dir).absolute()
            files = self._filter_updated_paths(bak_dir)
            if files:
                meta_entry = self._create_meta_entry(bak_dir, len(files))
                self._compress(
                    files, self._meta_dir / (str(meta_entry) + ".zip"), bak_dir
                )
                self._entries.append(meta_entry)
                self._to_json()
            else:
                logging.info("No files have been added or updated, skipping")

    def _to_json(self):
        with open(self._meta_dir / ".meta.json", "w") as f:
            json.dump([meta_entry.to_dict() for meta_entry in self._entries], f)

    def _create_meta_entry(self, bak_dir: Path, file_count):
        data = {"path": bak_dir, "timestamp": time.time(), "file_count": file_count}
        return MetaEntry(data)

    def format_backup_list(self) -> str:
        meta_header = [
            f"Backup Directory: {self._meta_dir}",
            f"Total Backups: {len(self._entries)}",
            "",
        ]
        if not self._entries:
            meta_header.append("No backups found")
            return "\n".join(meta_header)

        # Define column widths
        id_width = 10
        dir_width = 60
        date_width = 20

        # Header
        header = f"{'BACKUP ID':<{id_width}} {'DIRECTORY':<{dir_width}} {'DATE':<{date_width}}"
        separator = "-" * (id_width + dir_width + date_width + 2)

        lines = meta_header + [header, separator]

        # Data rows
        for entry in self._entries:
            backup_id = entry.id_
            directory = str(entry._path)
            date_str = entry.datetime

            # Truncate if too long
            if len(directory) > dir_width:
                directory = "..." + directory[-dir_width + 3 :]

            row = f"{backup_id:<{id_width}} {directory:<{dir_width}} {date_str:<{date_width}}"
            lines.append(row)

        return "\n".join(lines)

    def _get_bak_meta(self, bak_id: str) -> tuple[Path, int] | None:
        for entry in self._entries:
            if getattr(entry, "id_") == bak_id:
                return (getattr(entry, "_path"), getattr(entry, "_timestamp"))

    def _extract(self, entry: MetaEntry):
        with zipfile.ZipFile(self._meta_dir / (str(entry) + ".zip"), "r") as zipf:
            zipf.extractall(getattr(entry, "_path"))

    def restore(self, bak_ids: list[str]):
        for bak_id in bak_ids:
            bak_meta = self._get_bak_meta(bak_id)
            if bak_meta is None:
                logging.error("backup id not found, skipping")
                continue
            bak_chain = list(
                filter(
                    lambda x: getattr(x, "_timestamp") <= bak_meta[1],  # type: ignore
                    self._get_backup_chain(bak_meta[0]),
                )
            )
            for entry in bak_chain:
                self._extract(entry)

    def _find_index_by_id(self, bak_id) -> int | None:
        for i in range(len(self._entries)):
            if self._entries[i].id_ == bak_id:
                return i

    def rm(self, back_ids: list[str], all=False):
        for bak_id in back_ids:
            if all:
                "find bak dir of the bak id, find all MetaEntry instances of the bak dir, remove all those instances from self._entries:"
                "   use get_bak_meta[0], def a func that replaces self._entries with a self.entries where path of each entry is not bak dir"

                back_meta = self._get_bak_meta(bak_id)
                if back_meta is not None:
                    bak_dir = back_meta[0]
                    for entry in self._entries:
                        if entry._path == bak_dir:
                            (self._meta_dir / (str(entry) + ".zip")).unlink()
                    self._entries = [
                        entry for entry in self._entries if entry._path != bak_dir
                    ]

                else:
                    logging.error(f"backup id {bak_id} not found, skipping")
            else:
                entry_index = self._find_index_by_id(bak_id)
                if entry_index is not None:
                    try:
                        rm_entry = self._entries[entry_index]
                        (self._meta_dir / Path(str(rm_entry) + ".zip")).unlink()
                    except FileNotFoundError as e:
                        logging.error("failed to remove backup" + str(e))
                    del self._entries[entry_index]
                    logging.info(f"removed {rm_entry}from registry")
                else:
                    logging.error(f"backup id {bak_id} not found, skipping")

        self._to_json()


if __name__ == "__main__":
    args = parser.parse_args()
    setup_logging(args.verbose)
    output_dir = Path(args.output)
    metadata = Metadata(output_dir)
    if args.command == "create":
        metadata.backup(args.create_dir_paths)
    elif args.command == "list":
        print(metadata.format_backup_list())
    elif args.command == "restore":
        metadata.restore(args.restore_bak_ids)
    elif args.command == "rm":
        metadata.rm(args.rm_bak_ids, args.rm_all)
    else:
        logging.error("Must provide a subcommand")
        parser.print_usage()

# TODO:
#   Complete logging
