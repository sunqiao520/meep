param([switch]$Notebooks)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run setup.ps1 first.' }
Push-Location -LiteralPath $repoRoot
try {
    & (Join-Path $PSScriptRoot 'install_onemkl.ps1') -DownloadOnly
    $wheelhouse = Join-Path $repoRoot '.cache/wheelhouse'
    New-Item -ItemType Directory -Path $wheelhouse -Force | Out-Null
    & $python -m pip download --disable-pip-version-check --only-binary=:all: `
        --dest $wheelhouse -r requirements-windows.lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python wheel download failed.' }
    if ($Notebooks) {
        & $python -m pip download --disable-pip-version-check --only-binary=:all: `
            --dest $wheelhouse -c requirements-windows.lock.txt -r requirements-notebooks.lock.txt
        if ($LASTEXITCODE -ne 0) { throw 'Notebook wheel download failed.' }
    }
    & $python tools/windows/wheelhouse.py --write $wheelhouse
    if ($LASTEXITCODE -ne 0) { throw 'Wheelhouse checksum generation failed.' }
    Write-Host 'Offline cache prepared: .cache/installers and .cache/wheelhouse'
}
finally {
    Pop-Location
}
