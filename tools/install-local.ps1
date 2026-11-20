# Update one existing installation after a staged offline V3 verification.
# This script does not create a client registration, launch/stop NX, or change credentials.
param([string]$InstallRoot = '', [string]$Version = '', [string]$BuildRoot = '', [switch]$CleanReplace)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $codexHome = $env:CODEX_HOME
    if ([string]::IsNullOrWhiteSpace($codexHome)) { $codexHome = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex' }
    $InstallRoot = Join-Path $codexHome 'nx-sketch-mcp'
}
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path.TrimEnd('\','/')
$install = (Resolve-Path -LiteralPath ([IO.Path]::GetFullPath($InstallRoot))).Path.TrimEnd('\','/')
if ([string]::Equals($install,$projectRoot,[StringComparison]::OrdinalIgnoreCase) -or
    $install.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
    $projectRoot.StartsWith($install + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installation root and project root must not overlap.'
}
$metadataPath = Join-Path $install 'installation.json'
if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) { throw 'Existing installation.json is required; this tool does not register a new MCP installation.' }
$metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding utf8 | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace([string]$metadata.source_root) -or
    -not [string]::Equals((Resolve-Path -LiteralPath ([string]$metadata.source_root)).Path.TrimEnd('\','/'),$projectRoot,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installation source_root differs from this source tree.'
}
if (Get-Process -Name ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue) {
    throw 'NX, an NX journal, or a bridge helper is running. Save and close the appropriate session before replacing loaded assemblies; no process was changed.'
}
if ([string]::IsNullOrWhiteSpace($BuildRoot)) { $BuildRoot = Join-Path $projectRoot 'workspace/build/current/M2' }
$build = (Resolve-Path -LiteralPath ([IO.Path]::GetFullPath($BuildRoot))).Path
$nativeNames = @('M2Bridge.dll','M2Entry.dll','M2JsonlHelper.exe','M2Startup.dll','ReferenceGeometryNative.dll')
foreach ($name in $nativeNames) {
    if (-not (Test-Path -LiteralPath (Join-Path $build $name) -PathType Leaf)) {
        throw "BuildRoot must contain all five V3 artifacts; missing $name. Use -BuildRoot with a complete prepared build."
    }
}
$pythonExe = (Get-Command python.exe -ErrorAction Stop | Select-Object -First 1).Path
$stage = Join-Path $install ('.v3-install-stage-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $stage) { throw 'Unexpected staging path collision.' }
$stageApp = Join-Path $stage 'app'
$app = Join-Path $install 'app'
$backupRoot = Join-Path $stage 'backup'
$lockPath = Join-Path $install '.v3-install.lock'
$lock = $null
$launchMutex = $null
$mutexAcquired = $false
$journalGate = $null
$cleanup = $true
$replaceStarted = $false
$applied = [Collections.Generic.List[object]]::new()
function Assert-NoReparse([string]$path) {
    $current = [IO.Path]::GetFullPath($path)
    while ($current -and $current.StartsWith($install,[StringComparison]::OrdinalIgnoreCase)) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw ('Reparse point in managed installation path: ' + $current) }
        }
        if ([string]::Equals($current,$install,[StringComparison]::OrdinalIgnoreCase)) { break }
        $parent = [IO.Path]::GetDirectoryName($current)
        if ($parent -eq $current) { throw 'Invalid installation path.' }
        $current = $parent
    }
}
function Assert-PrivateConfigOutsideApp {
    $configured = $metadata.PSObject.Properties['mcp_config']
    $path = if ($configured -and -not [string]::IsNullOrWhiteSpace([string]$configured.Value)) { [string]$configured.Value } else { Join-Path $install 'mcp-config.json' }
    if (-not [IO.Path]::IsPathRooted($path)) { throw 'Existing private configuration path must be absolute.' }
    $path = [IO.Path]::GetFullPath($path)
    if (-not $path.StartsWith($install + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
        $path.StartsWith($app + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Existing private configuration must be a file under the installation root and outside app.' }
    Assert-NoReparse $path
    try { $config = Get-Content -LiteralPath $path -Raw -Encoding utf8 | ConvertFrom-Json -ErrorAction Stop }
    catch { throw 'Existing private configuration could not be checked safely.' }
    $tokenProperty = $config.PSObject.Properties['token_file']
    if (-not $tokenProperty -or [string]::IsNullOrWhiteSpace([string]$tokenProperty.Value) -or
        -not [IO.Path]::IsPathRooted([string]$tokenProperty.Value)) { throw 'Existing private token path is unavailable or not absolute.' }
    $tokenPath = [IO.Path]::GetFullPath([string]$tokenProperty.Value)
    if (-not $tokenPath.StartsWith($install + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
        $tokenPath.StartsWith($app + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Existing private token must be under the installation root and outside app.'
    }
    Assert-NoReparse $tokenPath
}
function Assert-AppTreeSafe([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return }
    if (-not (Test-Path -LiteralPath $path -PathType Container)) { throw 'CleanReplace app target must be a directory.' }
    $resolved = (Resolve-Path -LiteralPath $path).Path
    if (-not [string]::Equals($resolved, [IO.Path]::GetFullPath($app), [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals([IO.Path]::GetDirectoryName($resolved), $install, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'CleanReplace app target does not resolve to the installation app directory.'
    }
    Assert-NoReparse $resolved
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push($resolved)
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($item in Get-ChildItem -LiteralPath $directory -Force) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw ('Reparse point in old app; CleanReplace stopped: ' + $item.FullName) }
            if ($item.PSIsContainer) { $pending.Push($item.FullName) }
        }
    }
}
function Equal-FileBytes([string]$left,[string]$right) {
    $a = [IO.File]::Open($left,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    $b = $null
    try {
        $b = [IO.File]::Open($right,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
        if ($a.Length -ne $b.Length) { return $false }
        $x = [byte[]]::new(1048576); $y = [byte[]]::new(1048576)
        while (($n=$a.Read($x,0,$x.Length)) -gt 0) {
            $m=0; while ($m -lt $n) { $r=$b.Read($y,$m,$n-$m); if ($r -le 0) { return $false }; $m += $r }
            for ($j=0; $j -lt $n; $j++) { if ($x[$j] -ne $y[$j]) { return $false } }
        }
        return $b.ReadByte() -eq -1
    } finally { if ($b) { $b.Dispose() }; $a.Dispose() }
}
function Verify-App([string]$path) {
    $out = & $pythonExe -I -B (Join-Path $projectRoot 'tools/verify-installed-v3.py') $path
    if ($LASTEXITCODE -ne 0) { throw 'Offline V3 plan/export verification failed.' }
    $result = ($out | Out-String) | ConvertFrom-Json
    if ($result.offline_v3_plan_and_portable_export -ne 'PASS' -or $result.installed_stdio_v3_tool -ne 'PASS' -or $result.native_execution -ne 'NOT_RUN') { throw 'Invalid offline V3 verification result.' }
    return $result
}
try {
    Assert-NoReparse $install
    Assert-NoReparse $metadataPath
    Assert-NoReparse $app
    Assert-NoReparse $lockPath
    $lock = [IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    [void](New-Item -ItemType Directory -Path $stage -ErrorAction Stop)
    [void](New-Item -ItemType Directory -Path $stageApp -ErrorAction Stop)
    [void](New-Item -ItemType Directory -Path $backupRoot -ErrorAction Stop)
    [IO.File]::WriteAllText((Join-Path $stage 'installation.json'),(@{source_root=$projectRoot}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
    $files = [Collections.Generic.List[object]]::new()
    function Add-Managed([string]$source,[string]$relative) {
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw ('Missing source: ' + $source) }
        $relative = $relative.Replace('/','\')
        if ([IO.Path]::IsPathRooted($relative) -or $relative.Split('\') -contains '..') { throw 'Invalid managed relative path.' }
        $staged = [IO.Path]::GetFullPath((Join-Path $stageApp $relative))
        $target = [IO.Path]::GetFullPath((Join-Path $app $relative))
        if (-not $staged.StartsWith($stageApp + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
            -not $target.StartsWith($app + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Managed path escaped app.' }
        Assert-NoReparse $target
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $staged) | Out-Null
        Copy-Item -LiteralPath $source -Destination $staged
        $files.Add(@{source=$staged;target=$target;relative=$relative})
    }
    $packageRoot = Join-Path $projectRoot 'src/nx_sketch_mcp'
    foreach ($file in Get-ChildItem -LiteralPath $packageRoot -Recurse -File) {
        if ($file.Extension -notin @('.py','.cs','.ps1')) { continue }
        if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point in product source.' }
        $relative = [IO.Path]::GetRelativePath($packageRoot,$file.FullName)
        Add-Managed $file.FullName (Join-Path 'src/nx_sketch_mcp' $relative)
    }
    foreach ($name in $nativeNames) { Add-Managed (Join-Path $build $name) (Join-Path 'workspace/build/current/M2' $name) }
    Add-Managed (Join-Path $build 'M2Startup.dll') 'nx-profile/startup/M2Startup.dll'
    foreach ($name in @('mcp_stdio.py','run-mcp.ps1','start-nx-global.ps1','verify-m2-local-network.ps1')) { Add-Managed (Join-Path $projectRoot ('tools/'+$name)) ('tools/'+$name) }
    Add-Managed (Join-Path $projectRoot 'docs/installed-app-README.md') 'README.md'
    $featureDocs = @('F01-F02.md') + @(3..22 | ForEach-Object { 'F{0:D2}.md' -f $_ }) + @(8..22 | ForEach-Object { 'F{0:D2}-api-notes.md' -f $_ }) + @('V2.md','testing.md','M7-native-helical.md')
    foreach ($name in $featureDocs) { Add-Managed (Join-Path $projectRoot ('docs/'+$name)) ('docs/'+$name) }
    $sourceGuide = (Resolve-Path -LiteralPath (Join-Path $projectRoot 'docs/v3/reference-rebuild.md')).Path
    $sourceGuideUri = ([Uri]$sourceGuide).AbsoluteUri
    $installedGuide = Join-Path $stage 'installed-v3-guide.md'
    $guideText = @(
        '# V3 参考件重建指南',
        '',
        '完整使用说明、已审参考件和证据保留在 installation.json 所绑定的本机 source_root 中；安装目录不复制原件或证据。',
        '',
        ('[打开已绑定源项目的 V3 参考件重建指南](' + $sourceGuideUri + ')'),
        '',
        ('本机源文件：`' + $sourceGuide + '`'),
        '',
        '该路径须保持可用。已导出的 UG11 包可按包内 README 在独立目录运行。'
    ) -join "`n"
    [IO.File]::WriteAllText($installedGuide,$guideText + "`n",[Text.UTF8Encoding]::new($false))
    Add-Managed $installedGuide 'docs/v3/reference-rebuild.md'
    Add-Managed (Join-Path $projectRoot 'docs/installed-README.md') 'docs/installed-README.md'
    $binding = Join-Path $stageApp 'v3-runtime-binding.json'
    [IO.File]::WriteAllText($binding,(@{schema='v3-project-binding/1';source_root=$projectRoot}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
    $files.Add(@{source=$binding;target=(Join-Path $app 'v3-runtime-binding.json');relative='v3-runtime-binding.json'})
    $rootReadme = Join-Path $stage 'root-README.md'
    Copy-Item -LiteralPath (Join-Path $projectRoot 'docs/installed-README.md') -Destination $rootReadme
    $files.Add(@{source=$rootReadme;target=(Join-Path $install 'README.md');relative='__installation_README.md'})
    $smoke = Verify-App $stageApp
    if (-not [string]::IsNullOrWhiteSpace($Version) -and $Version -ne [string]$smoke.version) { throw 'Requested version differs from staged server version.' }
    if ([string]::IsNullOrWhiteSpace($Version)) { $Version = [string]$smoke.version }
    $userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $launchMutex = [Threading.Mutex]::new($false, ('Global\NxSketchMcpDedicatedLaunch-' + $userSid))
    try { $mutexAcquired = $launchMutex.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $mutexAcquired = $true }
    if (-not $mutexAcquired) { throw 'NX launcher is preparing a session; installation stopped.' }
    $coordinationRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex/nx-sketch-mcp/journal-coordination'
    [IO.Directory]::CreateDirectory($coordinationRoot) | Out-Null
    try {
        $journalGate = [IO.File]::Open((Join-Path $coordinationRoot 'gate.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    } catch { throw 'NX journal coordination gate is held; installation stopped.' }
    if (Test-Path -LiteralPath (Join-Path $coordinationRoot 'active.json')) { throw 'NX journal has an active or unresolved operation; installation stopped.' }
    if (Get-Process -Name ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue) { throw 'NX-related process appeared during staging; installation stopped.' }
    if ($CleanReplace) {
        # User-requested deletion is limited to the verified app subtree. The
        # install-root configuration, sessions, token and coordination are not copied or removed.
        Assert-AppTreeSafe $app
        Assert-PrivateConfigOutsideApp
        Assert-NoReparse (Join-Path $install 'README.md')
        Assert-NoReparse $metadataPath
        $replaceStarted = $true
        if (Test-Path -LiteralPath $app) { Remove-Item -LiteralPath $app -Recurse -Force }
        [IO.Directory]::Move($stageApp,$app)
        $installedSmoke = Verify-App $app
        if ([string]$installedSmoke.version -ne $Version) { throw 'Installed server version differs from staged version.' }
        $rootTarget = Join-Path $install 'README.md'
        if (Test-Path -LiteralPath $rootTarget -PathType Leaf) { [IO.File]::Move($rootReadme,$rootTarget,$true) }
        elseif (Test-Path -LiteralPath $rootTarget) { throw 'Installation README target is not a file.' }
        else { [IO.File]::Move($rootReadme,$rootTarget) }
        $metadata | Add-Member -NotePropertyName version -NotePropertyValue $Version -Force
        $metadata | Add-Member -NotePropertyName updated_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
        $newMetadata = Join-Path $stage 'metadata-new.json'
        [IO.File]::WriteAllText($newMetadata,($metadata | ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
        [IO.File]::Move($newMetadata,$metadataPath,$true)
        Write-Output ('Clean replaced version ' + $Version + '; offline V3 plan and portable export passed; native execution not run. Reconnect MCP; no NX hot reload.')
    } else {
    # Save only files we are authorized to replace; no unrelated files or private configuration are copied/deleted.
    foreach ($file in $files) {
        Assert-NoReparse $file.target
        $backup = Join-Path $backupRoot $file.relative
        $existed = Test-Path -LiteralPath $file.target -PathType Leaf
        if ((Test-Path -LiteralPath $file.target) -and -not $existed) { throw ('Managed target is not a file: ' + $file.target) }
        if ($existed) { New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null; Copy-Item -LiteralPath $file.target -Destination $backup }
        $applied.Add(@{target=$file.target;backup=$backup;existed=$existed})
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $file.target) | Out-Null
        Copy-Item -LiteralPath $file.source -Destination $file.target -Force
        # Avoid importing stale timestamp-based __pycache__ without deleting private files.
        if ([IO.Path]::GetExtension($file.target) -eq '.py') { [IO.File]::SetLastWriteTimeUtc($file.target,[DateTime]::UtcNow.AddSeconds(30)) }
    }
    $installedSmoke = Verify-App $app
    if ([string]$installedSmoke.version -ne $Version) { throw 'Installed server version differs from staged version.' }
    $metadataBackup = Join-Path $backupRoot 'installation.json'
    Copy-Item -LiteralPath $metadataPath -Destination $metadataBackup
    $applied.Add(@{target=$metadataPath;backup=$metadataBackup;existed=$true})
    $metadata | Add-Member -NotePropertyName version -NotePropertyValue $Version -Force
    $metadata | Add-Member -NotePropertyName updated_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    [IO.File]::WriteAllText($metadataPath,($metadata | ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
    Write-Output ('Installed version ' + $Version + '; managed files=' + $files.Count + '; offline V3 plan and portable export passed; native execution not run. Reconnect MCP; no NX hot reload.')
    }
} catch {
    $failure = $_
    if ($CleanReplace -and $replaceStarted) {
        $cleanup=$false
        throw ('CleanReplace failed after old app removal began. No old-version rollback exists; preserve ' + $stage + ' and investigate before retrying: ' + $failure.Exception.Message)
    }
    $rollbackErrors = [Collections.Generic.List[string]]::new()
    for ($i=$applied.Count-1; $i -ge 0; $i--) {
        $entry = $applied[$i]
        try {
            Assert-NoReparse $entry.target
            if ($entry.existed) {
                if (-not (Test-Path -LiteralPath $entry.target -PathType Leaf) -or -not (Equal-FileBytes $entry.target $entry.backup)) {
                    Copy-Item -LiteralPath $entry.backup -Destination $entry.target -Force
                }
            }
            elseif (Test-Path -LiteralPath $entry.target -PathType Leaf) { Remove-Item -LiteralPath $entry.target -Force }
        } catch { $rollbackErrors.Add($_.Exception.Message) }
    }
    if ($rollbackErrors.Count) { $cleanup=$false; throw ('Install failed; rollback incomplete. Preserve ' + $stage + ': ' + ($rollbackErrors -join '; ')) }
    throw $failure
} finally {
    if ($journalGate) { $journalGate.Dispose() }
    if ($launchMutex) { if ($mutexAcquired) { $launchMutex.ReleaseMutex() }; $launchMutex.Dispose() }
    if ($lock) { $lock.Dispose() }
    if ($cleanup -and (Test-Path -LiteralPath $stage)) {
        $actual = (Resolve-Path -LiteralPath $stage).Path
        if (-not [string]::Equals([IO.Path]::GetDirectoryName($actual),$install,[StringComparison]::OrdinalIgnoreCase) -or
            -not [IO.Path]::GetFileName($actual).StartsWith('.v3-install-stage-',[StringComparison]::Ordinal)) { throw 'Unsafe staging cleanup path; retained.' }
        Assert-NoReparse $actual
        Remove-Item -LiteralPath $actual -Recurse -Force
    }
}
