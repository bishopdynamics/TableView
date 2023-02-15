#!/bin/bash
# test as python script, without building the app

# Created 2022 by James Bishop (james@bishopdynamics.com)


function bail() {
	echo "script exited with error"
	exit 1
}

VENV_NAME="venv"

if [ "$(uname -s)" == "Darwin" ] || [ "$(uname -s)" == "Linux" ]; then
  PY_CMD='python3'
else
  # assume Windows
  PY_CMD='python'
fi

# create venv if missing
if [ ! -d "$VENV_NAME" ]; then
  ./setup-venv.sh || bail
fi

echo "activating virtualenv..."
# we need modules in the venv
if [ "$(uname -s)" == "Darwin" ] || [ "$(uname -s)" == "Linux" ]; then
  source "${VENV_NAME}/bin/activate" || bail
else
  # assume Windows
  source "${VENV_NAME}/Scripts/activate" || bail
fi

echo "running script..."
$PY_CMD TableView.py "$@" || {
  deactivate
  bail
}

echo "script exited cleanly"
