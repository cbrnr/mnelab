#!/bin/bash

RUFF_PATH=$(which ruff)
if [ -n "$RUFF_PATH" ]; then
    echo "Found ruff at: $RUFF_PATH"
    RUFF_BINARY="--add-binary=$RUFF_PATH:."
else
    echo "Warning: Ruff not found, formatting will not work in standalone build."
    RUFF_BINARY=""
fi

pyinstaller \
    --collect-all mne \
    --collect-all mnelab \
    --collect-all sklearn \
    --collect-all mne_qt_browser \
    --name MNELAB \
    --windowed \
    --noupx \
    --clean \
    --noconfirm \
    --icon ../src/mnelab/icons/mnelab-logo.svg \
    $RUFF_BINARY \
    ../src/mnelab/__main__.py
