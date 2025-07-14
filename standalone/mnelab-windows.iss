[Setup]
AppId={{D963A2CB-DBF5-4104-8142-9D039F65285E}
AppName=MNELAB
AppVersion={#version}
AppVerName=MNELAB {#version}
AppPublisher=MNELAB Developers
AppPublisherURL=https://github.com/cbrnr/mnelab
AppSupportURL=https://github.com/cbrnr/mnelab
AppUpdatesURL=https://github.com/cbrnr/mnelab/releases
DefaultDirName={autopf}\MNELAB
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UsePreviousAppDir=no
DisableProgramGroupPage=yes
OutputBaseFilename=MNELAB-{#version}
OutputDir=.\ 
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\src\mnelab\icons\mnelab-logo.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\MNELAB\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MNELAB"; Filename: "{app}\MNELAB.exe"
Name: "{autodesktop}\MNELAB"; Filename: "{app}\MNELAB.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MNELAB.exe"; Description: "{cm:LaunchProgram,MNELAB}"; Flags: nowait postinstall skipifsilent
