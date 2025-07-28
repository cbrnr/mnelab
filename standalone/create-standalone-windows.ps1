pyinstaller `
    --collect-all mne `
    --collect-all mnelab `
    --collect-all sklearn `
    --collect-all mne_qt_browser `
    --name MNELAB `
    --windowed `
    --noupx `
    --clean `
    --noconfirm `
    --icon ..\src\mnelab\icons\mnelab-logo.ico `
    ..\src\mnelab\__main__.py

& iscc.exe /Dversion=$(python get_version.py) mnelab-windows.iss
