param(
    [ValidateSet("list", "bootstrap", "preflight", "intake", "agent", "one", "all", "check")]
    [string]$Mode = "list",
    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",
    [string]$OnlyCompanyDir = "",
    [switch]$IncludeOriginal5,
    [switch]$SkipExisting,
    [switch]$SkipNetwork,
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
    if ($LASTEXITCODE -ne 0) { throw "python failed. exit_code=$LASTEXITCODE" }
}

if (-not (Test-Path -LiteralPath $Csv)) { throw "Universe CSV not found: $Csv. ZIP 안의 universe CSV를 먼저 적용하세요." }

$companies = @(Import-Csv -LiteralPath $Csv | Where-Object { [string]$_.include_in_evaluation -eq "1" })
if (-not $IncludeOriginal5) { $companies = @($companies | Where-Object { $ORIGINAL_5 -notcontains ([string]$_.company_dir) }) }
if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) { $companies = @($companies | Where-Object { [string]$_.company_dir -eq $OnlyCompanyDir }) }

Write-Host "[AlphaProve Valuation25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Valuation25] Target count: $($companies.Count)" -ForegroundColor Cyan
Write-Host "[AlphaProve Valuation25] SkipExisting: $SkipExisting, SkipNetwork: $SkipNetwork" -ForegroundColor DarkGray
if ($companies.Count -eq 0) { throw "No target companies. Check -OnlyCompanyDir or CSV." }

if ($Mode -eq "list") { $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize; exit 0 }

function Run-Bootstrap {
    $bootstrapArgs = @(".\scripts\bootstrap_valuation_25_universe.py", "--csv", $Csv)
    if (-not $IncludeOriginal5) { $bootstrapArgs += "--only-new-25" }
    Invoke-AlphaPython -PyArgs $bootstrapArgs
}

if ($Mode -in @("bootstrap", "preflight", "intake", "agent", "one", "all", "check")) { Run-Bootstrap }
if ($Mode -eq "bootstrap") { Write-Host "[DONE] bootstrap" -ForegroundColor Green; exit 0 }

if ($Mode -eq "preflight") {
    Write-Host "[CHECK] compile scripts" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-m", "py_compile", ".\scripts\bootstrap_valuation_25_universe.py")
    Write-Host "[CHECK] dynamic metadata import" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-c", "from common.company_metadata import get_company_metadata, ticker_for_company; print(get_company_metadata('dbhitek', 'DB하이텍')); print('ticker=', ticker_for_company('dbhitek','DB하이텍'))")
    Write-Host "[CHECK] core valuation dependencies" -ForegroundColor Cyan
    & python -c "import importlib.util; mods=['pandas','openpyxl','requests','yfinance']; [print(m, 'OK' if importlib.util.find_spec(m) else 'MISSING') for m in mods]"
    exit 0
}

function Has-ValuationOutputs {
    param([Parameter(Mandatory=$true)][string]$CompanyName, [Parameter(Mandatory=$true)][string]$Slug)
    $valuationDir = ".\data\반도체\$CompanyName\valuation"
    $workbook = Join-Path $valuationDir "$($Slug)_valuation_workbook.xlsx"
    $metrics = Join-Path $valuationDir "$($Slug)_valuation_metrics.json"
    $validation = Join-Path $valuationDir "$($Slug)_valuation_validation.json"
    return ((Test-Path -LiteralPath $workbook) -and (Test-Path -LiteralPath $metrics) -and (Test-Path -LiteralPath $validation))
}

function Run-ValuationIntake {
    param([Parameter(Mandatory=$true)][string]$Slug, [Parameter(Mandatory=$true)][string]$Name)
    $args = @(".\main.py", "valuation-intake", "--company-dir", $Slug, "--company", $Name)
    if ($SkipNetwork) { $args += "--skip-network" }
    Invoke-AlphaPython -PyArgs $args
}

function Run-ValuationAgent {
    param([Parameter(Mandatory=$true)][string]$Slug, [Parameter(Mandatory=$true)][string]$Name)
    Invoke-AlphaPython -PyArgs @(".\main.py", "valuation", "--company-dir", $Slug, "--company", $Name)
}

if ($Mode -eq "check") {
    Write-Host "[CHECK] valuation outputs" -ForegroundColor Cyan
    $workbooks = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_valuation_workbook.xlsx" -ErrorAction SilentlyContinue)
    Write-Host "valuation_workbook count: $($workbooks.Count)" -ForegroundColor Green
    $workbooks | Select-Object -First 60 FullName | Format-Table -AutoSize
    $metrics = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_valuation_metrics.json" -ErrorAction SilentlyContinue)
    Write-Host "valuation_metrics count: $($metrics.Count)" -ForegroundColor Green
    $metrics | Select-Object -First 60 FullName | Format-Table -AutoSize
    $validations = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_valuation_validation.json" -ErrorAction SilentlyContinue)
    Write-Host "valuation_validation count: $($validations.Count)" -ForegroundColor Green
    $validations | Select-Object -First 60 FullName | Format-Table -AutoSize
    $manifests = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "valuation_intake_manifest.json" -ErrorAction SilentlyContinue)
    Write-Host "valuation_intake_manifest count: $($manifests.Count)" -ForegroundColor Green
    $manifests | Select-Object -First 60 FullName | Format-Table -AutoSize
    exit 0
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name
    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[VALUATION] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray
    try {
        if ($SkipExisting -and (Has-ValuationOutputs -CompanyName $name -Slug $slug)) {
            Write-Host "[SKIP] valuation outputs already exist: $name / $slug" -ForegroundColor Yellow
            continue
        }
        if ($Mode -in @("intake", "one", "all")) { Run-ValuationIntake -Slug $slug -Name $name }
        if ($Mode -in @("agent", "one", "all")) { Run-ValuationAgent -Slug $slug -Name $name }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red
        if (-not $ContinueOnError) { exit 1 }
    }
}
Write-Host "[ALL DONE] Valuation25 $Mode" -ForegroundColor Green
