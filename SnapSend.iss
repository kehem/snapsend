[Setup]
AppId={{12345678-1234-1234-1234-123456789012}}
AppName=SnapSend
AppVersion=1.0.0
DefaultDirName={autopf}\SnapSend
DefaultGroupName=SnapSend
OutputDir=dist
OutputBaseFilename=SnapSend-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\SnapSend.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\SnapSend"; Filename: "{app}\SnapSend.exe"
Name: "{autodesktop}\SnapSend"; Filename: "{app}\SnapSend.exe"

[Run]
Filename: "{app}\SnapSend.exe"; Description: "Launch SnapSend"; Flags: nowait postinstall skipifsilent
