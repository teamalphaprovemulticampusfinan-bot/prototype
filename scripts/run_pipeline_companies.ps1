param(
    [string]$Agent = "chair",
    [string]$Csv = "",
    [switch]$DefaultFive,
    [switch]$ContinueOnError,
    [switch]$DryRun,
    [string[]]$ExtraArgs = @()
)

$ErrorActionPreference = "Stop"

# ASCII-only wrapper to avoid Korean mojibake/parser errors.
# Korean company names are handled inside the Python runner with Unicode escape strings.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$py = "python"
$runner = Join-Path $ScriptDir "run_pipeline_companies.py"

$pyArgs = @($runner, "--agent", $Agent)

if ($Csv -ne "") { $pyArgs += @("--csv", $Csv) }
if ($DefaultFive) { $pyArgs += "--default-five" }
if ($ContinueOnError) { $pyArgs += "--continue-on-error" }
if ($DryRun) { $pyArgs += "--dry-run" }

foreach ($item in $ExtraArgs) {
    $pyArgs += @("--extra-arg", $item)
}

Write-Host "[RUNNER] agent=$Agent" -ForegroundColor Cyan
if ($Csv -ne "") { Write-Host "[RUNNER] csv=$Csv" -ForegroundColor Cyan }
if ($DefaultFive) { Write-Host "[RUNNER] default-five=on" -ForegroundColor Cyan }

& $py @pyArgs
exit $LASTEXITCODE
