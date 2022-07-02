#!/bin/bash
# test as python script, without building the app

# Created 2022 by James Bishop (james@bishopdynamics.com)


function bail() {
	echo "script exited with error"
	exit 1
}

VENV_NAME="venv"

# create venv if missing
if [ ! -d "$VENV_NAME" ]; then
  ./setup-venv.sh || bail
fi

echo "activating virtualenv..."
# we need modules in the venv
source "${VENV_NAME}/bin/activate" || bail

echo "running script..."
python TableView.py "$@" || {
  deactivate
  bail
}

echo "script exited cleanly"
