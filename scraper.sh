#!/usr/bin/env bash

if [ -z "$1" ]; then
    echo "Usage: $0 <python_file_name>"
    exit 1
fi

PYTHON_FILE="$1"

source .venv/bin/activate
python3 "$PYTHON_FILE"