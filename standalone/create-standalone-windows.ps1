$ruffPath = (Get-Command ruff -ErrorAction SilentlyContinue).Source
if ($ruffPath) {
    Write-Host "Found ruff at: $ruffPath"
    $ruffBinary = @("--add-binary", "$ruffPath;.")
} else {
    Write-Host "Warning: ruff not found, formatting will not work in standalone build"
    $ruffBinary = @()
}

$pyinstallerArgs = @(
    "--collect-all", "mne",
    "--collect-all", "mnelab",
    "--collect-all", "sklearn",
    "--collect-all", "mne_qt_browser",
    "--name", "MNELAB",
    "--windowed",
    "--noupx",
    "--clean",
    "--noconfirm",
    "--icon", "..\src\mnelab\icons\mnelab-logo.ico"
) + $ruffBinary + @("..\src\mnelab\__main__.py")

pyinstaller @pyinstallerArgs

& iscc.exe /Dversion=$(python get_version.py) mnelab-windows.iss
