#define ExeName "Joystick_Diagrams.exe"
#define BuildDir "D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\"
#define ApplicationName "Joystick Diagrams"
#define Version "2.1.0"

[Setup]
AppName={#ApplicationName}
AppVersion={#Version}
VersionInfoVersion={#Version}
AppId={{CF6C627F-F3AB-42A2-97DC-F1319BB37430}}
ArchitecturesInstallIn64BitMode=x64
DefaultDirName={autopf}\{#ApplicationName}
DefaultGroupName={#ApplicationName}
AppCopyright=Robert Cox - joystick-diagrams.com
AppSupportURL=http://www.joystick-diagrams.com
SetupIconFile="{#BuildDir}img\logo.ico"
DisableWelcomePage=no
WizardImageFile="{#BuildDir}\img\logo-small.bmp"
WizardSmallImageFile="{#BuildDir}img\logo-thumb.bmp"
WizardImageStretch=no
WizardStyle=classic
OutputBaseFilename=Joystick Diagrams Installer - {#SetupSetting("AppVersion")}
[Dirs]
Name: "{userappdata}\Joystick Diagrams"

[Files]
Source: "{#BuildDir}*"; DestDir: "{app}"
Source: "{#BuildDir}img\*"; DestDir: "{app}\img"
Source: "{#BuildDir}lib\*"; DestDir: "{app}\lib"; Flags: recursesubdirs

#define ProcessFile(Source, FindResult, FindHandle) \
    Local[0] = FindGetFileName(FindHandle), \
    Local[1] = Source + "\\" + Local[0], \
    Local[2] = FindNext(FindHandle), \
    "'" + Local[0] + "'#13#10" + \
        (Local[2] ? ProcessFile(Source, Local[2], FindHandle) : "")
#define ProcessFolder(Source) \
    Local[0] = FindFirst(Source + "\\*.*", faAnyFile), \
    ProcessFile(Source, Local[0], Local[0])
#define DepedenciesToInstall ProcessFolder("D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\lib")
#define DependenciesLog "{app}\dependencies.log"

Source: "{#BuildDir}templates\*"; DestDir: "{app}\templates"; Flags: recursesubdirs
Source: "{#BuildDir}theme\*"; DestDir: "{app}\theme"

[UninstallDelete]
Type: files; Name: "{#DependenciesLog}"

[Tasks]
Name: "desktopicon"; Description: "Automatically create desktop icon?"; \
    GroupDescription: "Desktop Icon"; Flags: unchecked

[Icons]
Name: "{group}\{#ApplicationName}"; Filename: "{app}\{#ExeName}"; IconFilename: "{app}\{#ExeName}";
Name: "{userdesktop}\{#SetupSetting("AppName")}"; Filename: "{app}\{#ExeName}"; \
    IconFilename: "{app}\{#ExeName}"; Tasks: desktopicon

[Languages]
Name: "en"; MessagesFile: "D:\Git Repos\joystick-diagrams\installer\Default.isl"; InfoAfterFile: "D:\Git Repos\joystick-diagrams\installer\success.rtf"

[Run]
Filename: "{app}\{#ExeName}"; Description: Open Joystick Diagrams; Flags: nowait postinstall skipifsilent runascurrentuser

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  AppPath, DependenciesLogPath: string;
  Dependencies: TArrayOfString;
  Count, I: Integer;
  DependencyPath: string;
begin
  DependenciesLogPath := ExpandConstant('{#DependenciesLog}');

  if CurStep = ssInstall then
  begin
    if LoadStringsFromFile(DependenciesLogPath, Dependencies) then
    begin
      Count := GetArrayLength(Dependencies);
      Log(Format('Loaded %d dependencies, deleting...', [Count]));
      for I := 0 to Count - 1 do
        if (Dependencies[I] <> '.') and (Dependencies[I] <> '..') then
        begin
          DependencyPath := ExpandConstant('{app}\lib\' + Dependencies[I]);
          Log(Format('Deleting %s', [DependencyPath]));

          if DirExists(DependencyPath) then
          begin
            DelTree(DependencyPath,True,True,True);
          end;

          if FileExists(DependencyPath) then
          begin
            DeleteFile(DependencyPath);
          end;

        end;
    end;
  end
    else
  if CurStep = ssPostInstall then
  begin
    // Now that the app folder already exists,
    // save dependencies log (to be processed by future upgrade)
    if SaveStringToFile(DependenciesLogPath, {#DepedenciesToInstall}, False) then
    begin
      Log('Created dependencies log');
    end
      else
    begin
      Log('Failed to create dependencies log');
    end;
  end;
end;
