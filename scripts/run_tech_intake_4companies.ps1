param(
  [int]$MaxPatents = 0,
  [double]$SleepSec = 0.6,
  [int]$Timeout = 60,
  [switch]$ForceFetch,
  [switch]$SkipNetwork,
  [switch]$SkipAgent,
  [switch]$StopOnError,
  [string[]]$Only = @()
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$argsList = @(
  "scripts/run_tech_intake_4companies.py",
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
Write-Host "Tech Intake - 4 companies"
Write-Host "================================================================================"
Write-Host "MaxPatents = $MaxPatents  (0 = all patents from normalized CSV)"
Write-Host "SleepSec   = $SleepSec"
Write-Host "Timeout    = $Timeout"
Write-Host "ForceFetch = $ForceFetch"
Write-Host "SkipNetwork= $SkipNetwork"
Write-Host "SkipAgent  = $SkipAgent"
Write-Host "Only       = $($Only -join ', ')"
Write-Host "================================================================================"

python @argsList
