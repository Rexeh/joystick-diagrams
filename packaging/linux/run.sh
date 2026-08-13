#!/bin/sh
# Launcher for the frozen Linux build.
#
# The cd is load bearing: joystick_diagrams/version.py resolves
# ./version_manifest.json and ./templates relative to the working directory,
# so the app must start from its own install directory.
set -e

APP_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$APP_DIR"

exec ./joystick_diagrams "$@"
