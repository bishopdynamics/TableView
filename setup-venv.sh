#!/bin/bash
# create python virtualenv with all the modules this app requires

# Created 2022 by James Bishop (james@bishopdynamics.com)

VENV_NAME='venv'
PY_CMD='python3'

function bail() {
	echo "An unexpected error occurred"
	exit 1
}

function announce() {
  # sometimes you just need a message to be more noticable in the output
  echo ""
  echo "############# $* ##################"
  echo ""
}

# clear any existing virtualenv
if [ -d "$VENV_NAME" ]; then
	announce "removing existing $VENV_NAME"
	rm -r "$VENV_NAME" || bail
fi

announce "checking for virtualenv module"
$PY_CMD -m virtualenv --version || {
  # no virtualenv module, try to install it
  announce "virtualenv module not found, trying to install it for you"
  # always upgrade to latest pip
  $PY_CMD -m pip install --upgrade pip || {
    announce "something went wrong while upgrading pip!"
    echo "try manually: $PY_CMD -m pip install --upgrade pip"
    bail
  }
	$PY_CMD -m pip install virtualenv || {
    announce "something went wrong while trying to install virtualenv module?"
    echo "try manually: $PY_CMD -m pip install virtualenv"
    bail
  }
}

announce "setting up virtualenv"
$PY_CMD -m virtualenv "$VENV_NAME" || {
  announce "failed to create virtualenv, is virtualenv module setup properly?"
  echo "try manually upgrading it: $PY_CMD -m pip install --upgrade virtualenv"
  bail
}

# now activate the venv so we can install stuff inside it
source "${VENV_NAME}/bin/activate" || bail

# always upgrade to latest pip first
announce "upgrading pip"
pip install --upgrade pip || bail

# install this apps requirements
announce "installing requirements.txt"
pip install -r requirements.txt || bail

# fixes issue by bug in old version
announce "upgrading httplib2"
pip install --upgrade httplib2 || bail

# make sure pyinstaller stuff is latest version
announce "installing pyinstaller requirements"
pip3 install --upgrade PyInstaller pyinstaller-hooks-contrib || bail

deactivate || bail
announce "virtualenv setup complete: $VENV_NAME"
