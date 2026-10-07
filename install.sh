#!/bin/sh
# Install PyDevices' MicroPython build system, and optionally build.
#
#   curl -fsSL https://pydevices.github.io/install.sh | sh
#   curl -fsSL https://pydevices.github.io/install.sh | sh -s -- --port unix --variant pydevices --modules all
#
# Clones micropython-pydevices into ./micropython-pydevices, in the current
# directory (or updates the clone already there), checks the tools every build needs, and says what to
# run next. Arguments after "--" go to build_mp.py, which fetches MicroPython,
# the modules and each port's toolchain on its first run.
#
# On Windows, run it from Git Bash. There it clones first, then checks for
# Python and the MSYS2 toolchain that builds the windows port natively.
#
# Environment:
#   PYDEVICES_DIR     where to clone (default ./micropython-pydevices)
#   PYDEVICES_BRANCH  branch to check out (default main)
#
# Plain POSIX sh, and everything runs from main() on the last line, so a
# download cut short runs nothing. Nothing reads stdin: piped, stdin is this
# script; a build that has to ask reads the terminal.

set -u

URL=https://github.com/PyDevices/micropython-pydevices.git

say() { echo "$*"; }
fail() { echo "install.sh: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# Git Bash (MINGW), MSYS2 or Cygwin: native Windows, where Python is python or
# "py -3" and the windows port builds with MSYS2's make and MinGW gcc.
windows_host() {
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*) return 0 ;;
    esac
    return 1
}

# The first that really runs Python 3.9 or newer. Windows' python3 is often
# the Microsoft Store stub, which exits non-zero, so it's tried, not trusted.
find_python() {
    for p in python3 python "py -3"; do
        # shellcheck disable=SC2086 # "py -3" is two words on purpose
        if have ${p%% *} && $p -c 'import sys; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1; then
            PYTHON=$p
            return 0
        fi
    done
    PYTHON=
    return 1
}

windows_tools() {
    # What build_mp.py uses on Windows: MSYS2 at $MSYS2_ROOT (C:\msys64), or a
    # make and gcc already on PATH. A warning, never a stop: the clone is done.
    missing=
    find_python || missing="$missing Python-3.9+"
    root=$(cygpath -u "${MSYS2_ROOT:-C:\\msys64}" 2>/dev/null || echo /c/msys64)
    if [ -x "$root/usr/bin/make.exe" ] || have make; then :; else missing="$missing make"; fi
    if [ -x "$root/mingw64/bin/gcc.exe" ] || have gcc; then :; else missing="$missing gcc"; fi
    if [ -x "$root/usr/bin/autoreconf" ] || have autoreconf; then :; else missing="$missing autotools"; fi
    [ -z "$missing" ] && return 0
    say ""
    say "Not installed yet:$missing"
    say ""
    case "$missing" in
        *Python*)
            say "Python: install it from https://www.python.org/downloads/ (it's python or py,"
            say "never python3). If python opens the Microsoft Store, turn off the python.exe and"
            say "python3.exe aliases in Settings, Apps, Advanced app settings, App execution aliases."
            say "" ;;
    esac
    case "$missing" in
        *make*|*gcc*|*autotools*)
            say "MSYS2's MinGW toolchain, which builds the windows port. From PowerShell:"
            say ""
            say "  winget install --id MSYS2.MSYS2 -e"
            printf '%s\n' "  C:\\msys64\\usr\\bin\\bash.exe -lc \"pacman -Syu --noconfirm\""
            printf '%s\n' "  C:\\msys64\\usr\\bin\\bash.exe -lc \"pacman -S --needed --noconfirm make mingw-w64-x86_64-gcc autoconf automake libtool\""
            say ""
            say "(Run the first pacman line again if it says it must close.) build_mp.py finds"
            printf '%s\n' "MSYS2 in C:\\msys64 by itself; set MSYS2_ROOT if it's elsewhere."
            say "" ;;
    esac
    return 1
}

check_tools() {
    missing=
    for t in git python3 make cmake gcc g++; do
        have "$t" || missing="$missing $t"
    done
    if have python3 && ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
        missing="$missing python3>=3.9"
    fi
    if [ -n "$missing" ]; then
        say "Missing:$missing"
        say ""
        say "On Debian or Ubuntu (WSL included), this installs what every port needs:"
        say ""
        say "  sudo apt-get update && sudo apt-get install -y git make cmake ninja-build \\"
        say "    python3 python3-venv python3-pip gcc g++ pkg-config libffi-dev libsdl2-dev \\"
        say "    gcc-mingw-w64-x86-64 libtool libltdl-dev autoconf automake \\"
        say "    gcc-arm-none-eabi libnewlib-arm-none-eabi nodejs"
        say ""
        fail "install those, then run this again"
    fi
}

port_notes() {
    # What each port needs beyond the essentials; a build says so too, later.
    notes=
    have pkg-config && pkg-config --exists sdl2 2>/dev/null || notes="$notes
  unix:         libsdl2-dev, libffi-dev and pkg-config (the desktop display)"
    have x86_64-w64-mingw32-gcc && have libtoolize || notes="$notes
  windows:      gcc-mingw-w64-x86-64, libtool, libltdl-dev, autoconf, automake"
    have arm-none-eabi-gcc || notes="$notes
  rp2:          gcc-arm-none-eabi and libnewlib-arm-none-eabi"
    have node || notes="$notes
  webassembly:  nodejs (emsdk itself is fetched)"
    have ninja && python3 -c 'import venv' 2>/dev/null || notes="$notes
  esp32:        ninja-build and python3-venv (ESP-IDF itself is fetched)"
    if [ -n "$notes" ]; then
        say ""
        say "Not installed yet, needed only for these ports:$notes"
    fi
}

fetch() {  # dir branch
    if [ -d "$1/.git" ]; then
        origin=$(git -C "$1" remote get-url origin 2>/dev/null || true)
        case "$origin" in
            *PyDevices/micropython-pydevices*) ;;
            *) fail "$1 is a different git checkout ($origin); set PYDEVICES_DIR" ;;
        esac
        say "Updating $1"
        git -C "$1" fetch -q origin "$2" < /dev/null || fail "git fetch failed"
        git -C "$1" checkout -q "$2" < /dev/null || fail "could not check out $2 (local changes?)"
        git -C "$1" merge -q --ff-only "origin/$2" < /dev/null || fail "$1 has diverged from origin/$2; update it by hand"
    elif [ -e "$1" ] && [ -n "$(ls -A "$1" 2>/dev/null)" ]; then
        fail "$1 exists and is not a micropython-pydevices clone; set PYDEVICES_DIR"
    else
        say "Cloning micropython-pydevices into $1"
        git clone -q --branch "$2" "$URL" "$1" < /dev/null || fail "git clone failed"
    fi
    say "micropython-pydevices $(git -C "$1" rev-parse --short HEAD) ($2)"
}

main_windows() {  # dir branch [build_mp.py arguments]
    dir=$1 branch=$2
    shift 2
    have git || fail "git is missing; install Git for Windows (https://git-scm.com), then run this again from Git Bash"
    fetch "$dir" "$branch"
    windows_tools
    ready=$?

    if [ $# -gt 0 ]; then
        [ -n "$PYTHON" ] || fail "no Python to build with; install it, then run this again"
        say ""
        say "Building: $PYTHON build_mp.py $*"
        cd "$dir" || fail "cannot enter $dir"
        # shellcheck disable=SC2086
        if [ -r /dev/tty ] && ( : < /dev/tty ) 2>/dev/null; then
            exec $PYTHON build_mp.py "$@" < /dev/tty
        fi
        # shellcheck disable=SC2086
        exec $PYTHON build_mp.py "$@" < /dev/null
    fi

    if [ "$ready" -eq 0 ]; then
        say ""
        say "Ready. To build the windows port, in PowerShell or here:"
    else
        say "Once those are installed, build the windows port, in PowerShell or here:"
    fi
    say ""
    say "  cd $dir"
    say "  ${PYTHON:-python} build_mp.py --port windows --variant pydevices --modules all"
    say ""
    say "Every other port (esp32, rp2, webassembly, unix) builds from WSL, as on Linux."
    say "The guide: https://github.com/PyDevices/micropython-pydevices/blob/main/docs/newcomers.md#on-windows"
}

main() {
    dir=${PYDEVICES_DIR:-micropython-pydevices}
    branch=${PYDEVICES_BRANCH:-main}
    if windows_host; then
        main_windows "$dir" "$branch" "$@"
        return
    fi
    case "$(uname -s)" in
        Linux) ;;
        *) say "Note: the build system is tested on Linux (WSL included); $(uname -s) may need more." ;;
    esac

    check_tools
    fetch "$dir" "$branch"

    if [ $# -gt 0 ]; then
        say ""
        say "Building: ./build_mp.py $*"
        cd "$dir" || fail "cannot enter $dir"
        if [ -r /dev/tty ] && ( : < /dev/tty ) 2>/dev/null; then
            exec python3 build_mp.py "$@" < /dev/tty
        fi
        exec python3 build_mp.py "$@" < /dev/null
    fi

    port_notes
    say ""
    say "Ready. To build:"
    say ""
    say "  cd $dir"
    say "  ./build_mp.py          # asks for port, board, variant, flash size and modules"
    say "  ./build_mp.py --port unix --variant pydevices --modules all"
    say "  ./build_mp.py --port esp32 --board ESP32_GENERIC_S3 --variant SPIRAM_OCT --flash 8MB --modules all"
    say ""
    say "The guide: https://github.com/PyDevices/micropython-pydevices/blob/main/docs/newcomers.md"
}

main "$@"
