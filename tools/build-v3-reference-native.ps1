# Build the optional P3 native reader separately from the managed bridge.
# This compiles only; it never starts NX or replaces a loaded DLL.
param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $projectRoot 'src\bridge\V3\ReferenceGeometryNative.cpp'
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
$vcvars = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
$nxBase = $env:UGII_BASE_DIR
if ([string]::IsNullOrWhiteSpace($nxBase)) { throw 'UGII_BASE_DIR is required' }
$ugopen = Join-Path $nxBase 'UGOPEN'
foreach ($path in @($source, $vcvars, (Join-Path $ugopen 'uf_brep.h'), (Join-Path $ugopen 'libufun.lib'))) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required build input missing: $path" }
}
New-Item -ItemType Directory -Force -Path $output | Out-Null
$snapshot = Join-Path $output 'ReferenceGeometryNative.cpp'
if (Test-Path -LiteralPath $snapshot) { throw 'Build source snapshot already exists; choose a new output directory' }
if (Test-Path -LiteralPath (Join-Path $output 'ReferenceGeometryNative.dll')) { throw 'Native DLL already exists; choose a new output directory' }
Copy-Item -LiteralPath $source -Destination $snapshot
$originalBytes = [System.IO.File]::ReadAllBytes($source)
$snapshotBytes = [System.IO.File]::ReadAllBytes($snapshot)
if ($originalBytes.Length -ne $snapshotBytes.Length) { throw 'Source copy length differs' }
for ($i = 0; $i -lt $originalBytes.Length; $i++) {
    if ($originalBytes[$i] -ne $snapshotBytes[$i]) { throw 'Source copy differs' }
}
$env:V3_NATIVE_VCVARS = $vcvars
$env:V3_NATIVE_INCLUDE = $ugopen
$env:V3_NATIVE_SOURCE = $snapshot
$command = 'call "%V3_NATIVE_VCVARS%" >nul && cl.exe /nologo /LD /EHsc /std:c++14 /I "%V3_NATIVE_INCLUDE%" /FoReferenceGeometryNative.obj /FeReferenceGeometryNative.dll "%V3_NATIVE_SOURCE%" /link /LIBPATH:"%V3_NATIVE_INCLUDE%" libufun.lib'
Push-Location $output
try {
    $buildOutput = & cmd.exe /d /c $command 2>&1
    $code = $LASTEXITCODE
    $record = @('P3 native build; source snapshot directly byte-compared with workspace input before compile.',
                "Workspace source: $source", "Compiled snapshot: $snapshot", "Working directory: $output",
                "V3_NATIVE_VCVARS=$vcvars", "V3_NATIVE_INCLUDE=$ugopen", "V3_NATIVE_SOURCE=$snapshot",
                "Command: cmd.exe /d /c $command", "Exit code: $code", 'Compiler output:') + $buildOutput
    $record | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $output 'native-build-record.txt')
    $buildOutput | Write-Output
    if ($code -ne 0) { throw "Native compile failed: $code" }
} finally {
    Pop-Location
    Remove-Item Env:V3_NATIVE_VCVARS, Env:V3_NATIVE_INCLUDE, Env:V3_NATIVE_SOURCE -ErrorAction SilentlyContinue
}
