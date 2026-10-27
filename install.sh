#!/bin/sh
# Install PyDevices' MicroPython build system, and optionally build.
#
#   curl -fsSL https://pydevices.github.io/install.sh | sh
#   curl -fsSL https://pydevices.github.io/install.sh | sh -s -- --port unix --variant pydevices --modules all
#   curl -fsSL https://pydevices.github.io/install.sh | sh -s -- --deps rp2
#
# Clones micropython-pydevices into ./micropython-pydevices, in the current
# directory (or updates the clone already there), checks the tools every build needs, and says what to
# run next. Arguments after "--" go to build_mp.py, which fetches MicroPython,
# the modules and each port's toolchain on its first run.
#
# On Windows, run it from Git Bash. There it clones first, then checks for
# Python and the MSYS2 toolchain that builds the windows port natively.
#
# --deps <port>... installs, with apt-get, the Debian packages every port needs
# and those of the ports named (unix, esp32, rp2, windows, webassembly, or
# all), then stops: no clone, no build. A dev container's image is made this
# way. It uses sudo unless it runs as root.
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

# The Debian packages: the ones every port needs, then each port's. This one
# list is what the advice below prints and what --deps installs.
BASE_PKGS="git make cmake python3 gcc g++"
PORTS="unix esp32 rp2 windows webassembly"

port_pkgs() {  # port
    case "$1" in
        unix) echo "pkg-config libsdl2-dev libffi-dev" ;;
        esp32) echo "ninja-build python3-venv libusb-1.0-0" ;;
        rp2) echo "gcc-arm-none-eabi libnewlib-arm-none-eabi" ;;
        windows) echo "gcc-mingw-w64-x86-64 binutils-mingw-w64-x86-64 libtool libltdl-dev autoconf automake" ;;
        webassembly) echo "nodejs" ;;
        *) return 1 ;;
    esac
}

port_aside() {  # port
    case "$1" in
        unix) echo "the desktop display" ;;
        esp32) echo "ESP-IDF itself is fetched" ;;
        rp2) echo "the pico-sdk is fetched" ;;
        windows) echo "SDL2 for MinGW is fetched" ;;
        webassembly) echo "emsdk itself is fetched" ;;
    esac
}

# Whether what a package provides is here, by the command or file a build uses.
pkg_present() {  # package
    case "$1" in
        python3) have python3 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null ;;
        libsdl2-dev) have pkg-config && pkg-config --exists sdl2 2>/dev/null ;;
        libffi-dev) have pkg-config && pkg-config --exists libffi 2>/dev/null ;;
        ninja-build) have ninja ;;
        python3-venv) have python3 && python3 -c 'import venv' 2>/dev/null ;;
        # ESP-IDF's installer checks the openocd it fetches, which needs libusb.
        libusb-1.0-0)
            for d in /usr/lib/*-linux-gnu /lib/*-linux-gnu /usr/lib64 /usr/lib; do
                [ -e "$d/libusb-1.0.so.0" ] && return 0
            done
            return 1 ;;
        gcc-arm-none-eabi) have arm-none-eabi-gcc ;;
        libnewlib-arm-none-eabi)
            # A toolchain from Arm carries its own newlib; Debian's comes apart.
            have arm-none-eabi-gcc || return 1
            libc=$(arm-none-eabi-gcc -print-file-name=libc.a 2>/dev/null)
            case "$libc" in /*) [ -f "$libc" ] ;; *) return 1 ;; esac ;;
        gcc-mingw-w64-x86-64) have x86_64-w64-mingw32-gcc ;;
        binutils-mingw-w64-x86-64) have x86_64-w64-mingw32-windres ;;
        libtool) have libtoolize ;;
        # libffi's autoreconf needs libltdl's macros (LT_SYS_SYMBOL_USCORE), which
        # come apart from libtoolize: libltdl-dev on Debian.
        libltdl-dev) [ -f "$(aclocal --print-ac-dir 2>/dev/null || echo /usr/share/aclocal)/ltdl.m4" ] ;;
        autoconf) have autoreconf ;;
        nodejs) have node ;;
        *) have "$1" ;;
    esac
}

# The packages in "a b c" that aren't here yet.
missing_pkgs() {
    out=
    for pkg in $1; do
        pkg_present "$pkg" || out="$out $pkg"
    done
    echo "$out" | sed 's/^ *//'
}

# Every package, base and ports, as the one apt-get line, wrapped.
all_pkgs_line() {
    pkgs=$BASE_PKGS
    for port in $PORTS; do pkgs="$pkgs $(port_pkgs "$port")"; done
    line="  sudo apt-get update && sudo apt-get install -y"
    for pkg in $pkgs; do
        if [ $(( ${#line} + ${#pkg} )) -gt 76 ]; then
            say "$line \\"
            line="   "
        fi
        line="$line $pkg"
    done
    say "$line"
}

# --deps: apt-get install the base and the named ports' packages.
install_deps() {  # port...
    [ $# -gt 0 ] || fail "--deps takes the ports to install for: $(list "$PORTS"), or all"
    pkgs=$BASE_PKGS
    which="$(list "$*")"
    for port in "$@"; do
        if [ "$port" = all ]; then
            for p in $PORTS; do pkgs="$pkgs $(port_pkgs "$p")"; done
            which="every port"
        else
            p=$(port_pkgs "$port") || fail "there is no port called $port; the ports are $(list "$PORTS")"
            pkgs="$pkgs $p"
        fi
    done
    have apt-get || fail "--deps installs with apt-get (Debian, Ubuntu, WSL). Elsewhere, install these under your system's names: $pkgs"
    sudo=
    if [ "$(id -u)" -ne 0 ]; then
        have sudo || fail "--deps needs root or sudo to run apt-get"
        sudo=sudo
    fi
    say "Installing the packages for $which:"
    say "  $pkgs"
    # shellcheck disable=SC2086 # $sudo and $pkgs split on purpose
    $sudo env DEBIAN_FRONTEND=noninteractive apt-get update < /dev/null || fail "apt-get update failed"
    # shellcheck disable=SC2086
    $sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y $pkgs < /dev/null || fail "apt-get install failed"
    say ""
    say "Installed: $which can build once micropython-pydevices is cloned:"
    say "  curl -fsSL https://pydevices.github.io/install.sh | sh"
}

check_tools() {
    missing=$(missing_pkgs "$BASE_PKGS")
    if [ -n "$missing" ]; then
        say "Missing: $missing"
        say ""
        say "On Debian or Ubuntu (WSL included), this installs what every port needs:"
        say ""
        all_pkgs_line
        say ""
        fail "install those, then run this again"
    fi
}

# "a b c" as "a, b and c".
list() {
    # shellcheck disable=SC2086 # split on spaces on purpose
    set -- $1
    out=
    while [ $# -gt 0 ]; do
        if [ -z "$out" ]; then out=$1
        elif [ $# -eq 1 ]; then out="$out and $1"
        else out="$out, $1"
        fi
        shift
    done
    echo "$out"
}

# Port by port: what's installed, and the Debian package for what isn't.
# Sets READY (ports that build now), WAITING (ports that don't yet), NOTES
# (a line per waiting port) and PKGS (a line per waiting port: the port, then
# its packages).
port_notes() {
    READY='' WAITING='' NOTES='' PKGS=''
    for port in $PORTS; do
        port_note "$port" "$(missing_pkgs "$(port_pkgs "$port")")" "$(port_aside "$port")"
    done
    [ -n "$WAITING" ] || return 0
    say ""
    say "Not installed yet, needed only for these ports:$NOTES"
    say ""
    say "On Debian or Ubuntu (WSL included), this installs them, a line per port;"
    say "leave out the lines for ports you won't build:"
    say ""
    say "  sudo apt-get update"
    width=$(printf '%s\n' "$PKGS" | while read -r port pkgs; do echo "${#pkgs}"; done | sort -n | tail -n 1)
    printf '%s\n' "$PKGS" | while read -r port pkgs; do
        say "$(printf '  sudo apt-get install -y %-*s  # %s' "$width" "$pkgs" "$port")"
    done
    say ""
    say "Other distributions carry the same tools under their own names. A build"
    say "for a port that's still missing something stops and says so."
    say ""
    say "This script can install them too, a port at a time or all of them:"
    say "  curl -fsSL https://pydevices.github.io/install.sh | sh -s -- --deps rp2"
}

port_note() {  # port "missing packages" aside
    if [ -z "$2" ]; then
        READY="$READY $1"
        return 0
    fi
    pkgs=$(echo "$2" | sed 's/^ *//')
    WAITING="$WAITING $1"
    NOTES="$NOTES
$(printf '  %-14s%s (%s)' "$1:" "$(echo "$pkgs" | sed 's/ /, /g')" "$3")"
    PKGS="${PKGS}${PKGS:+
}$1 $pkgs"
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
    say "The guide: https://github.com/PyDevices/micropython-pydevices/blob/main/docs/guides/build-on-windows.md"
}

main() {
    if [ "${1:-}" = --deps ]; then
        shift
        install_deps "$@"
        return
    fi
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
    if [ -z "$WAITING" ]; then
        say "Ready. To build:"
    elif [ -z "$READY" ]; then
        say "Nothing builds until those are installed. Then:"
    else
        say "Ready for $(list "$READY"); $(list "$WAITING") once those are installed. To build:"
    fi
    say ""
    say "  cd $dir"
    say "  ./build_mp.py          # asks for port, board, variant, flash size and modules"
    say "  ./build_mp.py --port unix --variant pydevices --modules all"
    say "  ./build_mp.py --port esp32 --board ESP32_GENERIC_S3 --variant SPIRAM_OCT --flash 8MB --modules all"
    say ""
    say "The guide: https://github.com/PyDevices/micropython-pydevices/blob/main/docs/get-started/install.md"
}

main "$@"
