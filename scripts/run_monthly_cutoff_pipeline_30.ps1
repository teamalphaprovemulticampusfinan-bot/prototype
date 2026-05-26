param(
  [string]$Field = "반도체",
  [string]$Start = "2025-01",
  [string]$End = "",
  [string]$UniverseCsv = "",
  [string]$OnlyCompanyDir = "",
  [string]$RunId = "monthly_cutoff_30",
  [int]$Limit = 0,
  [int]$TimeoutSec = 1800,
  [int]$RetryTimeoutSec = 2400,
  [int]$MaxRetries = 1,
  [int]$CheckpointEvery = 1,
  [double]$AutoSafeSlowRatio = 0.95,
  [int]$IntakeConcurrency = 4,
  [int]$AgentConcurrency = 6,
  [int]$MarketLlmTimeout = 25,
  [int]$MarketGeminiRetries = 3,
  [switch]$ContinueOnError,
  [switch]$SkipNetwork,
  [switch]$ForceFetch,
  [switch]$IncludeTechCutoff,
  [switch]$SafeFirst,
  [switch]$SkipNetworkNormalFirst,
  [switch]$NoAutoSafeAfterTimeout,
  [switch]$AcceptExistingOutputs,
  [switch]$NoAcceptExistingAfterTimeout,
  [switch]$NoCheckpointXlsx
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

chcp 65001 | Out-Null
$env:PYTHONPATH = (Resolve-Path ".\src").Path
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if ([string]::IsNullOrWhiteSpace($UniverseCsv)) {
  Write-Error "UniverseCsv is required. Example: -UniverseCsv 'data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv'"
  exit 1
}

if (-not (Test-Path $UniverseCsv)) {
  Write-Error "UniverseCsv not found: $UniverseCsv"
  exit 1
}

$argsList = @(
  "scripts\run_monthly_cutoff_pipeline_30.py",
  "--field", $Field,
  "--start", $Start,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId,
  "--timeout-sec", [string]$TimeoutSec,
  "--retry-timeout-sec", [string]$RetryTimeoutSec,
  "--max-retries", [string]$MaxRetries,
  "--checkpoint-every", [string]$CheckpointEvery,
  "--auto-safe-slow-ratio", [string]$AutoSafeSlowRatio,
  "--intake-concurrency", [string]$IntakeConcurrency,
  "--agent-concurrency", [string]$AgentConcurrency,
  "--market-llm-timeout", [string]$MarketLlmTimeout,
  "--market-gemini-retries", [string]$MarketGeminiRetries
)

if (-not [string]::IsNullOrWhiteSpace($End)) {
  $argsList += @("--end", $End)
}
if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
  $argsList += @("--only-company-dir", $OnlyCompanyDir)
}
if ($Limit -gt 0) {
  $argsList += @("--limit", [string]$Limit)
}
if ($ContinueOnError) {
  $argsList += "--continue-on-error"
}
if ($SkipNetwork) {
  $argsList += "--skip-network"
}
if ($ForceFetch) {
  $argsList += "--force-fetch"
}
if ($IncludeTechCutoff) {
  $argsList += "--include-tech-cutoff"
}
if ($SafeFirst) {
  $argsList += "--safe-first"
}
if ($SkipNetworkNormalFirst) {
  $argsList += "--skip-network-normal-first"
}
if ($NoAutoSafeAfterTimeout) {
  $argsList += "--no-auto-safe-after-timeout"
}
if ($AcceptExistingOutputs) {
  $argsList += "--accept-existing-outputs"
}
if ($NoAcceptExistingAfterTimeout) {
  $argsList += "--no-accept-existing-after-timeout"
}
if ($NoCheckpointXlsx) {
  $argsList += "--no-checkpoint-xlsx"
}

Write-Host "[monthly-cutoff] projectRoot=$projectRoot"
Write-Host "[monthly-cutoff] python arguments:"
$argsList | ForEach-Object { Write-Host "  $_" }

python @argsList
exit $LASTEXITCODE
