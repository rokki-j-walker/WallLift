$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Set-Location -Path $ProjectRoot

$Version = "0.1.4"
$AppName = "WallLift"
$DistDir = Join-Path $ProjectRoot "dist\$AppName"
$ArchivePath = Join-Path $ProjectRoot "dist\$AppName-$Version-windows-x64.zip"

function Copy-ResourceFiles {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string[]]$Extensions,
        [string[]]$IgnoredParts = @()
    )

    if (-not (Test-Path $Source)) {
        return
    }

    $sourceRoot = (Resolve-Path $Source).Path.TrimEnd("\", "/")

    Get-ChildItem -Path $Source -Recurse -File | ForEach-Object {
        if ($Extensions -notcontains $_.Extension.ToLowerInvariant()) {
            return
        }

        $fullPath = (Resolve-Path $_.FullName).Path
        $relativePath = $fullPath.Substring($sourceRoot.Length).TrimStart("\", "/")
        $parts = $relativePath -split '[\\/]'
        foreach ($ignoredPart in $IgnoredParts) {
            if ($parts -contains $ignoredPart) {
                return
            }
        }

        $targetPath = Join-Path $Destination $relativePath
        New-Item -ItemType Directory -Force -Path (Split-Path $targetPath -Parent) | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $targetPath -Force
    }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm walllift.spec

Copy-ResourceFiles -Source (Join-Path $ProjectRoot "lang") -Destination (Join-Path $DistDir "lang") -Extensions @(".json")
Copy-ResourceFiles -Source (Join-Path $ProjectRoot "themes") -Destination (Join-Path $DistDir "themes") -Extensions @(".json", ".png") -IgnoredParts @("WallLift_result")

if (Test-Path $ArchivePath) {
    Remove-Item -LiteralPath $ArchivePath -Force
}

Compress-Archive -Path (Join-Path $DistDir "*") -DestinationPath $ArchivePath -CompressionLevel Optimal

Write-Host ""
Write-Host "Build completed: dist\WallLift\WallLift.exe"
Write-Host "Archive completed: dist\WallLift-$Version-windows-x64.zip"
