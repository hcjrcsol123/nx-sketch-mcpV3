param(
 [Parameter(Mandatory)][string]$RunDirectory,
 [Parameter(Mandatory)][string]$SourceRun,
 [string]$BlankTemplate = 'workspace/v3/p4/P4-20261118-17/fixture/default-composition.prt',
 [string]$BuildRoot = 'workspace/build/current/M2',
 [string]$PythonExe = 'python',
 [switch]$AuthorizedForNative
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(!$AuthorizedForNative){throw 'STOP: root must schedule and authorize this run.'}
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$run=[IO.Path]::GetFullPath($RunDirectory);$sourceRun=[IO.Path]::GetFullPath($SourceRun)
$blank=[IO.Path]::GetFullPath($BlankTemplate);$build=[IO.Path]::GetFullPath($BuildRoot)
$pythonPath=(Get-Command $PythonExe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
foreach($p in @((Join-Path $sourceRun 'product-source/summary.json'),(Join-Path $sourceRun 'shutdown.json'),(Join-Path $sourceRun 'preload-claim.txt'),$blank,(Join-Path $build 'M2Startup.dll'))){if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "STOP: missing input $p"}}
if((Test-Path -LiteralPath $run) -or !(Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($run)) -PathType Container)){throw 'STOP: run must be new with an existing parent.'}
if(Get-Process ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue){throw 'STOP: physical lane occupied.'}
[void](New-Item -ItemType Directory -Path $run -ErrorAction Stop)
$claim=Join-Path $run 'target-claim.txt'
[IO.File]::WriteAllText($claim,"Scoped reviewed-disk-source target, not general recognition. Start $([DateTimeOffset]::Now.ToString('o'))`r`n")
$vars=@('UGII_BASE_DIR','UGII_USER_DIR','NX_SKETCH_MCP_M2_ENTRY_DLL','NX_SKETCH_MCP_M2_PIPE','NX_SKETCH_MCP_M2_TOKEN_FILE');$previous=@{}
foreach($name in $vars){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
try {
 $fixtureDir=Join-Path $run 'fixture';[void](New-Item -ItemType Directory -Path $fixtureDir)
 $fixture=Join-Path $fixtureDir 'blank.prt';$target=Join-Path $fixtureDir 'reviewed-result.prt'
 $src=[IO.File]::Open($blank,'Open','Read','Read')
 try {$dst=[IO.File]::Open($fixture,'CreateNew','Write','None');try{$src.CopyTo($dst)}finally{$dst.Dispose()}}finally{$src.Dispose()}
 $network=Join-Path $run 'network-prelaunch.json'
 & (Join-Path $root 'tools/verify-m2-local-network.ps1') -NxExe 'C:\0sf\ug\NXBIN\ugraf.exe' -OutputPath $network | Out-Null
 $net=Get-Content -LiteralPath $network -Raw -Encoding UTF8 | ConvertFrom-Json
 if($net.inbound_isolation_configured -ne $true){throw 'STOP: network isolation not established.'}
 $startup=Join-Path $run 'isolated/profile/startup';[void](New-Item -ItemType Directory -Path $startup -Force)
 [IO.File]::Copy((Join-Path $build 'M2Startup.dll'),(Join-Path $startup 'M2Startup.dll'),$false)
 $isolated=. (Join-Path $root 'tools/prepare-m2-session.ps1') -BuildRoot $build -SessionRoot (Join-Path $run 'isolated/sessions') -PythonExe $pythonPath
 $config=$isolated.ConfigPath;$configData=Get-Content -LiteralPath $config -Raw -Encoding UTF8 | ConvertFrom-Json
 $configData.timeout_seconds=120.0
 [IO.File]::WriteAllText($config,($configData | ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
 $env:UGII_BASE_DIR='C:\0sf\ug';$env:UGII_USER_DIR=[IO.Path]::GetDirectoryName($startup);$env:NX_SKETCH_MCP_M2_ENTRY_DLL=Join-Path $build 'M2Entry.dll'
 if(Get-Process ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue){throw 'STOP: lane occupied before launch.'}
 $exe='C:\0sf\ug\NXBIN\ugraf.exe'
 # NX is the interactive application controlled by the scoped UI helpers.
 $proc=Start-Process -FilePath $exe -WorkingDirectory $run -WindowStyle Normal -PassThru
 $launch=@{pid=$proc.Id;process_start_utc=$proc.StartTime.ToUniversalTime().ToString('o');start_ticks=[string]$proc.StartTime.ToUniversalTime().Ticks;exe=$exe;copied_part=$fixture;test_stage='M5'}
 $launchPath=Join-Path $run 'launch.json';[IO.File]::WriteAllText($launchPath,($launch|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
 [IO.File]::AppendAllText($claim,"Started dedicated NX PID $($launch.pid), start ticks $($launch.start_ticks), independent fixture $fixture.`r`n")
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
 [IO.File]::AppendAllText($claim,"Submitted fixture through PID-scoped verified file-open dialog; actual work-part identity and blank state remain subject to takeover and inspection.`r`n")
 $modeling=-join @([char]0x5efa,[char]0x6a21);$basic=-join @([char]0x57fa,[char]0x672c,[char]0x73af,[char]0x5883);$timer=[Diagnostics.Stopwatch]::StartNew();$ready=$false
 while(!$proc.HasExited -and $timer.ElapsedMilliseconds -lt 55000){$proc.Refresh();if($proc.MainWindowTitle.StartsWith('Designcenter') -and ($proc.MainWindowTitle.Contains($modeling) -or $proc.MainWindowTitle.Contains($basic)) -and $proc.Responding){$ready=$true;break};Start-Sleep -Milliseconds 250}
 if(!$ready){throw 'STOP: modeling window did not become ready after the verified open dialog.'}
 [IO.File]::WriteAllText((Join-Path $run 'open-ready.json'),(@{pid=$launch.pid;start_ticks=$launch.start_ticks;window_title=$proc.MainWindowTitle;elapsed_ms=$timer.ElapsedMilliseconds;note='Modeling window observed; actual part path and full load require takeover.'}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
 $evidence=Join-Path $run 'product-target';[void](New-Item -ItemType Directory -Path $evidence)
 & $pythonPath -B (Join-Path $PSScriptRoot 'run_reviewed_target.py') --pid $launch.pid --start-ticks $launch.start_ticks --source-run $sourceRun --fixture $fixture --target $target --config $config --evidence-dir $evidence
 if($LASTEXITCODE -ne 0){throw 'STOP: target run failed or UNKNOWN; do not return, replay or close automatically.'}
 & (Join-Path $root 'tools/close-m2-test-nx.ps1') -LaunchReport $launchPath -OutputPath (Join-Path $run 'shutdown.json') -SavedPartPath $target | Out-Null
 $postTimer=[Diagnostics.Stopwatch]::StartNew()
 do {$active=@(Get-Process ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue);if(!$active.Count -or @($active|Where-Object {$_.ProcessName -in @('ugraf','run_journal')}).Count){break};Start-Sleep -Milliseconds 200} while($postTimer.ElapsedMilliseconds -lt 10000)
 [IO.File]::WriteAllText((Join-Path $run 'postclose-processes.json'),(@{observed_at=[DateTimeOffset]::Now.ToString('o');processes=@($active|ForEach-Object {@{pid=$_.Id;name=$_.ProcessName}})}|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
 if($active.Count){throw 'STOP: relevant process remains active; inspect recorded identities manually.'}
 [IO.File]::AppendAllText($claim,"Scoped target created, save/reopen and safe return completed; dedicated NX normally exited. Separate G/P/persistence evidence remains required. End $([DateTimeOffset]::Now.ToString('o'))`r`n")
} catch {[IO.File]::AppendAllText($claim,"STOP; preserve evidence, inspect state, no automatic replay or close: $($_.Exception.Message)`r`n");throw}
finally{foreach($name in $vars){[Environment]::SetEnvironmentVariable($name,$previous[$name],'Process')}}
