param(
 [Parameter(Mandatory=$true)][string]$NxInstallDir,
 [Parameter(Mandatory=$true)][string]$OutputDir,
 [string]$InputDir,
 [string]$Overrides,
 [string]$PythonExe = 'python',
 [switch]$Execute
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Default is a read-only preflight. This is not native verification or authorization
# to run a queued task; the operator must coordinate exclusive NX scheduling.
$bundle = [IO.Path]::GetFullPath($PSScriptRoot)
$inputRoot = if ($InputDir) { [IO.Path]::GetFullPath($InputDir) } else { $bundle }
$parameterPath = if ($Overrides) { [IO.Path]::GetFullPath($Overrides) } else { Join-Path $bundle 'parameters.json' }
$nx = [IO.Path]::GetFullPath($NxInstallDir).TrimEnd('\')
$out = [IO.Path]::GetFullPath($OutputDir).TrimEnd('\')
$runner = Join-Path $nx 'NXBIN\run_journal.exe'
$assembly = Join-Path $nx 'NXBIN\managed\NXOpen.dll'
$ufAssembly = Join-Path $nx 'NXBIN\managed\NXOpen.UF.dll'
$utilitiesAssembly = Join-Path $nx 'NXBIN\managed\NXOpen.Utilities.dll'
$ugraf = Join-Path $nx 'NXBIN\ugraf.exe'
$ugii = Join-Path $nx 'UGII'
$journal = Join-Path $inputRoot 'journal.cs'
$manifest = Join-Path $inputRoot 'manifest.json'
$required = @('journal.cs','journal.template.cs','manifest.json','profile.json','parameters.json','parameter-schema.json','logic-ir.json','bundle_runtime.py','README.md','Run-Bundle.ps1')
foreach ($name in $required) {
 $path=Join-Path $bundle $name
 if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "STOP: required bundle file missing: $path" }
}
foreach ($path in @($runner,$assembly,$ufAssembly,$utilitiesAssembly,$ugraf,$journal,$manifest,$parameterPath)) {
 if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "STOP: required file missing: $path" }
}
if (!(Test-Path -LiteralPath $ugii -PathType Container)) { throw "STOP: required UGII directory missing: $ugii" }
function Assert-Profile([string]$path) {
 Add-Type -AssemblyName System.Runtime.Serialization
 $inputStream=[IO.File]::OpenRead($path); $reader=$null
 try {
  $reader=[System.Runtime.Serialization.Json.JsonReaderWriterFactory]::CreateJsonReader($inputStream,[System.Xml.XmlDictionaryReaderQuotas]::Max)
  $document=New-Object System.Xml.XmlDocument; $document.Load($reader)
  $expected=@{release='NX V11.0'; assembly_version='11.0.0.33'; file_version='11.0.0.33'; product_version='11.0.0.33'; journal_language='C#'; ui_language_environment='simpl_chinese'}
  $root=$document.DocumentElement
  if ($root.GetAttribute('type') -cne 'object' -or $root.ChildNodes.Count -ne $expected.Count) { throw 'STOP: invalid bundle profile.' }
  foreach ($name in $expected.Keys) {
   $nodes=@($document.SelectNodes('/root/'+$name))
   if ($nodes.Count -ne 1 -or $nodes[0].GetAttribute('type') -cne 'string' -or $nodes[0].InnerText -cne $expected[$name]) { throw "STOP: unexpected bundle profile field: $name" }
  }
 } finally { if ($null -ne $reader) { $reader.Dispose() }; $inputStream.Dispose() }
}
Assert-Profile (Join-Path $bundle 'profile.json')
if (Test-Path -LiteralPath $out) { throw 'STOP: output already exists; do not overwrite or replay.' }
$parent = [IO.Path]::GetDirectoryName($out)
if (!$parent -or !(Test-Path -LiteralPath $parent -PathType Container)) { throw 'STOP: output parent directory must already exist.' }
foreach ($path in @($runner,$assembly)) {
 $v = [Diagnostics.FileVersionInfo]::GetVersionInfo($path)
 if ($v.FileVersion -cne '11.0.0.33' -or $v.ProductVersion -cne '11.0.0.33') { throw "STOP: unexpected installed NX file version: $path" }
}
try { $assemblyVersion = [Reflection.AssemblyName]::GetAssemblyName($assembly).Version.ToString() } catch { throw 'STOP: cannot read NXOpen assembly version.' }
if ($assemblyVersion -cne '11.0.0.33') { throw 'STOP: unexpected NXOpen assembly version.' }
if ($env:UGII_LANG -cne 'simpl_chinese') { throw 'STOP: UGII_LANG must be simpl_chinese, matching the observed profile.' }
# Avoid inherited user/site customizations which can inject startup code. License
# configuration is inherited and never printed. BASE/ROOT and PATH are scoped to
# the child launch and restored, so another installed NX need not be reconfigured.
foreach ($name in @('UGII_CUSTOM_DIRECTORY_FILE','UGII_USER_DIR','UGII_SITE_DIR','UGII_VENDOR_DIR')) {
 if ([Environment]::GetEnvironmentVariable($name,'Process')) { throw "STOP: inherited NX customization requires review: $name" }
}
function Assert-BundleInputs {
 $python=Get-Command $PythonExe -CommandType Application -ErrorAction Stop | Select-Object -First 1
 & $python.Source -I -B (Join-Path $bundle 'bundle_runtime.py') --overrides $parameterPath --check-input $inputRoot
 if ($LASTEXITCODE -ne 0) { throw 'STOP: bundle input does not match the selected parameters; regenerate it and do not replay an earlier failed run.' }
}
Assert-BundleInputs
function Read-ManifestCheckpoints([string]$path) {
 Add-Type -AssemblyName System.Runtime.Serialization
 $inputStream=[IO.File]::OpenRead($path); $reader=$null
 try {
  $reader=[System.Runtime.Serialization.Json.JsonReaderWriterFactory]::CreateJsonReader($inputStream,[System.Xml.XmlDictionaryReaderQuotas]::Max)
  $document=New-Object System.Xml.XmlDocument; $document.Load($reader)
  $schema=@($document.SelectNodes('/root/schema')); $checkpoints=@($document.SelectNodes('/root/checkpoints'))
  if ($schema.Count -ne 1 -or $schema[0].GetAttribute('type') -cne 'string' -or $schema[0].InnerText -cne 'ug11-compiler/1') { throw 'STOP: unsupported manifest schema.' }
  if ($checkpoints.Count -ne 1 -or $checkpoints[0].GetAttribute('type') -cne 'array') { throw 'STOP: missing checkpoint list.' }
  $entries=@($checkpoints[0].ChildNodes); if (!$entries.Count) { throw 'STOP: empty checkpoint list.' }
  $seen=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  $ids=New-Object 'System.Collections.Generic.List[string]'
  foreach ($entry in $entries) {
   $id=$entry.InnerText
   if ($entry.Name -cne 'item' -or $entry.GetAttribute('type') -cne 'string' -or $id -cnotmatch '^[A-Za-z0-9_.-]+$' -or $id -cin @('save','close','reopen','final_close') -or !$seen.Add($id)) { throw 'STOP: invalid, duplicate, or reserved checkpoint.' }
   $ids.Add($id)
  }
  return $ids.ToArray()
 } finally { if ($null -ne $reader) { $reader.Dispose() }; $inputStream.Dispose() }
}
$ids=@(Read-ManifestCheckpoints $manifest)
function Assert-NoNxProcess {
 $busy=@(Get-Process -ErrorAction Stop | Where-Object { $_.ProcessName -in @('ugraf','run_journal','M2JsonlHelper','NxSketchMcp.BridgeHelper') })
 if ($busy.Count) { throw ('STOP: NX/Journal/helper process active: '+(($busy | ForEach-Object { $_.ProcessName+':'+$_.Id }) -join ', ')) }
}
Assert-NoNxProcess
# Fail closed unless the effective inbound policy and every potentially applicable
# runner allow reduce to fixed TCP 4711/4712, as in the previously used guard.
$profileNames=@(Get-NetConnectionProfile -ErrorAction Stop | ForEach-Object { if ($_.NetworkCategory.ToString() -eq 'DomainAuthenticated') { 'Domain' } else { $_.NetworkCategory.ToString() } } | Select-Object -Unique)
if (!$profileNames.Count) { throw 'STOP: cannot determine an active firewall network profile.' }
$netshPolicy=(& netsh advfirewall show allprofiles | Out-String)
if ($LASTEXITCODE -ne 0 -or ([regex]::Matches($netshPolicy,'(?m)^State\s+ON\s*$')).Count -ne 3 -or ([regex]::Matches($netshPolicy,'(?m)^Firewall Policy\s+BlockInbound,AllowOutbound\s*$')).Count -ne 3) { throw 'STOP: effective firewall defaults could not be verified.' }
$allowPorts=[System.Collections.Generic.HashSet[int]]::new()
foreach ($rule in @(Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True -Direction Inbound -Action Allow -ErrorAction Stop)) {
 $active=$rule.Profile.ToString() -eq 'Any'
 foreach ($profileName in $profileNames) { if ($rule.Profile.ToString().Split(',').Trim() -contains $profileName) { $active=$true } }
 if (!$active -or $rule.PackageFamilyName -or $rule.PolicyAppId) { continue }
 $apps=@($rule | Get-NetFirewallApplicationFilter -ErrorAction Stop)
 $services=@($rule | Get-NetFirewallServiceFilter -ErrorAction Stop)
 if ($apps.Count -ne 1 -or $services.Count -ne 1 -or !$apps[0].Program -or !$services[0].Service) { throw ('STOP: ambiguous firewall application/service filter: '+$rule.DisplayName) }
 $app=$apps[0]; $service=$services[0]
 $program=[Environment]::ExpandEnvironmentVariables([string]$app.Program).Trim('"')
 if ($program -ine 'Any' -and $program -ine $runner -and $program -notmatch '[*?]') { continue }
 if ($service.Service -and $service.Service -ine 'Any') { continue }
 $ports=@($rule | Get-NetFirewallPortFilter -ErrorAction Stop)
 if ($ports.Count -ne 1 -or !$ports[0].Protocol -or !$ports[0].LocalPort) { throw ('STOP: ambiguous firewall port filter: '+$rule.DisplayName) }
 $port=$ports[0]
 if ($port.Protocol.ToString() -notin @('TCP','6')) { throw ('STOP: potentially applicable runner allow is not fixed TCP: '+$rule.DisplayName) }
 foreach ($number in @($port.LocalPort)) {
  $n=0
  if (![int]::TryParse([string]$number,[ref]$n) -or $n -notin @(4711,4712)) { throw ('STOP: unexpected potentially applicable runner allow: '+$rule.DisplayName) }
  [void]$allowPorts.Add($n)
 }
}
if (!$Execute) {
 Write-Output 'Preflight passed at this moment; no model was created. Native identity, port/image locks, scheduling and actual execution remain unverified. Use -Execute only after coordinating an isolated run.'
 return
}
# Recheck after preflight and reserve both IPv4/IPv6 for each permitted port. The
# process observation and these locks are not a system-wide scheduler.
$portLocks=[System.Collections.Generic.List[System.Net.Sockets.Socket]]::new()
$inputLocks=[System.Collections.Generic.List[System.IO.FileStream]]::new()
$imageLock=$null; $claim=$null; $previous=@{}
$vars=@('UGII_BASE_DIR','UGII_ROOT_DIR','PATH','UG11_EVIDENCE','UG11_MODEL')
foreach ($name in $vars) { $previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process') }
try {
 foreach ($number in $allowPorts) {
  foreach ($family in @([Net.Sockets.AddressFamily]::InterNetwork,[Net.Sockets.AddressFamily]::InterNetworkV6)) {
   $socket=[Net.Sockets.Socket]::new($family,[Net.Sockets.SocketType]::Stream,[Net.Sockets.ProtocolType]::Tcp); $portLocks.Add($socket); $socket.ExclusiveAddressUse=$true
   if ($family -eq [Net.Sockets.AddressFamily]::InterNetworkV6) { $socket.DualMode=$false; $addr=[Net.IPAddress]::IPv6Any } else { $addr=[Net.IPAddress]::Any }
   $socket.Bind([Net.IPEndPoint]::new($addr,$number))
  }
 }
 $imageLock=[IO.File]::Open($ugraf,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
 $testLock=$null
 try { $testLock=[IO.File]::Open($ugraf,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read) } catch [IO.IOException] { }
 if ($null -ne $testLock) { $testLock.Dispose(); throw 'STOP: image exclusion could not be verified.' }
 Assert-NoNxProcess
 # Prevent changes to any checked package or selected input while validation,
 # copy and execution are in progress. Existing writers cause a closed failure.
 $lockedPaths=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 foreach ($path in @($journal,$manifest,$parameterPath)+@($required | ForEach-Object { Join-Path $bundle $_ })) {
  $full=[IO.Path]::GetFullPath($path)
  if ($lockedPaths.Add($full)) { $inputLocks.Add([IO.File]::Open($full,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)) }
 }
 Assert-Profile (Join-Path $bundle 'profile.json')
 Assert-BundleInputs
 $ids=@(Read-ManifestCheckpoints $manifest)
 Assert-NoNxProcess
 if (Test-Path -LiteralPath $out) { throw 'STOP: output already exists; do not overwrite or replay.' }
 New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
 $claim=Join-Path $out 'claim.txt'
 $stream=[IO.File]::Open($claim,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None); $stream.Dispose()
 [IO.File]::WriteAllLines($claim,@('Independent UG11 bundle run; license configuration inherited and omitted.',('start: '+[DateTimeOffset]::Now.ToString('o')),('runner: '+$runner),('bundle: '+$bundle),('output: '+$out),'Process observation is not a system-wide lock; firewall and scheduling need independent review.'))
 $journalCopy=Join-Path $out 'journal.cs'; $manifestCopy=Join-Path $out 'manifest.json'; $model=Join-Path $out 'blank.prt'; $evidence=Join-Path $out 'native-evidence.tsv'; $stdout=Join-Path $out 'runner-stdout.txt'; $stderr=Join-Path $out 'runner-stderr.txt'
 [IO.File]::Copy($journal,$journalCopy,$false); [IO.File]::Copy($manifest,$manifestCopy,$false)
 $ids=@(Read-ManifestCheckpoints $manifestCopy)
 $stream=[IO.File]::Open($evidence,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read); $stream.Dispose()
 [Environment]::SetEnvironmentVariable('UGII_BASE_DIR',$nx,'Process'); [Environment]::SetEnvironmentVariable('UGII_ROOT_DIR',$ugii,'Process')
 [Environment]::SetEnvironmentVariable('PATH',(Join-Path $nx 'NXBIN')+';'+$ugii+';'+$previous['PATH'],'Process')
 [Environment]::SetEnvironmentVariable('UG11_EVIDENCE',$evidence,'Process'); [Environment]::SetEnvironmentVariable('UG11_MODEL',$model,'Process')
 & $runner $journalCopy 1> $stdout 2> $stderr
 $code=$LASTEXITCODE
 [IO.File]::AppendAllText($claim,"`nrunner exit code: $code`nend: $([DateTimeOffset]::Now.ToString('o'))`n")
 $lines=@([IO.File]::ReadAllLines($evidence) | Where-Object { $_.Length -gt 0 }); $reason=$null
 if ($code -ne 0) { $reason='nonzero runner exit' }
 elseif (!(Test-Path -LiteralPath $model -PathType Leaf)) { $reason='saved model missing' }
 elseif ($lines.Count -lt 1 -or $lines[-1] -cne "result`tPASS") { $reason='missing terminal result PASS' }
 elseif (@($lines | Where-Object { $_ -cmatch '^failure\t' }).Count) { $reason='failure record present' }
 elseif (@($lines | Where-Object { $_ -cmatch '^native_release\t' }).Count -ne 1 -or @($lines | Where-Object { $_ -ceq "native_release`tNX V11.0" }).Count -ne 1) { $reason='native release missing or ambiguous' }
 elseif (@($lines | Where-Object { $_ -cmatch '^runtime\t' }).Count -ne 1 -or @($lines | Where-Object { $_ -ceq "runtime`tassembly=11.0.0.33 file=11.0.0.33 product=11.0.0.33 language=simpl_chinese" }).Count -ne 1) { $reason='runtime identity missing or ambiguous' }
 else {
  $expected=New-Object 'System.Collections.Generic.List[string]'; foreach ($id in @($ids)+@('save','close','reopen','final_close')) { $expected.Add("checkpoint`t$id begin"); $expected.Add("checkpoint`t$id complete") }
  $actual=@($lines | Where-Object { $_ -cmatch '^checkpoint\t' })
  if ($actual.Count -ne $expected.Count) { $reason='missing or extra checkpoint' } else { for ($i=0; $i -lt $actual.Count; $i++) { if ($actual[$i] -cne $expected[$i]) { $reason='checkpoint order/content mismatch'; break } } }
  if (@($lines | Where-Object { $_ -cmatch '^result\t' }).Count -ne 1) { $reason='ambiguous result records' }
 }
 try { Assert-NoNxProcess } catch { $reason='NX/Journal/helper remains active after runner exit' }
 if ($reason) { throw "STOP: $reason. State may be UNKNOWN; preserve $out, do not replay, and investigate manually." }
 [IO.File]::AppendAllText($claim,"wrapper outcome: protocol complete; inspect raw observations, isolation and shutdown before acceptance`n")
 Write-Output "Protocol complete at $out; inspect raw observations, isolation and shutdown before acceptance."
} catch {
 if ($claim -and (Test-Path -LiteralPath $claim -PathType Leaf)) { [IO.File]::AppendAllText($claim,"wrapper exception; preserve artifacts, state may be UNKNOWN; do not replay`n") }
 throw
} finally {
 if ($null -ne $imageLock) { $imageLock.Dispose() }; foreach ($socket in $portLocks) { $socket.Dispose() }; foreach ($file in $inputLocks) { $file.Dispose() }
 foreach ($name in $vars) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
