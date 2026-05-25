param(
  [string]$CompanyDir = "nepes",
  [string]$Company = "nepes",
  [switch]$NoGdelt,
  [switch]$NoSerper,
  [int]$GdeltIntervalSec = 6,
  [int]$Gdelt429SleepSec = 0,
  [int]$GdeltMaxRecords = 5
)

$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if ($NoGdelt) {
  $env:MACRO_ENABLE_GDELT = "0"
} else {
  $env:MACRO_ENABLE_GDELT = "1"
}

if ($NoSerper) {
  $env:MACRO_ENABLE_SERPER = "0"
}

$env:MACRO_GDELT_MIN_INTERVAL_SEC = "$GdeltIntervalSec"
$env:MACRO_GDELT_429_SLEEP_SEC = "$Gdelt429SleepSec"
$env:MACRO_GDELT_MAXRECORDS = "$GdeltMaxRecords"
$env:MACRO_GDELT_RETRY_ON_429 = "0"
$env:MACRO_GDELT_PRE_WAIT = "0"
$env:MACRO_REUSE_TODAY_OUTPUTS = "1"
$env:MACRO_SMM_PUBLIC_TRY = "0"

Write-Host "================================================================================"
Write-Host "Macro intake check"
Write-Host "================================================================================"
Write-Host "CompanyDir=$CompanyDir"
Write-Host "Company=$Company"
Write-Host "MACRO_ENABLE_GDELT=$env:MACRO_ENABLE_GDELT"
Write-Host "MACRO_ENABLE_SERPER=$env:MACRO_ENABLE_SERPER"
Write-Host "MACRO_GDELT_MIN_INTERVAL_SEC=$env:MACRO_GDELT_MIN_INTERVAL_SEC"
Write-Host "MACRO_GDELT_429_SLEEP_SEC=$env:MACRO_GDELT_429_SLEEP_SEC"
Write-Host "MACRO_GDELT_MAXRECORDS=$env:MACRO_GDELT_MAXRECORDS"
Write-Host "MACRO_GDELT_RETRY_ON_429=$env:MACRO_GDELT_RETRY_ON_429"
Write-Host "MACRO_REUSE_TODAY_OUTPUTS=$env:MACRO_REUSE_TODAY_OUTPUTS"
Write-Host "================================================================================"

python main.py intake --company-dir $CompanyDir --company $Company --agents macro --stop-on-error

Write-Host "================================================================================"
Write-Host "Latest macro output files"
Write-Host "================================================================================"

$macroDir = Join-Path (Get-Location) "data\_global_common\macro"
if (Test-Path $macroDir) {
  Get-ChildItem $macroDir -Filter "*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 20 Name, Length, LastWriteTime | Format-Table -AutoSize
} else {
  Write-Host "Macro directory not found: $macroDir"
}

Write-Host "================================================================================"
Write-Host "Workspace check"
Write-Host "================================================================================"
Write-Host "workspace exists? $(Test-Path .\workspace)"
