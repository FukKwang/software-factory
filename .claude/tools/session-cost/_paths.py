"""Find the Claude Code transcript folder of the factory root.

Claude Code stores transcripts in ~/.claude/projects/<cwd with every
non-alphanumeric character replaced by '-'>. Pass a folder as the first
argument to override.
"""
import os, re, sys

FACTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def transcripts_dir():
    if len(sys.argv) > 1:
        return os.path.expanduser(sys.argv[1])
    return os.path.expanduser('~/.claude/projects/' + re.sub(r'[^A-Za-z0-9]', '-', FACTORY))
