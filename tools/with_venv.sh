#!/bin/bash
TOOLS=`dirname $1`
#TOOLS=/opt/stack/ttm
VENV=$TOOLS/.venv

source $VENV/bin/activate && $@
