param(
    [Parameter(Mandatory=$true)][string]$NxRoot,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $OutputPath) { throw 'Refusing to overwrite version evidence.' }
$root = (Resolve-Path -LiteralPath $NxRoot).Path
$runner = Join-Path $root 'NXBIN\run_journal.exe'
$ugraf = Join-Path $root 'NXBIN\ugraf.exe'
$assembly = Join-Path $root 'NXBIN\managed\NXOpen.dll'
foreach ($file in @($runner, $ugraf, $assembly)) {
    if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required NX executable or assembly missing.' }
}
foreach ($file in @($runner, $ugraf)) {
    $version = (Get-Item -LiteralPath $file).VersionInfo
    if ($version.FileVersion -cne '2506.1700' -or $version.ProductVersion -cne '2506.1700') {
        throw 'NX executable version differs from reviewed 2506.1700.'
    }
}
$version = (Get-Item -LiteralPath $assembly).VersionInfo
$assemblyVersion = [Reflection.AssemblyName]::GetAssemblyName($assembly).Version.ToString()
if ($version.FileVersion -cne '2506.0.0.0' -or $version.ProductVersion -cne '2506.0.0.0' -or $assemblyVersion -cne '2506.0.0.0') {
    throw 'NXOpen version differs from reviewed 2506.0.0.0.'
}
$evidence = [ordered]@{nx_root=$root; executable_file_version='2506.1700';
    executable_product_version='2506.1700'; nxopen_file_version=$version.FileVersion;
    nxopen_product_version=$version.ProductVersion; nxopen_assembly_version=$assemblyVersion;
    status='PASS'}
[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath), ($evidence | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
