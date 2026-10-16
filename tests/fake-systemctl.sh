#!/bin/sh
# Isolated disk-guard test only: must never be installed as production systemctl.
test "$1" = stop && test "$2" = strfry.service
