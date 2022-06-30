#!/bin/bash
# Build the macos app

# Created 2022 by James Bishop (james@bishopdynamics.com)

APP_NAME='TableView'
VENV_NAME='venv'

function bail() {
	echo "An unexpected error occurred"
	exit 1
}

# create venv if missing
if [ ! -d "$VENV_NAME" ]; then
  ./setup-venv.sh || bail
fi

# we need modules in the venv
source "${VENV_NAME}/bin/activate" || bail

# make sure our build workspace is clean
rm -rf build dist

# store the current commit id into a file: commit_id which will end up inside the app under "data"
GIT_COMMIT=$(git rev-parse --short HEAD)
echo "$GIT_COMMIT" > commit_id

# using the .spec file, build a macos app out of our project
# TODO what is the line to generate the spec in the first place?
pyinstaller ${APP_NAME}.spec || {
  deactivate
  bail
}

# all done, deactivate the venv
deactivate
echo "Success, resulting app: \"dist/${APP_NAME}.app"
