param(
  [switch]$SkipNetwork,
  [int]$Years = 5
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$argsList = @("scripts\run_valuation_5companies.py", "--years", "$Years")
if ($SkipNetwork) { $argsList += "--skip-network" }
python @argsList
