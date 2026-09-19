#!/usr/bin/env python3
"""ULTRONE root CLI entrypoint forwarding to apps.api.main."""

import sys
from apps.api.main import main

if __name__ == "__main__":
    main(sys.argv[1:])
