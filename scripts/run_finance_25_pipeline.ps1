param(
    [ValidateSet("list", "bootstrap", "intake", "standardize", "agent", "all", "one")]
    [string]$Mode = "list",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [string]$OnlyCompanyDir = "",

    [switch]$IncludeOriginal5,

    [switch]$ContinueOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

$ORIGINAL_5 = @("nepes", "hanmi", "hansol", "duksan", "ltc")

function Invoke-AlphaPython {
    param([Parameter(Mandatory = $true)][string[]]$PyArgs)
    Write-Host ("[PY] python " + ($PyArgs -join " ")) -ForegroundColor DarkGray
    & python @PyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "python failed. exit_code=$LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $Csv)) {
    throw "Universe CSV not found: $Csv. 먼저 finance25_automation_patch_v1.zip 안의 CSV를 적용하세요."
}

$companies = @(
    Import-Csv -LiteralPath $Csv | Where-Object {
        [string]$_.include_in_evaluation -eq "1"
    }
)

if (-not $IncludeOriginal5) {
    $companies = @($companies | Where-Object { $ORIGINAL_5 -notcontains ([string]$_.company_dir) })
}

if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
    $companies = @($companies | Where-Object { [string]$_.company_dir -eq $OnlyCompanyDir })
}

Write-Host "[AlphaProve Finance25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Finance25] Target count: $($companies.Count)" -ForegroundColor Cyan

if ($companies.Count -eq 0) {
    throw "No target companies. Check -OnlyCompanyDir or CSV."
}

if ($Mode -eq "list") {
    $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize
    exit 0
}

# always ensure metadata before running intake/agent
if ($Mode -in @("bootstrap", "intake", "standardize", "agent", "all", "one")) {
    $bootstrapArgs = @(".\scripts\bootstrap_finance_25_universe.py", "--csv", $Csv)
    if (-not $IncludeOriginal5) { $bootstrapArgs += "--only-new-25" }
    Invoke-AlphaPython -PyArgs $bootstrapArgs
}

if ($Mode -eq "bootstrap") {
    Write-Host "[DONE] bootstrap" -ForegroundColor Green
    exit 0
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name
    $code = ([string]$c.stock_code).PadLeft(6, '0')
    $market = [string]$c.market
    $field = if ([string]::IsNullOrWhiteSpace([string]$c.field)) { "반도체" } else { [string]$c.field }

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[FINANCE] $name / $slug / $code / $market" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        if ($Mode -in @("intake", "all", "one")) {
            Invoke-AlphaPython -PyArgs @(
                ".\main.py", "intake",
                "--company-dir", $slug,
                "--company", $name,
                "--field", $field,
                "--agents", "finance",
                "--finance-mode", "all",
                "--finance-years", "2021", "2022", "2023", "2024", "2025"
            )
        }

        if ($Mode -in @("standardize", "all", "one")) {
            Invoke-AlphaPython -PyArgs @(
                ".\scripts\standardize_finance_files.py",
                "--company-dir", $slug,
                "--company", $name,
                "--stock-code", $code,
                "--market", $market,
                "--field", $field
            )
        }

        if ($Mode -in @("agent", "all", "one")) {
            Invoke-AlphaPython -PyArgs @(
                ".\main.py", "finance",
                "--company", $name
            )
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red
        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host "[ALL DONE] Finance25 $Mode" -ForegroundColor Green
