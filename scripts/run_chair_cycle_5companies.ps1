param(
  [string[]]$Only = @(),
  [switch]$NoIntake,
  [switch]$StopOnError
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$argsList = @(".\scripts\run_chair_cycle_5companies.py")

foreach ($item in $Only) {
  if ($item -and $item.Trim().Length -gt 0) {
    $argsList += @("--only", $item.Trim())
  }
}
if ($NoIntake) { $argsList += "--no-intake" }
if ($StopOnError) { $argsList += "--stop-on-error" }

Write-Host "================================================================================"
Write-Host "AlphaProve Full Chair Cycle: Data Intake -> Agents -> Auditor -> Chair"
Write-Host "================================================================================"

python @argsList
exit $LASTEXITCODE
