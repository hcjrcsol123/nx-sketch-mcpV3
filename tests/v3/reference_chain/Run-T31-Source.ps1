param(
 [Parameter(Mandatory)][string]$RunDirectory,
 [string]$BuildRoot = 'workspace/build/current/M2',
 [string]$PythonExe = 'python',
 [string]$SourcePart = '',
 [switch]$IncludeInventory,
 [switch]$ReviewedSource,
 [switch]$AuthorizedForNative
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if (!$AuthorizedForNative) { throw 'STOP: root must schedule and authorize this run.' }
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$run=[IO.Path]::GetFullPath($RunDirectory)
$build=[IO.Path]::GetFullPath($BuildRoot)
$source=if($SourcePart){[IO.Path]::GetFullPath($SourcePart)}else{Join-Path $root ('tests/'+[string]::Concat([char]0x5916,[char]0x7403,[char]0x53c9)+'.prt')}
$pythonPath=(Get-Command $PythonExe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
if (!(Test-Path -LiteralPath $source -PathType Leaf) -or !(Test-Path -LiteralPath (Join-Path $build 'M2Startup.dll') -PathType Leaf) -or
    (Test-Path -LiteralPath $run) -or
    !(Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($run)) -PathType Container)) { throw 'STOP: inputs missing or run directory already exists.' }
if (Get-Process ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue) { throw 'STOP: physical lane occupied.' }
[void](New-Item -ItemType Directory -Path $run -ErrorAction Stop)
$claim=Join-Path $run 'preload-claim.txt'
[IO.File]::WriteAllText($claim,"T31 source run started $([DateTimeOffset]::Now.ToString('o'))`r`n")
$sourceLock=$null; $copyLock=$null
$vars=@('UGII_BASE_DIR','UGII_USER_DIR','NX_SKETCH_MCP_M2_ENTRY_DLL','NX_SKETCH_MCP_M2_PIPE','NX_SKETCH_MCP_M2_TOKEN_FILE');$previous=@{}
foreach($name in $vars){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
function Equal-Streams([IO.Stream]$a,[IO.Stream]$b) {
 if($a.Length -ne $b.Length){return $false}
 $a.Position=0;$b.Position=0;$x=[byte[]]::new(1048576);$y=[byte[]]::new(1048576)
 while(($n=$a.Read($x,0,$x.Length)) -gt 0){$offset=0;while($offset -lt $n){$m=$b.Read($y,$offset,$n-$offset);if($m -le 0){return $false};$offset+=$m};for($i=0;$i -lt $n;$i++){if($x[$i] -ne $y[$i]){return $false}}}
 return $true
}
try {
 $sourceLock=[IO.File]::Open($source,'Open','Read','Read')
 $copy=Join-Path $run 'reference-copy.prt'
 $out=[IO.File]::Open($copy,'CreateNew','Write','None')
 try {$sourceLock.CopyTo($out)} finally {$out.Dispose()}
 $copyLock=[IO.File]::Open($copy,'Open','Read','Read')
 if(!(Equal-Streams $sourceLock $copyLock)){throw 'STOP: source and independent copy differ.'}
 [IO.File]::AppendAllText($claim,"Reference and new independent copy byte-equal; both read handles deny writes/deletion before NX launch and remain held until after analysis and exit.`r`n")
 $network=Join-Path $run 'network-prelaunch.json'
 & (Join-Path $root 'tools/verify-m2-local-network.ps1') -NxExe 'C:\0sf\ug\NXBIN\ugraf.exe' -OutputPath $network | Out-Null
 $state=Get-Content -LiteralPath $network -Raw -Encoding UTF8 | ConvertFrom-Json
 if($state.inbound_isolation_configured -ne $true){throw 'STOP: network isolation not established.'}
 $startup=Join-Path $run 'isolated/profile/startup';[void](New-Item -ItemType Directory -Path $startup -Force)
 [IO.File]::Copy((Join-Path $build 'M2Startup.dll'),(Join-Path $startup 'M2Startup.dll'),$false)
 $isolated=. (Join-Path $root 'tools/prepare-m2-session.ps1') -BuildRoot $build -SessionRoot (Join-Path $run 'isolated/sessions') -PythonExe $pythonPath
 $config=$isolated.ConfigPath
 $configData=Get-Content -LiteralPath $config -Raw -Encoding UTF8 | ConvertFrom-Json
 $configData.timeout_seconds=120.0
 [IO.File]::WriteAllText($config,($configData | ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
 $env:UGII_BASE_DIR='C:\0sf\ug';$env:UGII_USER_DIR=[IO.Path]::GetDirectoryName($startup);$env:NX_SKETCH_MCP_M2_ENTRY_DLL=Join-Path $build 'M2Entry.dll'
 if(Get-Process ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue){throw 'STOP: lane occupied before launch.'}
 $exe='C:\0sf\ug\NXBIN\ugraf.exe'
 # NX is the interactive application controlled by the scoped UI helpers.
 $proc=Start-Process -FilePath $exe -WorkingDirectory $run -WindowStyle Normal -PassThru
 $launch=@{pid=$proc.Id;process_start_utc=$proc.StartTime.ToUniversalTime().ToString('o');start_ticks=[string]$proc.StartTime.ToUniversalTime().Ticks;exe=$exe;copied_part=$copy;test_stage='M5'}
 $launchPath=Join-Path $run 'launch.json'
 [IO.File]::WriteAllText($launchPath,($launch | ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
 [IO.File]::AppendAllText($claim,"Started dedicated NX PID $($launch.pid), start ticks $($launch.start_ticks); locked copy will be opened using the scoped verified NX dialog.`r`n")
 [void]$proc.WaitForInputIdle(30000)
 $timer=[Diagnostics.Stopwatch]::StartNew()
 while(!(Test-Path -LiteralPath $isolated.TokenFile -PathType Leaf) -and !$proc.HasExited -and $timer.ElapsedMilliseconds -lt 60000){Start-Sleep -Milliseconds 250;$proc.Refresh()}
 if($proc.HasExited -or !(Test-Path -LiteralPath $isolated.TokenFile -PathType Leaf)){throw 'STOP: bridge startup not established; inspect process manually.'}
 $windowTimer=[Diagnostics.Stopwatch]::StartNew();$ready=$false
 while(!$proc.HasExited -and $windowTimer.ElapsedMilliseconds -lt 45000){
  $proc.Refresh();if($proc.MainWindowHandle -ne [IntPtr]::Zero -and $proc.MainWindowTitle.StartsWith('Designcenter') -and $proc.Responding){$ready=$true;break}
  Start-Sleep -Milliseconds 250
 }
 if(!$ready){throw 'STOP: dedicated interactive NX main window did not become ready.'}
 & (Join-Path $root 'tools/nx_ui/nx-ui.ps1') -NxPid $launch.pid -Action OpenModal -OutputPath (Join-Path $run 'open-modal.json') | Out-Null
 & (Join-Path $root 'tools/m2-nx-test-ui.ps1') -LaunchReport $launchPath -Action OpenPart -OutputPath (Join-Path $run 'open-part.json') | Out-Null
 [IO.File]::AppendAllText($claim,"Submitted the locked independent copy through the PID-scoped, verified file-open dialog; actual work-part identity and full load remain subject to takeover.`r`n")
 $modeling=-join @([char]0x5efa,[char]0x6a21);$timer=[Diagnostics.Stopwatch]::StartNew();$ready=$false
 while(!$proc.HasExited -and $timer.ElapsedMilliseconds -lt 55000){$proc.Refresh();if($proc.MainWindowTitle.StartsWith('Designcenter') -and $proc.MainWindowTitle.Contains($modeling) -and $proc.Responding){$ready=$true;break};Start-Sleep -Milliseconds 250}
 if(!$ready){throw 'STOP: modeling window did not become ready after the verified open dialog.'}
 [IO.File]::WriteAllText((Join-Path $run 'open-ready.json'),(@{pid=$launch.pid;start_ticks=$launch.start_ticks;window_title=$proc.MainWindowTitle;elapsed_ms=$timer.ElapsedMilliseconds;note='Modeling window observed; actual part path and full load require takeover.'}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
 $evidence=Join-Path $run 'product-source';[void](New-Item -ItemType Directory -Path $evidence -ErrorAction Stop)
 $clientArgs=@('--pid',$launch.pid,'--start-ticks',$launch.start_ticks,'--source',$source,'--part',$copy,'--config',$config,'--evidence-dir',$evidence)
 if($IncludeInventory){$clientArgs+='--include-inventory'}
 if($ReviewedSource -or !$SourcePart){$clientArgs+='--reviewed-source'}
 & $pythonPath -B (Join-Path $PSScriptRoot 'run_product_reference.py') @clientArgs
 if($LASTEXITCODE -ne 0){throw 'STOP: source product run failed or UNKNOWN; do not return, replay, or close automatically.'}
 $result=Get-Content -LiteralPath (Join-Path $evidence 'summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 if($result.status -ne 'SOURCE_ANALYZED_TARGET_BLOCKED'){throw 'STOP: unexpected source result.'}
 if(!(Equal-Streams $sourceLock $copyLock)){throw 'STOP: source and copy differ after analysis.'}
 [IO.File]::AppendAllText($claim,"Product source analysis and safe return completed; byte equality maintained while pre-load locks still held.`r`n")
 & (Join-Path $root 'tools/close-m2-test-nx.ps1') -LaunchReport $launchPath -OutputPath (Join-Path $run 'shutdown.json') | Out-Null
 if(Get-Process -Id $launch.pid -ErrorAction SilentlyContinue){throw 'STOP: launched PID still active; inspect manually.'}
 $postTimer=[Diagnostics.Stopwatch]::StartNew()
 do {$active=@(Get-Process ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue);if(!$active.Count -or @($active|Where-Object {$_.ProcessName -in @('ugraf','run_journal')}).Count){break};Start-Sleep -Milliseconds 200} while($postTimer.ElapsedMilliseconds -lt 10000)
 [IO.File]::WriteAllText((Join-Path $run 'postclose-processes.json'),(@{observed_at=[DateTimeOffset]::Now.ToString('o');processes=@($active|ForEach-Object {@{pid=$_.Id;name=$_.ProcessName}})}|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
 if($active.Count){throw 'STOP: relevant process remains active; inspect recorded identities manually.'}
 if(!(Equal-Streams $sourceLock $copyLock)){throw 'STOP: source and copy differ after shutdown.'}
 [IO.File]::AppendAllText($claim,"Normal process exit observed; original and loaded copy remain byte-equal; source locks held continuously from before launch through exit. End $([DateTimeOffset]::Now.ToString('o')). No claim of exhaustive geometry equality.`r`n")
} catch {
 [IO.File]::AppendAllText($claim,"STOP; preserve evidence, investigate state, no automatic replay or close. On supervisor exit locks are released even if NX remains active; uninterrupted preload-through-exit proof is absent. $($_.Exception.Message)`r`n")
 throw
} finally {if($null -ne $copyLock){$copyLock.Dispose()};if($null -ne $sourceLock){$sourceLock.Dispose()};foreach($name in $vars){[Environment]::SetEnvironmentVariable($name,$previous[$name],'Process')}}
