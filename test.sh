#!/bin/bash
# test as python script, without building the app
#   NOTE: stdin stuff does not work correctly this way

# Created 2022 by James Bishop (james@bishopdynamics.com)


function bail() {
	echo "An unexpected error occurred"
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

echo "app exited cleanly"
