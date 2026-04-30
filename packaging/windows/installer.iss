#define MyAppName "WallLift"
#define MyAppVersion "0.1.3"
#define MyAppPublisher "WallLift"
#define MyAppExeName "WallLift.exe"

[Setup]
AppId={{8D6D72C4-A60F-4D55-83DD-4CFD6B459774}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-setup-windows-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\WallLift\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[CustomMessages]
english.UninstallDataTitle=Remove user data
english.UninstallDataInfo=WallLift can also remove saved settings and downloaded AI files from:%n%n%1
english.UninstallDataCheck=Remove saved settings and downloaded AI files
english.UninstallDataOk=Continue
english.UninstallDataCancel=Cancel
russian.UninstallDataTitle=Удаление данных пользователя
russian.UninstallDataInfo=WallLift также может удалить сохранённые настройки и скачанные AI-файлы из папки:%n%n%1
russian.UninstallDataCheck=Удалить настройки и скачанные AI-файлы
russian.UninstallDataOk=Продолжить
russian.UninstallDataCancel=Отмена

[Code]
var
  RemoveUserData: Boolean;

function ShowUninstallDataPage: Boolean;
var
  Form: TSetupForm;
  InfoLabel: TNewStaticText;
  DataCheckBox: TNewCheckBox;
  OkButton: TNewButton;
  CancelButton: TNewButton;
  DataDir: String;
begin
  Result := False;
  DataDir := ExpandConstant('{userappdata}\{#MyAppName}');

  Form := CreateCustomForm(ScaleX(460), ScaleY(190), False, True);
  try
    Form.Caption := ExpandConstant('{cm:UninstallDataTitle}');

    InfoLabel := TNewStaticText.Create(Form);
    InfoLabel.Parent := Form;
    InfoLabel.Left := ScaleX(12);
    InfoLabel.Top := ScaleY(12);
    InfoLabel.Width := Form.ClientWidth - ScaleX(24);
    InfoLabel.Height := ScaleY(80);
    InfoLabel.AutoSize := False;
    InfoLabel.WordWrap := True;
    InfoLabel.Caption := FmtMessage(ExpandConstant('{cm:UninstallDataInfo}'), [DataDir]);

    DataCheckBox := TNewCheckBox.Create(Form);
    DataCheckBox.Parent := Form;
    DataCheckBox.Left := ScaleX(12);
    DataCheckBox.Top := ScaleY(104);
    DataCheckBox.Width := Form.ClientWidth - ScaleX(24);
    DataCheckBox.Height := ScaleY(24);
    DataCheckBox.Caption := ExpandConstant('{cm:UninstallDataCheck}');
    DataCheckBox.Checked := False;

    OkButton := TNewButton.Create(Form);
    OkButton.Parent := Form;
    OkButton.Left := Form.ClientWidth - ScaleX(216);
    OkButton.Top := Form.ClientHeight - ScaleY(42);
    OkButton.Width := ScaleX(96);
    OkButton.Height := ScaleY(30);
    OkButton.Caption := ExpandConstant('{cm:UninstallDataOk}');
    OkButton.ModalResult := mrOk;
    OkButton.Default := True;

    CancelButton := TNewButton.Create(Form);
    CancelButton.Parent := Form;
    CancelButton.Left := Form.ClientWidth - ScaleX(108);
    CancelButton.Top := OkButton.Top;
    CancelButton.Width := ScaleX(96);
    CancelButton.Height := ScaleY(30);
    CancelButton.Caption := ExpandConstant('{cm:UninstallDataCancel}');
    CancelButton.ModalResult := mrCancel;
    CancelButton.Cancel := True;

    Result := Form.ShowModal = mrOk;
    RemoveUserData := DataCheckBox.Checked;
  finally
    Form.Free();
  end;
end;

function InitializeUninstall: Boolean;
begin
  RemoveUserData := False;
  Result := ShowUninstallDataPage();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if (CurUninstallStep = usPostUninstall) and RemoveUserData then
  begin
    DataDir := ExpandConstant('{userappdata}\{#MyAppName}');
    if DirExists(DataDir) then
    begin
      DelTree(DataDir, True, True, True);
    end;
  end;
end;
