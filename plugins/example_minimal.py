"""
Minimal plugin for SGAuto.

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


def extract_comment(file_path, all_files, log):
    log("Extracting binary data for {}".format(file_path))
    with open(file_path, "rb") as f:
        content = f.read(100)  # Read first 100 bytes
    return content.decode("utf-8", errors="replace")
