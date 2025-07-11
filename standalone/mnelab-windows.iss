; filepath: /Users/clemens/Projects/mnelab/standalone/windows/mnelab-installer.iss
;
; To build this installer, you need to:
; 1. Install Inno Setup: https://jrsoftware.org/isinfo.php
; 2. Run your pyinstaller-windows.bat script to create the 'dist\MNELAB' directory.
; 3. Open this .iss file in the Inno Setup Compiler and click "Compile".

#define MyAppVersion "1.1.0"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{F2A4E8B3-C89B-4D4B-9A6A-7E7E7E7E7E7E}
AppName=MNELAB
; Update this version number to match your application's version.
AppVersion={#MyAppVersion}
AppPublisher=MNELAB Developers
AppPublisherURL=https://github.com/mnelab/mnelab
AppSupportURL=https://github.com/mnelab/mnelab
AppUpdatesURL=https://github.com/mnelab/mnelab/releases
DefaultDirName={autopf}\MNELAB
DefaultGroupName=MNELAB
AllowNoIcons=yes
; The output installer file name.
OutputBaseFilename=mnelab-{#MyAppVersion}
; The directory where PyInstaller places your bundled app.
OutputDir=.\
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; The icon for the installer and the Add/Remove Programs entry.
SetupIconFile=..\src\mnelab\icons\mnelab-logo.ico
UninstallDisplayIcon={app}\MNELAB.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; This line copies all files from your PyInstaller output directory into the user's installation folder.
Source: "dist\MNELAB\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MNELAB"; Filename: "{app}\MNELAB.exe"
Name: "{group}\{cm:UninstallProgram,MNELAB}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MNELAB"; Filename: "{app}\MNELAB.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MNELAB.exe"; Description: "{cm:LaunchProgram,MNELAB}"; Flags: nowait postinstall skipifsilent
