param(
    [ValidateSet('Debug', 'Release', 'RelWithDebInfo')][string]$Configuration = 'Debug',
    [string]$Wheelhouse
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run tools/windows/setup.ps1 first.' }
Push-Location -LiteralPath $repoRoot
try {
    $pipArguments = @('install', '--disable-pip-version-check',
        '-c', 'requirements-windows.lock.txt', '-r', 'requirements-notebooks.lock.txt')
    if ($Wheelhouse) {
        $wheelhousePath = (Resolve-Path -LiteralPath $Wheelhouse).Path
        & $python tools/windows/wheelhouse.py $wheelhousePath
        if ($LASTEXITCODE -ne 0) { throw 'Offline wheel checksums do not match.' }
        $pipArguments += @('--no-index', '--find-links', $wheelhousePath)
    }
    & $python -m pip @pipArguments
    if ($LASTEXITCODE -ne 0) { throw 'Notebook dependency installation failed.' }
    & (Join-Path $PSScriptRoot 'build.ps1') -Configuration $Configuration
    & $python tools/windows/configure_notebook.py --configuration $Configuration
    if ($LASTEXITCODE -ne 0) { throw 'Notebook kernel configuration failed.' }
}
finally {
    Pop-Location
}
