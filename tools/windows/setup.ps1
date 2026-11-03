param(
    [string]$PythonExe,
    [string]$MklRoot,
    [switch]$InstallOneMKL,
    [string]$Wheelhouse
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location -LiteralPath $repoRoot
try {
    if ($InstallOneMKL) { & (Join-Path $PSScriptRoot 'install_onemkl.ps1') }
    if (-not $PythonExe) {
        if (Get-Command py.exe -ErrorAction SilentlyContinue) {
            $PythonExe = & py.exe -3.12 -c 'import sys; print(sys.executable)'
        }
        else {
            $PythonExe = & python.exe -c 'import sys; print(sys.executable)'
        }
        if ($LASTEXITCODE -ne 0) { throw 'Install standard Windows CPython 3.12 x64, or pass -PythonExe.' }
    }
    & $PythonExe -c "import struct,sys; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'CPython 3.12 x64 is required'"
    if ($LASTEXITCODE -ne 0) { throw 'Python version or architecture does not match the project.' }
    & $PythonExe tools/windows/configure_environment.py @(
        if ($MklRoot) { '--mkl-root'; $MklRoot }
    )
    if ($LASTEXITCODE -ne 0) { throw 'Standalone oneMKL SDK selection failed.' }
    $venvPython = Join-Path $repoRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $PythonExe -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv.' }
    }
    & $venvPython -c "import struct,sys; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8"
    if ($LASTEXITCODE -ne 0) { throw 'Existing .venv is incompatible; use a fresh project directory.' }
    # Remove the previous port's pip SDK from this project environment only.
    $legacyInstalled = & $venvPython -c "from importlib.metadata import distributions; old={'mkl-devel','mkl-include','mkl','onemkl-license','intel-openmp','intel-cmplr-lib-ur','tbb-devel','tbb','tcmlib','umf'}; print(' '.join(d.metadata['Name'] for d in distributions() if d.metadata['Name'].lower() in old))"
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect legacy SDK packages.' }
    if ($legacyInstalled -and $legacyInstalled.Trim()) {
        $legacyPackages = $legacyInstalled.Trim().Split(' ')
        & $venvPython -m pip uninstall -y @legacyPackages
        if ($LASTEXITCODE -ne 0) { throw 'Could not remove legacy pip SDK packages.' }
    }
    $pipArguments = @('install', '--disable-pip-version-check', '-r', 'requirements-windows.lock.txt')
    if ($Wheelhouse) {
        $wheelhousePath = (Resolve-Path -LiteralPath $Wheelhouse).Path
        & $venvPython tools/windows/wheelhouse.py $wheelhousePath
        if ($LASTEXITCODE -ne 0) { throw 'Offline Python wheel checksums do not match.' }
        $pipArguments += @('--no-index', '--find-links', $wheelhousePath)
    }
    & $venvPython -m pip @pipArguments
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    & $venvPython tools/windows/doctor.py
    if ($LASTEXITCODE -ne 0) { throw 'Development environment verification failed.' }
    Write-Host 'Setup complete. Open this folder in VS2022 or run tools/windows/build.ps1 -Configuration Debug.'
}
finally {
    Pop-Location
}
