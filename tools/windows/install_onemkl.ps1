param(
    [switch]$DownloadOnly,
    [string]$InstallDir = (Join-Path ${env:ProgramFiles(x86)} 'Intel/oneAPI')
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$dependency = (Get-Content (Join-Path $PSScriptRoot 'dependencies.json') -Raw | ConvertFrom-Json).oneMKL
$sdk = Join-Path $InstallDir ('mkl/' + $dependency.directoryVersion)
$versionParts = $dependency.version.Split('.')
$versionNumber = [int]$versionParts[0] * 10000 + [int]$versionParts[1] * 100 + [int]$versionParts[2]
if (-not $DownloadOnly -and (Test-Path -LiteralPath (Join-Path $sdk 'include/mkl_version.h')) -and
    (Test-Path -LiteralPath (Join-Path $sdk 'lib/cmake/mkl/MKLConfig.cmake')) -and
    (Test-Path -LiteralPath (Join-Path $sdk 'bin/mkl_sequential.2.dll'))) {
    $header = Get-Content -LiteralPath (Join-Path $sdk 'include/mkl_version.h') -Raw
    if ($header -match ("INTEL_MKL_VERSION\s+" + $versionNumber + '\b')) {
        Write-Host "Standalone oneMKL $($dependency.version) is already installed: $sdk"
        return
    }
}
$cache = Join-Path $repoRoot '.cache/installers'
New-Item -ItemType Directory -Path $cache -Force | Out-Null
$installer = Join-Path $cache $dependency.installer
if (-not (Test-Path -LiteralPath $installer)) {
    $download = $installer + '.download'
    & curl.exe --fail --location --retry 2 --output $download $dependency.url
    if ($LASTEXITCODE -ne 0) { throw 'Intel installer download failed.' }
    $downloadHash = (Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash
    if ($downloadHash -ne $dependency.sha256) { throw 'Intel installer SHA256 mismatch.' }
    Move-Item -LiteralPath $download -Destination $installer
}
if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $dependency.sha256) {
    throw 'Cached Intel installer SHA256 mismatch; it may be an unfinished download.'
}
$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Intel Corporation') {
    throw 'Intel installer digital signature validation failed.'
}
Write-Host "Verified standalone Intel oneMKL $($dependency.version): $installer"
if ($DownloadOnly) { return }

$logDirectory = Join-Path $cache 'install-logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$installerArguments = @('-s', '-a', '--silent', '--eula', 'accept',
    '--install-dir', ('"{0}"' -f $InstallDir.TrimEnd('\')),
    '--log-dir', ('"{0}"' -f $logDirectory), '-p=NEED_VS2022_INTEGRATION=0')
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $process = Start-Process -FilePath $installer -ArgumentList $installerArguments -WindowStyle Hidden -Wait -PassThru
}
else {
    Write-Host 'Windows will request administrator approval to install the standalone Intel SDK.'
    $process = Start-Process -FilePath $installer -ArgumentList $installerArguments -Verb RunAs -WindowStyle Hidden -Wait -PassThru
}
if ($process.ExitCode -notin @(0, 3010)) {
    throw "Intel installation failed (exit $($process.ExitCode)); inspect $logDirectory."
}
if (-not (Test-Path -LiteralPath (Join-Path $sdk 'lib/cmake/mkl/MKLConfig.cmake'))) {
    throw "Installer exited but the expected SDK is missing at $sdk. Inspect $logDirectory."
}
Write-Host "Installed standalone oneMKL SDK: $sdk"
if ($process.ExitCode -eq 3010) { Write-Host 'The installer reported that Windows needs a restart.' }
