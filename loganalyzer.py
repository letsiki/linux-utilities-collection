#!/usr/bin/env python3
"""
Return log message stats.
- Receives file(s) as  input
- Can expand directories too with the -e, --expand-dir option
- Can print output to json format with -j, --json option (default is a human readable text)
- Can output to file with the -o, --output option (default is console)
"""

import sys
import pathlib 
import re
import  argparse
from collections import Counter
from functools import reduce
import json

# Regex pattern for validating an log entry, and isolating the log type, should work with simple dates and anything more detailed
PATTERN = r'\d{4}-\d{2}-\d{2}(?: [,:0-9TZ]+)?[^ ]* ([a-zA-Z]+)'

parser = argparse.ArgumentParser(__name__, add_help=True, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('filepaths', nargs='*', help="provide file paths of the log files")
parser.add_argument('-j', '--json', action='store_true', help="outputs result as json")
parser.add_argument('-e', '--expand-dir', action='store_true', help="automatically expands dirs")
parser.add_argument('-o', '--output', help="switch output to the desired file")


def _classify_msgs(msgs: list[str]) ->  Counter:
    """Function that receives text lines from logs and counts logging types into a Counter dictionary
    """
    counter = Counter()
    for msg in msgs:
        if match := re.match(PATTERN, msg):
            counter[match.group(1)] += 1
    return counter
        
def _log2dict(path: pathlib.Path | str) -> Counter:
    """Extracts log stats from a text file
    """
    # Converts path to Path object if it isn't already
    path = pathlib.Path(path)

    with open(path, encoding="utf-8") as f:
        return _classify_msgs(f.readlines())

 
def _handle_output(output: dict, output_file: str | pathlib.Path | None = None, to_json: bool=True):
    """Handles result delivery
    """
    if to_json:
        if output_file:
            with open(output_file, 'w') as  f:
                json.dump(output, f)
        else:
            print(json.dumps(output, indent=4))
    else:
        hr_out = _human_readable(output) 
        if output_file:
            with open(output_file, 'w') as f:
                f.write(hr_out)
        else:
            print(hr_out)

def _human_readable(data: dict) -> str:
    """Stringifies data to a human readable format
    """
    lines = []
    lines.append(f"Total Lines: {data['total_lines']}")
    lines.append(f"Log Levels:")
    for log_level, count in data["log_levels"].items():
        lines.append(f"\t{log_level}: {count}")
    lines.append(f"Files processed:\n\t{',\n\t'.join(map(str, data['files_processed']))}")

    return "\n".join(lines)

def _expand_dir(filepath_list: list[str] | list[pathlib.Path]) -> list[str]:
    """Expands all dirs in a filepath list and returns a new list with non-dir paths
    """
    expanded_paths = []
    for path in filepath_list:
        if pathlib.Path(path).is_dir():
            expanded_paths.extend(_expand_dir(list(pathlib.Path(path).iterdir())))
        else:
            expanded_paths.append(path)
    return expanded_paths


def _is_text(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024000000)
        return True 
    except Exception:
        return False   

def parse_files(filepath_list: list[str] | list[pathlib.Path], output_file: str | pathlib.Path | None, to_json: bool, expand_dir=False):
    """
    - Orchestrates parsing of all log files, 
    - unifies all results to a common counter dictionary,
    - upgrades it into an enriched dictionary with the addition of total lines processed and files processed,
    - delegates output to handle_output function
    - exits with code 1 if any error occurred, but returns a result in any case
    """
    total_counter = Counter()
    exit_code = 0
    if expand_dir:
        filepath_list = _expand_dir(filepath_list)
    filepath_list = list(filter(_is_text, map(pathlib.Path, [path for path in filepath_list])))
    # Not efficient but filters out files containing no logs from the processed files entry
    filepath_list = list(filter(_log2dict, filepath_list))
    try:
        total_counter = reduce(lambda x, y: x + y, map(_log2dict, filepath_list), total_counter)
    except (TypeError, FileNotFoundError) as e:
        print(e)
        exit_code = 1
    output = {
        "total_lines": sum(total_counter.values()),
        "log_levels": total_counter.copy(),
        "files_processed": list(map(str, filepath_list))
    }

    _handle_output(output, output_file, to_json)
    sys.exit(exit_code)

def main():
    args = parser.parse_args()
    if not args.filepaths:
        args.filepaths = [path.strip() for path in sys.stdin.read().split('\n') if path.strip()]
    parse_files(args.filepaths, args.output, args.json, args.expand_dir)

if __name__ == '__main__':
    main()



