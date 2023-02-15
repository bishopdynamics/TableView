#!/bin/bash
# Launch the app created by build-app.sh

# Created 2022 by James Bishop (james@bishopdynamics.com)

APP_NAME="TableView"
if [ "$(uname -s)" == "Darwin" ]; then
  OUTPUT_FILE="dist/${APP_NAME}.app/Contents/MacOS/${APP_NAME}"
elif [ "$(uname -s)" == "Linux" ]; then
  OUTPUT_FILE="dist/${APP_NAME}"
else
  # assume Windows
  OUTPUT_FILE="dist/${APP_NAME}.exe"
fi

function bail() {
	echo "An unexpected error occurred"
	exit 1
}

./build-app.sh || bail

if [ ! -f "${OUTPUT_FILE}" ]; then
  echo "Could not find \"${APP_NAME}\", you need to build first: ./build-app.sh"
  bail
fi

"./${OUTPUT_FILE}" "$@" || bail

echo "app exited cleanly"