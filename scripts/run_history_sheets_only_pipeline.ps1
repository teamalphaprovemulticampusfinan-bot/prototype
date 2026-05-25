param(
    [string]$Field = "",
    [Parameter(Mandatory = $true)]
    [string]$AsOfDate,
    [ValidateSet("daily", "monthly")]
    [string]$Frequency = "daily",
    [string]$UniverseCsv,
    [switch]$DefaultFive,
    [string]$Agents,
    [switch]$ContinueOnError,
    [string]$RunId,
    [switch]$SkipArchive
)

$ErrorActionPreference = "Stop"

if (-not $Field) {
    $Field = -join ([char[]](0xBC18, 0xB3C4, 0xCCB4))
}

$scriptPath = Join-Path $PSScriptRoot "run_history_sheets_only_pipeline.py"
$pyArgs = @(
    $scriptPath,
    "--field", $Field,
    "--as-of-date", $AsOfDate,
    "--frequency", $Frequency
)

if ($UniverseCsv) {
    $pyArgs += @("--universe-csv", $UniverseCsv)
}
if ($DefaultFive) {
    $pyArgs += "--default-five"
}
if ($Agents) {
    $pyArgs += @("--agents", $Agents)
}
if ($ContinueOnError) {
    $pyArgs += "--continue-on-error"
}
if ($RunId) {
    $pyArgs += @("--run-id", $RunId)
}
if ($SkipArchive) {
    $pyArgs += "--skip-archive"
}

& python @pyArgs
exit $LASTEXITCODE
