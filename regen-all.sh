#!/bin/bash
cd pyjwm
cmdStr=./jwmgen.py
if [ -f "`command -v jwmgen.py`" ]; then
    cmdStr="jwmgen.py"
fi

PARAM2=
if [ -d "/usr/local/share/applications" ]; then
    PARAM2="/usr/local/share/applications"
fi

PARAM3=
if [ -d "$HOME/.local/share/applications" ]; then
    $cmdStr
    PARAM3="$HOME/.local/share/applications"
fi

PARAM4=
if [ -d "/var/lib/flatpak/app" ]; then
    PARAM4="/var/lib/flatpak/app"
fi

mkdir -p ~/.local/share
$cmdStr /usr/share/applications $PARAM2 $PARAM3 $PARAM4 ~/.local/share/system-applications-menu --menu-name "All Programs"
# ^ The default menu-name is "Programs"
