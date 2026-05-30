; Inno Setup script for the CryptTraject CLI Windows installer.
;
; Wraps the PyInstaller output (dist/crypttraject/, a self-contained folder
; with crypttraject-cli.exe + all native libs incl. Pyfhel/SEAL) into a
; single CryptTraject-Setup.exe. The end user just double-clicks it: the
; tool is installed to Program Files and added to PATH, so
; `crypttraject-cli` works from any terminal with nothing else to install.
;
; Built by packaging/build_binaries.py via the Inno Setup compiler (ISCC).
; AppVersion can be overridden on the command line:
;     ISCC /DAppVersion=0.1.0 packaging\installer.iss

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName "CryptTraject CLI"
#define AppPublisher "CryptTraject"
#define ExeName "crypttraject-cli.exe"

[Setup]
AppId={{8F3C2A11-4B7E-4D2A-9C61-CRYPTTRAJECT01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\CryptTraject
DefaultGroupName=CryptTraject
DisableProgramGroupPage=yes
; Per-machine install puts the binary in Program Files and writes the
; system PATH. Requires admin; the installer requests elevation.
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist
OutputBaseFilename=CryptTraject-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "addtopath"; Description: "Ajouter crypttraject-cli au PATH (recommandé)"; GroupDescription: "Intégration système:"

[Files]
; Ship the entire PyInstaller folder (exe + libs + data).
Source: "..\dist\crypttraject\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\CryptTraject CLI (invite de commande)"; Filename: "{cmd}"; Parameters: "/K ""cd /d %USERPROFILE% && echo Tapez: crypttraject-cli --help"""
Name: "{group}\Désinstaller CryptTraject"; Filename: "{uninstallexe}"

[Registry]
; Add {app} to the system PATH when the task is selected. The PATH change
; is picked up by new terminals (a fresh login guarantees it).
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
