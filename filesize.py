#! /usr/bin/env python3

"""
Script for reporting sizes of files and length of directory contents
"""

import argparse
import pathlib
import sys

arg_parser = argparse.ArgumentParser(add_help=True)

arg_parser.add_argument("paths", nargs="*", help="files-directories to process")
arg_parser.add_argument("--verbose", "-v", action="store_true", help="verbose mode")


def parse_path(path: str | pathlib.Path, verbose=False):
    """Routing function. Will delegate to parse_dir if path is a directory, or parse_file if path is a file

    Args:
        path: Path object or stringified file path pointing to the dir to be processed
        verbose: bool object, used to control output verbosity

    Raises:
        FileNotFound, if provided path, does not correspond to a file or dir
    """
    path = pathlib.Path(path)

    if path.is_dir():
        _parse_dir(path, verbose=verbose)
    elif path.is_file():
        _parse_file(path, verbose=verbose)
    else:
        raise FileNotFoundError(f"{path} cannot be found skipping")


def _parse_dir(path: pathlib.Path, verbose: bool):
    """Function that prints the file/dir count of a directory

    Args:
        path: Path object pointing to the dir to be processed
        verbose: bool object, used to control output verbosity

    Returns:
        None

    Note:
        Expects path arg to be a Path object and pointing to a directory
    """
    # this is necessary for dirs, otherwise the '.' path would not work properly
    path = path.absolute()

    stringified_path = _get_verbose(path) if verbose else path.name

    contents_list = list(path.iterdir())

    dir_count = list(filter(pathlib.Path.is_dir, contents_list))

    file_count = list(filter(pathlib.Path.is_file, contents_list))

    print(
        stringified_path,
        "is a directory. It contains",
        len(file_count),
        "files and",
        len(dir_count),
        "directories",
    )


def _parse_file(path: pathlib.Path, verbose: bool):
    """Function that prints the size of a non-dir file

    Args:
        path: Path object pointing to the file to be processed
        verbose: bool object, used to control output verbosity

    Returns:
        None

    Note:
        Expects path arg to be a Path object and pointing to a file
    """
    stringified_path = _get_verbose(path) if verbose else path.name

    print(stringified_path, "is a file of size", path.stat().st_size, "bytes")


def _get_verbose(path: pathlib.Path) -> str:
    """function that prints the absolute file path, resolving symlinks if necessary

    Args:
        path: Path object pointing to the path to be printed

    Returns:
        stringified absolute and resolved path
    """
    return str(path.resolve())


def main():
    args = arg_parser.parse_args()
    if not args.paths:
        args.paths = [
            path.strip() for path in sys.stdin.read().split("\n") if path.strip()
        ]
    exit_code = 0
    for path in args.paths:
        try:
            parse_path(path, args.verbose)
        except (FileNotFoundError, TypeError) as e:
            exit_code = 1
            print(e)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
