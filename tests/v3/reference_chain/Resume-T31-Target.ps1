param(
 [Parameter(Mandatory)][string]$RunDirectory,
 [Parameter(Mandatory)][string]$SourceRun,
 [string]$PythonExe='python',
 [switch]$AuthorizedForNative
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$AuthorizedForNative){throw 'STOP: root must authorize this one controlled target run.'}
$run=(Resolve-Path -LiteralPath $RunDirectory).Path;$source=(Resolve-Path -LiteralPath $SourceRun).Path
$launchPath=Join-Path $run 'launch.json';$launch=Get-Content -LiteralPath $launchPath -Raw -Encoding UTF8 | ConvertFrom-Json
$proc=Get-Process -Id $launch.pid -ErrorAction Stop
if($proc.ProcessName -ne 'ugraf' -or $proc.Path -ine $launch.exe -or [string]$proc.StartTime.ToUniversalTime().Ticks -ne [string]$launch.start_ticks){throw 'STOP: target PID, image or start epoch differs.'}
$all=@(Get-Process ugraf,run_journal,M2JsonlHelper,NxSketchMcp.BridgeHelper -ErrorAction SilentlyContinue)
if($all.Count -ne 1 -or $all[0].Id -ne $proc.Id){throw 'STOP: lane contains another relevant process.'}
$fixture=[IO.Path]::GetFullPath($launch.copied_part);$target=Join-Path ([IO.Path]::GetDirectoryName($fixture)) 'reviewed-result.prt'
$evidence=Join-Path $run 'product-target';$claim=Join-Path $run 'resume-claim.txt'
if(!(Test-Path -LiteralPath $fixture -PathType Leaf) -or (Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $evidence) -or (Test-Path -LiteralPath $claim)){throw 'STOP: fixture missing or target/evidence already exists; do not replay.'}
$configs=@(Get-ChildItem -LiteralPath (Join-Path $run 'isolated/sessions') -Filter 'mcp-config.json' -File -Recurse)
if($configs.Count -ne 1){throw 'STOP: current private session configuration is missing or ambiguous.'}
$summary=Join-Path $source 'product-source/summary.json';$reconciliation=Join-Path $source 'source-reconciliation.json'
if(!(Test-Path -LiteralPath $summary -PathType Leaf) -or !(Test-Path -LiteralPath $reconciliation -PathType Leaf)){throw 'STOP: source analysis or close reconciliation missing.'}
$python=(Get-Command $PythonExe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
[IO.File]::WriteAllText($claim,"Controlled existing target PID $($launch.pid), epoch $($launch.start_ticks), resume start $([DateTimeOffset]::Now.ToString('o')); source reconciliation and product client gates apply.`r`n")
try {
 [void](New-Item -ItemType Directory -Path $evidence -ErrorAction Stop)
 & $python -B (Join-Path $PSScriptRoot 'run_reviewed_target.py') --pid $launch.pid --start-ticks $launch.start_ticks --source-run $source --fixture $fixture --target $target --config $configs[0].FullName --evidence-dir $evidence
 if($LASTEXITCODE -ne 0){throw 'STOP: target client failed or UNKNOWN; do not replay or close automatically.'}
 [IO.File]::AppendAllText($claim,"Target client reported safe return; dedicated NX remains for root-controlled normal shutdown. End $([DateTimeOffset]::Now.ToString('o')).`r`n")
} catch {[IO.File]::AppendAllText($claim,"STOP: preserve artifacts and investigate; no automatic replay or close. $($_.Exception.Message)`r`n");throw}
