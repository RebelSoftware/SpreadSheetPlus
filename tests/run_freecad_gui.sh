#!/bin/bash
# Run a FreeCAD GUI script truly headless and always exit.
#
# Why this exists: the AppImage's own `AppRun` wrapper unconditionally does
# `export QT_QPA_PLATFORM=xcb`, so setting QT_QPA_PLATFORM in the caller's
# environment has no effect and a real window pops up on the desktop (and the
# process keeps running after the script ends).
#
# This wrapper replicates AppRun's environment but forces the offscreen Qt
# platform, so GUI tests (view providers, dialogs, commands) run without a
# window and terminate on their own.
#
# Usage: tests/run_freecad_gui.sh <script.py> [args...]
#        tests/run_freecad_gui.sh freecadcmd -M <repo> <script.py>
#
# Override the AppImage location with FREECAD_APPDIR if needed.

set -u

# Find an extracted AppImage (or any FreeCAD install) to run: FREECAD_APPDIR
# first, then the usual places a dev copy lives.
if [ -n "${FREECAD_APPDIR:-}" ]; then
    APPDIR="${FREECAD_APPDIR}"
else
    APPDIR=""
    for candidate in "${HOME}/Applications/squashfs-root" "${HOME}/squashfs-root" \
                     "/opt/FreeCAD/squashfs-root"; do
        if [ -x "${candidate}/usr/bin/freecad" ]; then
            APPDIR="${candidate}"
            break
        fi
    done
fi

if [ -z "${APPDIR}" ] || [ ! -x "${APPDIR}/usr/bin/freecad" ]; then
    echo "run_freecad_gui.sh: cannot find FreeCAD" >&2
    echo "set FREECAD_APPDIR to your extracted AppImage directory" >&2
    exit 2
fi

export PREFIX="${APPDIR}/usr"
export PYTHONHOME="${APPDIR}/usr"
export PATH_TO_FREECAD_LIBDIR="${APPDIR}/usr/lib"
export FONTCONFIG_FILE=/etc/fonts/fonts.conf
export FONTCONFIG_PATH=/etc/fonts
export SSL_CERT_FILE="${PREFIX}/ssl/cacert.pem"
export GIT_SSL_CAINFO="${APPDIR}/usr/ssl/cacert.pem"

# Must come after anything that could set it (this is the whole point).
export QT_QPA_PLATFORM="${FCSP_QPA_PLATFORM:-offscreen}"

# First argument selects the binary (like AppRun does); default to the GUI app.
if [ "$#" -gt 0 ] && [ -x "${APPDIR}/usr/bin/$1" ]; then
    MAIN="${APPDIR}/usr/bin/$1"
    shift
else
    MAIN="${APPDIR}/usr/bin/freecad"
fi

"${MAIN}" "$@"
status=$?
exit $status
