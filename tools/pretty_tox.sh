#! /bin/sh

TESTRARGS=$1

# Delete bytecodes from normal directories before running tests.
# Note that bytecodes in dot directories will not be deleted
# to keep bytecodes of python modules installed into virtualenvs.
sh -c "find . -type d -name '.?*' -prune -o \
    \( -type d -name '__pycache__' -o -type f -name '*.py[co]' \) \
    -print0 | xargs -0 rm -rf"

exec 3>&1
status=$(exec 4>&1 >&3; ( python setup.py testr --slowest --testr-args="--subunit $TESTRARGS"; echo $? >&4 ) | subunit-trace -f) && exit $status
