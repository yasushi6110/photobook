#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/photoBook:${PYTHONPATH}"
python3 "${SCRIPT_DIR}/photoBook/mainWidget.py"
