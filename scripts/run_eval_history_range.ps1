param(
  [string]$Field = "반도체",
  [ValidateSet("monthly","daily")]
  [string]$Frequency = "monthly",
  [Parameter(Mandatory=$true)][string]$Start,
  [Parameter(Mandatory=$true)][string]$End,
  [Parameter(Mandatory=$true)][string]$UniverseCsv,
  [Parameter(Mandatory=$true)][string]$RunId,
  [string]$HistoryCsv = "",
  [int]$Limit = 0,
  [switch]$WriteSheets
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = ((Resolve-Path ".\src_eval").Path + ";" + (Resolve-Path ".\src").Path)

$argsList = @(
  ".\scripts\run_eval_history_range.py",
  "--field", $Field,
  "--frequency", $Frequency,
  "--start", $Start,
  "--end", $End,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId
)
if ($HistoryCsv -ne "") { $argsList += @("--history-csv", $HistoryCsv) }
if ($Limit -gt 0) { $argsList += @("--limit", [string]$Limit) }
if ($WriteSheets) { $argsList += @("--write-sheets") }

python @argsList
