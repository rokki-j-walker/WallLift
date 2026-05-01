param(
    [switch]$SkipExeBuild
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Set-Location -Path $ProjectRoot

$AppName = "WallLift"
$Version = "0.1.4"
$InnoCompiler = "C:\Program Files\utilities\Inno Setup 7\ISCC.exe"
$AppExe = Join-Path $ProjectRoot "dist\$AppName\$AppName.exe"
$InstallerScript = Join-Path $PSScriptRoot "installer.iss"
$InstallerPath = Join-Path $ProjectRoot "dist\installer\$AppName-$Version-setup-windows-x64.exe"

if (-not (Test-Path $InnoCompiler)) {
    throw "Inno Setup compiler was not found: $InnoCompiler"
}

if (-not $SkipExeBuild) {
    Write-Host "Building application EXE..."
    & (Join-Path $PSScriptRoot "build_exe.ps1")
} elseif (-not (Test-Path $AppExe)) {
    Write-Host "Application build is missing. Building EXE first..."
    & (Join-Path $PSScriptRoot "build_exe.ps1")
}

if (-not (Test-Path $AppExe)) {
    throw "Application executable was not found after build: $AppExe"
}

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "dist\installer") | Out-Null

& $InnoCompiler $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compiler failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $InstallerPath)) {
    throw "Installer was not created: $InstallerPath"
}

Write-Host ""
Write-Host "Installer completed: dist\installer\$AppName-$Version-setup-windows-x64.exe"
