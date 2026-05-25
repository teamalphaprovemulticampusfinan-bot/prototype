param(
  [Parameter(Mandatory=$true)][string]$Field,
  [ValidateSet("monthly","daily")][string]$Frequency = "monthly",
  [Parameter(Mandatory=$true)][string]$Start,
  [Parameter(Mandatory=$true)][string]$End,
  [Parameter(Mandatory=$true)][string]$UniverseCsv,
  [Parameter(Mandatory=$true)][string]$RunId,
  [int]$Limit = 0,
  [int]$TimeoutSec = 900,
  [string]$Agents = "",
  [switch]$WriteSheets,
  [switch]$StopOnError,
  [switch]$SkipRealPipeline,
  [switch]$KeepLocalOutputs
)

Set-Location (Split-Path -Parent $PSScriptRoot)
chcp 65001 | Out-Null
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH=(Resolve-Path ".\src_eval").Path + ";" + (Resolve-Path ".\src").Path

$argsList = @(
  ".\scripts\run_eval_history_real_pipeline_v30.py",
  "--field", $Field,
  "--frequency", $Frequency,
  "--start", $Start,
  "--end", $End,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId,
  "--timeout-sec", "$TimeoutSec"
)

if ($Limit -gt 0) { $argsList += @("--limit", "$Limit") }
if ($Agents -ne "") { $argsList += @("--agents", $Agents) }
if ($WriteSheets) { $argsList += "--write-sheets" }
if ($StopOnError) { $argsList += "--stop-on-error" }
if ($SkipRealPipeline) { $argsList += "--skip-real-pipeline" }
if ($KeepLocalOutputs) { $argsList += "--keep-local-outputs" }

python @argsList
exit $LASTEXITCODE
