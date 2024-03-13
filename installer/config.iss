[Setup]
AppName=Joystick Diagrams
AppVersion=2.0.8
AppId=JoystickDiagrams
ArchitecturesInstallIn64BitMode=x64
DefaultDirName={autopf}\Joystick Diagrams
DefaultGroupName=Joystick Diagrams
AppCopyright=Robert Cox - joystick-diagrams.com
AppSupportURL=http://www.joystick-diagrams.com
SetupIconFile=D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\img\logo.ico
DisableWelcomePage=no
WizardImageFile=D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\img\logo-small.bmp
WizardSmallImageFile=D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\img\logo-thumb.bmp
WizardImageStretch=no
WizardStyle=classic
OutputBaseFilename=Joystick Diagrams Installer
[Dirs]
Name: "{userappdata}\Joystick Diagrams"

[Files]
Source: "D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\*"; DestDir: "{app}"
Source: "D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\img\*"; DestDir: "{app}\img"
Source: "D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\lib\*"; DestDir: "{app}\lib"; Flags: recursesubdirs

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

Source: "D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\templates\*"; DestDir: "{app}\templates"; Flags: recursesubdirs
Source: "D:\Git Repos\joystick-diagrams\build\exe.win-amd64-3.11\theme\*"; DestDir: "{app}\theme"

[UninstallDelete]
Type: files; Name: "{#DependenciesLog}"

[Icons]
Name: "{group}\Joystick Diagrams"; Filename: "{app}\Joystick_Diagrams.exe"; IconFilename: "{app}\Joystick_Diagrams.exe"

[Languages]
Name: "en"; MessagesFile: "D:\Git Repos\joystick-diagrams\installer\Default.isl"; InfoAfterFile: "D:\Git Repos\joystick-diagrams\installer\success.rtf"

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
