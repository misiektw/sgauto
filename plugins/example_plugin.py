"""
Example plugin for SGAuto.

This plugin demonstrates how to create a comment extraction plugin.
The plugin module must contain a single function:

    def extract_comment(file_path: str, all_files: dict, log: function) -> str:
        ...
        return 'Some generated comment'

Example usage:
    The plugin can read from any of the monitored files and extract metadata,
    game state, player info, etc. to generate a meaningful comment.

    Any string returned will be used as comment for a backup.
"""

import os

from typing_extensions import Callable


def extract_comment(file_path: str, all_files: dict, log: Callable[[str], None]) -> str:
    """
    Args:
        file_path - file path with this script attached
        all_files - rest of the files in the list
        log - method object for showing text in log
    Returns:
        A comment string for the backup, or empty string to skip comment file creation.
    """

    log("Trying to extract comment for {}".format(file_path))
    # Example: Read the first file and extract a simple comment
    if not file_path:
        return ""

    try:
        # Example: Read file content and create a comment
        with open(file_path, "r") as f:
            content = f.read(100)  # Read first 100 bytes

        # Simple example: use file size as comment
        size = os.path.getsize(file_path)
        timestamp = all_files[file_path]

        comment = "C: {content} | {name} | Size: {size} bytes | Last modified: {date}"
        return comment.format(
            content=content, name=os.path.basename(file_path), size=size, date=timestamp
        )
    except Exception as e:
        log("Error during file processing: {}".format(e))
        # Return empty string on error - plugin errors are logged by sgauto
        return ""
