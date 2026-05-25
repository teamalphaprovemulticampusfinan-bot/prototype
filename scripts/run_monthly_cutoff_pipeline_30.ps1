param(
  [string]$Field = "반도체",
  [string]$Start = "2025-01",
  [string]$End = "",
  [string]$UniverseCsv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",
  [string]$RunId = "monthly_cutoff_30",
  [int]$Limit = 0,
  [int]$TimeoutSec = 1200,
  [switch]$ContinueOnError,
  [switch]$SkipNetwork,
  [switch]$ForceFetch,
  [switch]$IncludeTechCutoff
)

Set-Location (Split-Path -Parent $PSScriptRoot)
chcp 65001 | Out-Null
$env:PYTHONPATH = (Resolve-Path .\src).Path
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$argsList = @(
  "scripts\run_monthly_cutoff_pipeline_30.py",
  "--field", $Field,
  "--start", $Start,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId,
  "--timeout-sec", [string]$TimeoutSec
)
if ($End -ne "") { $argsList += @("--end", $End) }
if ($Limit -gt 0) { $argsList += @("--limit", [string]$Limit) }
if ($ContinueOnError) { $argsList += "--continue-on-error" }
if ($SkipNetwork) { $argsList += "--skip-network" }
if ($ForceFetch) { $argsList += "--force-fetch" }
if ($IncludeTechCutoff) { $argsList += "--include-tech-cutoff" }

python @argsList
