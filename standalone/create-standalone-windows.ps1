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

$version = python get_version.py

$iscc = Join-Path $env:INNO_DIR "iscc.exe"
& $iscc /Dversion=$version mnelab-windows.iss
