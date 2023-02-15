#!/bin/bash
# Build the macos app

# Created 2022 by James Bishop (james@bishopdynamics.com)

APP_NAME='TableView'
VENV_NAME='venv'

function bail() {
	echo "An unexpected error occurred"
	exit 1
}

function announce() {
  # for when you want to say something loudly
  MSG="$*"
  echo ""
  echo "####################################################################"
  echo "    $MSG"
  echo "####################################################################"
  echo ""
}

# create venv
announce "Rebuilding virtualenv: ${VENV_NAME}"
./setup-venv.sh || bail


# we need modules in the venv
announce "Activating virtualenv"
if [ "$(uname -s)" == "Darwin" ] || [ "$(uname -s)" == "Linux" ]; then
  source "${VENV_NAME}/bin/activate" || bail
else
  # assume Windows
  source "${VENV_NAME}/Scripts/activate" || bail
fi


# make sure our build workspace is clean
announce "Cleaning workspace"
rm -rf build dist

# store the current commit id into a file: commit_id which will end up inside the app under "data"
GIT_COMMIT=$(git rev-parse --short HEAD)
echo "$GIT_COMMIT" > commit_id
announce "Building from commit: $GIT_COMMIT"

# using the .spec file, build a macos app out of our project
# TODO what is the line to generate the spec in the first place?
pyinstaller ${APP_NAME}.spec || {
  deactivate
  bail
}

# done withbuild, deactivate the venv
announce "Deactivating virtualenv"
deactivate

announce "Cleaning temp workspace"
rm -r 'build' || bail  # clean up temp files
# rm -r 'dist/TableView' || bail  # clean up temp files

# zip up the app for release
ZIP_FILE_NAME="${APP_NAME}_${GIT_COMMIT}.zip"
announce "Creating archive: ${ZIP_FILE_NAME}"

if [ "$(uname -s)" == "Darwin" ]; then
  # on macos, we must properly zip the resulting app in order to distribute it
  pushd 'dist' || bail
  # this command is exactly the same as when you right-click and Compress in the UI
  #   https://superuser.com/questions/505034/compress-files-from-os-x-terminal
  ditto -c -k --sequesterRsrc --keepParent ${APP_NAME}.app "${ZIP_FILE_NAME}" || {
    echo "failed to compress app using \"ditto\" command"
    bail
  }
  popd || bail
fi


announce "Build Success!"
