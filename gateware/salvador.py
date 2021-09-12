#!/usr/bin/env python3

from sys import argv, path, exit
from pathlib import Path

gatewarePath = Path(argv[0]).resolve().parent
if (gatewarePath / 'salvador').is_dir():
	path.insert(0, str(gatewarePath))
else:
	raise ImportError('Cannot find the gateware as `salvador` is not present')

from salvador import cli

if __name__ == '__main__':
	exit(cli())
