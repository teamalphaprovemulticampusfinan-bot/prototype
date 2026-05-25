param(
  [int]$MaxPatents = 0,
  [double]$SleepSec = 0.6,
  [int]$Timeout = 60,
  [string[]]$Only = @(),
  [switch]$ForceFetch,
  [switch]$SkipNetwork,
  [switch]$SkipAgent,
  [switch]$StopOnError
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$argsList = @(
  ".\scripts\run_tech_intake_5companies.py",
  "--max-patents", "$MaxPatents",
  "--sleep-sec", "$SleepSec",
  "--timeout", "$Timeout"
)

foreach ($item in $Only) {
  if ($item -and $item.Trim().Length -gt 0) {
    $argsList += @("--only", $item.Trim())
  }
}
if ($ForceFetch) { $argsList += "--force-fetch" }
if ($SkipNetwork) { $argsList += "--skip-network" }
if ($SkipAgent) { $argsList += "--skip-agent" }
if ($StopOnError) { $argsList += "--stop-on-error" }

Write-Host "================================================================================"
Write-Host "AlphaProve Tech Intake 5 Companies"
Write-Host "MaxPatents=$MaxPatents"
Write-Host "SleepSec=$SleepSec"
Write-Host "Timeout=$Timeout"
Write-Host "================================================================================"

python @argsList
exit $LASTEXITCODE
