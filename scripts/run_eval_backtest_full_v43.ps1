param(
    [Parameter(Mandatory=$false)][string]$Field = "반도체",
    [Parameter(Mandatory=$false)][ValidateSet("monthly", "daily")][string]$Frequency = "monthly",
    [Parameter(Mandatory=$true)][string]$Start,
    [Parameter(Mandatory=$true)][string]$End,
    [Parameter(Mandatory=$true)][string]$UniverseCsv,
    [Parameter(Mandatory=$false)][string]$RunId = "bt_v43",
    [Parameter(Mandatory=$false)][string]$RunStamp = "",
    [Parameter(Mandatory=$false)][string]$Agents = "data-intake,finance,valuation,tech,market,issue,macro,auditor,chair",
    [Parameter(Mandatory=$false)][int]$TimeoutSec = 900,
    [Parameter(Mandatory=$false)][int]$Limit = 0,
    [Parameter(Mandatory=$false)][switch]$WriteSheets,
    [Parameter(Mandatory=$false)][switch]$SkipRealPipeline,
    [Parameter(Mandatory=$false)][switch]$SkipSourceMaterialize,
    [Parameter(Mandatory=$false)][switch]$KeepLocalOutputs,
    [Parameter(Mandatory=$false)][switch]$StopOnError
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$srcEval = (Resolve-Path ".\src_eval").Path
$srcMain = (Resolve-Path ".\src").Path
$env:PYTHONPATH = $srcEval + [System.IO.Path]::PathSeparator + $srcMain

$argsList = @(
    ".\scripts\run_eval_backtest_full_v43.py",
    "--field", $Field,
    "--frequency", $Frequency,
    "--start", $Start,
    "--end", $End,
    "--universe-csv", $UniverseCsv,
    "--run-id", $RunId,
    "--agents", $Agents,
    "--timeout-sec", $TimeoutSec.ToString()
)
if ($RunStamp -ne "") { $argsList += @("--run-stamp", $RunStamp) }
if ($Limit -gt 0) { $argsList += @("--limit", $Limit.ToString()) }
if ($WriteSheets) { $argsList += "--write-sheets" }
if ($SkipRealPipeline) { $argsList += "--skip-real-pipeline" }
if ($SkipSourceMaterialize) { $argsList += "--skip-source-materialize" }
if ($KeepLocalOutputs) { $argsList += "--keep-local-outputs" }
if ($StopOnError) { $argsList += "--stop-on-error" }

python @argsList
