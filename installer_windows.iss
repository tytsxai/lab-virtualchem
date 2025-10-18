; ============================================================================
; VirtualChemLab Windows 安装程序配置
; 使用 Inno Setup 6+ 编译
; 下载地址: https://jrsoftware.org/isdl.php
; ============================================================================

#define MyAppName "VirtualChemLab"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "VirtualChemLab Team"
#define MyAppURL "https://virtualchemlab.com"
#define MyAppExeName "VirtualChemLab.exe"
#define MyAppDescription "虚拟化学实验室 - 高性能桌面版"

[Setup]
; 基本信息
AppId={{8F9D2E6C-4B5A-4D3E-9F1C-7A8B6C5D4E3F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/support
AppUpdatesURL={#MyAppURL}/updates
AppCopyright=Copyright (C) 2025 {#MyAppPublisher}

; 安装路径
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 输出配置
OutputDir=dist
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
SetupIconFile=assets\icons\app.ico

; 压缩配置（最高压缩率）
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=1048576
LZMANumFastBytes=273

; 外观配置
WizardStyle=modern
WizardImageFile=compiler:WizModernImage-IS.bmp
WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp

; 系统要求
MinVersion=10.0.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; 权限
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; 其他设置
AllowNoIcons=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
DisableWelcomePage=no
LicenseFile=LICENSE
InfoBeforeFile=
InfoAfterFile=

; 目录设置
CreateAppDir=yes
DiskSpanning=no

[Languages]
; 多语言支持
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[CustomMessages]
; 自定义中文消息
chinesesimplified.CreateDesktopIconMsg=创建桌面快捷方式(&D)
chinesesimplified.CreateQuickLaunchIconMsg=创建快速启动图标(&Q)
chinesesimplified.LaunchProgramMsg=启动 {#MyAppName}(&L)
chinesesimplified.AssociateFilesMsg=关联 .vcl 实验文件(&A)
chinesesimplified.InstallDriversMsg=安装虚拟设备驱动程序（推荐）

[Tasks]
; 安装任务
Name: "desktopicon"; Description: "{cm:CreateDesktopIconMsg}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIconMsg}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "associatefiles"; Description: "{cm:AssociateFilesMsg}"; GroupDescription: "文件关联:"; Flags: unchecked

[Files]
; 主程序文件
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 运行时文件
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

; 注意：dist\VirtualChemLab 目录下的所有文件都会被包含

[Icons]
; 开始菜单图标
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\访问官网"; Filename: "{#MyAppURL}"
Name: "{group}\用户手册"; Filename: "{app}\README.md"

; 桌面图标
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"

; 快速启动图标
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; 文件关联
Root: HKA; Subkey: "Software\Classes\.vcl"; ValueType: string; ValueName: ""; ValueData: "VirtualChemLabFile"; Flags: uninsdeletevalue; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\VirtualChemLabFile"; ValueType: string; ValueName: ""; ValueData: "VirtualChemLab 实验文件"; Flags: uninsdeletekey; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\VirtualChemLabFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\VirtualChemLabFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatefiles

; 应用程序路径
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"

; 卸载信息
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{#MyAppVersion}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#MyAppURL}"

[Run]
; 安装后运行
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgramMsg}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载前运行（清理）
Filename: "{app}\{#MyAppExeName}"; Parameters: "--cleanup"; Flags: runhidden; RunOnceId: "CleanupOnUninstall"

[UninstallDelete]
; 卸载时删除的文件和目录
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\data\backups"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"

[Code]
// ============================================================================
// Pascal Script 自定义代码
// ============================================================================

var
  DownloadPage: TDownloadWizardPage;

// 初始化安装程序
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  Version: TWindowsVersion;
begin
  Result := True;

  // 检查Windows版本
  GetWindowsVersionEx(Version);
  if Version.Major < 10 then
  begin
    MsgBox('此应用程序需要 Windows 10 或更高版本。' + #13#10 +
           '您当前的系统版本过低，无法安装。',
           mbError, MB_OK);
    Result := False;
    Exit;
  end;

  // 检查是否已安装旧版本
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1') or
     RegKeyExists(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1') then
  begin
    if MsgBox('检测到已安装的版本。是否要先卸载旧版本？',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 这里可以添加卸载旧版本的代码
    end;
  end;
end;

// 初始化卸载程序
function InitializeUninstall(): Boolean;
begin
  Result := True;

  if MsgBox('确定要卸载 {#MyAppName} 吗？' + #13#10 +
            '您的实验数据和配置文件将被保留。',
            mbConfirmation, MB_YESNO) = IDNO then
  begin
    Result := False;
  end;
end;

// 安装完成后
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 创建数据目录
    if not DirExists(ExpandConstant('{app}\data')) then
      CreateDir(ExpandConstant('{app}\data'));

    if not DirExists(ExpandConstant('{app}\logs')) then
      CreateDir(ExpandConstant('{app}\logs'));

    if not DirExists(ExpandConstant('{app}\config')) then
      CreateDir(ExpandConstant('{app}\config'));
  end;
end;

// 获取卸载后的大小
function GetUninstallDataSize(): Integer;
begin
  Result := 150 * 1024 * 1024; // 约150MB
end;

// 是否需要重启
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  NeedsRestart := False;
  Result := '';
end;

// 自定义页面
procedure InitializeWizard();
begin
  // 可以在这里添加自定义安装页面
end;

// 卸载完成后
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // 询问是否删除用户数据
    DataPath := ExpandConstant('{app}\data');
    if DirExists(DataPath) then
    begin
      if MsgBox('是否删除所有实验数据和配置文件？' + #13#10 +
                '警告：此操作不可恢复！',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(DataPath, True, True, True);
      end;
    end;
  end;
end;

// ============================================================================
// 辅助函数
// ============================================================================

// 检查.NET Framework是否已安装（如果需要）
function IsDotNetInstalled(): Boolean;
begin
  Result := True; // 我们不需要.NET Framework
end;

// 获取安装大小
function GetInstallSize(): Int64;
begin
  Result := 150 * 1024 * 1024; // 约150MB
end;
