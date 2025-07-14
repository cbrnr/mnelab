pyinstaller `
    --collect-all mne `
    --collect-all mnelab `
    --name MNELAB `
    --windowed `
    --noupx `
    --clean `
    --noconfirm `
    --icon ..\src\mnelab\icons\mnelab-logo.ico `
    ..\src\mnelab\__main__.py

& iscc.exe /Dversion=$(python get_version.py) mnelab-windows.iss
