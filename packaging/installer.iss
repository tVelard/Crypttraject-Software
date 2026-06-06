; Inno Setup script for the CryptTraject desktop application installer.
;
; Wraps the PyInstaller output (dist/crypttraject/, a self-contained folder
; with CryptTraject.exe + all native libs incl. Pyfhel/SEAL and the Qt
; WebEngine Chromium runtime) into a single CryptTraject-Setup.exe. The end
; user just double-clicks it: the app is installed to Program Files with
; Start Menu and (optional) desktop shortcuts, nothing else to install.
;
; Built by packaging/build_binaries.py via the Inno Setup compiler (ISCC).
; AppVersion can be overridden on the command line:
;     ISCC /DAppVersion=0.1.0 packaging\installer.iss

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName "CryptTraject"
#define AppPublisher "CryptTraject"
#define ExeName "CryptTraject.exe"

[Setup]
AppId={{8F3C2A11-4B7E-4D2A-9C61-CRYPTTRAJECT01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\CryptTraject
DefaultGroupName=CryptTraject
DisableProgramGroupPage=yes
; Per-machine install puts the app in Program Files. Requires admin; the
; installer requests elevation.
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist
OutputBaseFilename=CryptTraject-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#ExeName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "addtopath"; Description: "Ajouter crypttraject-client (CLI) au PATH"; GroupDescription: "Intégration système:"; Flags: unchecked

[Files]
; Ship the entire PyInstaller folder (exe + libs + data + Qt WebEngine).
Source: "..\dist\crypttraject\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\CryptTraject"; Filename: "{app}\{#ExeName}"
Name: "{group}\Désinstaller CryptTraject"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CryptTraject"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Lancer CryptTraject"; Flags: nowait postinstall skipifsilent

[Registry]
; Optionally add {app} to the system PATH so the bundled CLI
; (crypttraject-client.exe, if present) is reachable from a terminal.
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; \
    Check: NeedsAddPath('{app}'); Tasks: addtopath

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKLM,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  // Avoid duplicating the entry on re-install/upgrade.
  Result := Pos(';' + Uppercase(ExpandConstant(Param)) + ';',
                ';' + Uppercase(OrigPath) + ';') = 0;
end;
