param(
    [ValidateSet('Release', 'RelWithDebInfo', 'Debug')][string]$Configuration = 'Release',
    [switch]$Test,
    [switch]$FullTest,
    [switch]$Wheel,
    [switch]$Fresh,
    [ValidateRange(1, 86400)][int]$TestTimeoutSec = 600,
    [ValidateRange(1, 32)][int]$Jobs = 4
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Run tools/windows/setup.ps1 first; see WINDOWS_BUILD.md.'
}
$preset = 'windows-msvc-' + $Configuration.ToLowerInvariant()
Push-Location -LiteralPath $repoRoot
try {
    $configureArgs = @('--preset', $preset)
    if ($Fresh) { $configureArgs += '--fresh' }
    & $python tools/windows/run.py --preset $preset cmake @configureArgs
    if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed.' }
    & $python tools/windows/run.py --preset $preset cmake --build --preset $preset --parallel $Jobs
    if ($LASTEXITCODE -ne 0) { throw 'Native build failed.' }
    if ($Test -or $FullTest) {
        $testArgs = @('--preset', $preset, '--timeout', $TestTimeoutSec.ToString(), '-j', '2')
        if ($Configuration -eq 'Debug' -and -not $FullTest) { $testArgs += @('-E', '^core\.pml$') }
        & $python tools/windows/run.py --preset $preset ctest @testArgs
        if ($LASTEXITCODE -ne 0) { throw 'CTest failed.' }
        & $python tools/windows/run.py --preset $preset python tools/windows/test_upstream.py
        if ($LASTEXITCODE -ne 0) { throw 'Python regression tests failed.' }
        & $python tools/windows/run.py --preset $preset python tools/windows/test_upstream.py `
            test_ring test_multilevel_atom `
            test_mode_decomposition.TestModeDecomposition.test_linear_taper_2d `
            test_mode_decomposition.TestModeDecomposition.test_oblique_waveguide_backward_mode
        if ($LASTEXITCODE -ne 0) { throw 'Harminv/MPB numerical tests failed.' }
    }
    if ($Wheel) {
        & $python tools/windows/run.py python -m build --wheel --no-isolation
        if ($LASTEXITCODE -ne 0) { throw 'Release wheel build failed.' }
    }
}
finally {
    Pop-Location
}
