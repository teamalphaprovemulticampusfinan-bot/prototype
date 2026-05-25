[CmdletBinding()]
param(
  [string]$Field = "반도체",
  [string]$Frequency = "monthly",
  [string]$Start,
  [string]$End,
  [string]$UniverseCsv,
  [string]$RunId,
  [int]$Limit = 0,
  [int]$TimeoutSec = 900,
  [string]$HoldPolicy = "directional_argmax",
  [switch]$StopOnError,
  [switch]$WriteSheets,
  [switch]$SkipRealPipeline,
  [switch]$KeepLocalOutputs
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Start)) {
  throw "Start is required. Example: -Start 2025-01"
}
if ([string]::IsNullOrWhiteSpace($End)) {
  throw "End is required. Example: -End 2026-01"
}
if ([string]::IsNullOrWhiteSpace($UniverseCsv)) {
  throw "UniverseCsv is required."
}
if ([string]::IsNullOrWhiteSpace($RunId)) {
  throw "RunId is required."
}
if (($Frequency -ne "monthly") -and ($Frequency -ne "daily")) {
  throw "Frequency must be monthly or daily."
}

chcp 65001 | Out-Null

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$srcEvalPath = (Resolve-Path ".\src_eval").Path
$srcPath = (Resolve-Path ".\src").Path
$env:PYTHONPATH = "$srcEvalPath;$srcPath"

$env:ALPHAPROVE_EVAL_HISTORY = "1"
$env:ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED = "1"
$env:ALPHAPROVE_FIELD = $Field
$env:ALPHAPROVE_EVAL_FREQUENCY = $Frequency

$argsList = @(
  ".\scripts\run_eval_backtest_full_v38.py",
  "--field", $Field,
  "--frequency", $Frequency,
  "--start", $Start,
  "--end", $End,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId,
  "--timeout-sec", "$TimeoutSec",
  "--hold-policy", $HoldPolicy
)

if ($Limit -gt 0) {
  $argsList += @("--limit", "$Limit")
}
if ($StopOnError) {
  $argsList += "--stop-on-error"
}
if ($WriteSheets) {
  $argsList += "--write-sheets"
}
if ($SkipRealPipeline) {
  $argsList += "--skip-real-pipeline"
}
if ($KeepLocalOutputs) {
  $argsList += "--keep-local-outputs"
}

Write-Host "[v38a] PYTHONPATH=$env:PYTHONPATH"
Write-Host "[v38a] python $($argsList -join ' ')"

& python @argsList
exit $LASTEXITCODE
