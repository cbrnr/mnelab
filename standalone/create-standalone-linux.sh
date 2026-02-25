pyinstaller \
    --collect-all mne \
    --collect-all mnelab \
    --collect-all sklearn \
    --collect-all mne_qt_browser \
    --collect-all pybvrf \
    --name MNELAB \
    --windowed \
    --noupx \
    --clean \
    --noconfirm \
    --icon ../src/mnelab/icons/mnelab-logo.svg \
    ../src/mnelab/__main__.py
