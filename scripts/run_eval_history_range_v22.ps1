param(
  [string]$Field = "반도체",
  [ValidateSet("monthly","daily")]
  [string]$Frequency = "monthly",
  [Parameter(Mandatory=$true)][string]$Start,
  [Parameter(Mandatory=$true)][string]$End,
  [Parameter(Mandatory=$true)][string]$UniverseCsv,
  [Parameter(Mandatory=$true)][string]$RunId,
  [int]$Limit = 0
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$evalSrc = (Resolve-Path ".\src\eval").Path
$src = (Resolve-Path ".\src").Path
$env:PYTHONPATH = $evalSrc + ";" + $src

$argsList = @(
  ".\scripts\run_eval_history_range_v22.py",
  "--field", $Field,
  "--frequency", $Frequency,
  "--start", $Start,
  "--end", $End,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId
)
if ($Limit -gt 0) {
  $argsList += @("--limit", [string]$Limit)
}
python @argsList
