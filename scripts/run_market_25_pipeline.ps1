param(
    [ValidateSet("list", "bootstrap", "patch-config", "preflight", "one", "agent", "all", "check")]
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
    if ($LASTEXITCODE -ne 0) { throw "python failed. exit_code=$LASTEXITCODE" }
}

if (-not (Test-Path -LiteralPath $Csv)) { throw "Universe CSV not found: $Csv. ZIP 안의 universe CSV를 먼저 적용하세요." }

$companies = @(Import-Csv -LiteralPath $Csv | Where-Object { [string]$_.include_in_evaluation -eq "1" })
if (-not $IncludeOriginal5) { $companies = @($companies | Where-Object { $ORIGINAL_5 -notcontains ([string]$_.company_dir) }) }
if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) { $companies = @($companies | Where-Object { [string]$_.company_dir -eq $OnlyCompanyDir }) }

Write-Host "[AlphaProve Market25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Market25] Target count: $($companies.Count)" -ForegroundColor Cyan
if ($companies.Count -eq 0) { throw "No target companies. Check -OnlyCompanyDir or CSV." }

if ($Mode -eq "list") {
    $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize
    exit 0
}

function Run-Bootstrap {
    $bootstrapArgs = @(".\scripts\bootstrap_market_25_universe.py", "--csv", $Csv)
    if (-not $IncludeOriginal5) { $bootstrapArgs += "--only-new-25" }
    Invoke-AlphaPython -PyArgs $bootstrapArgs
}

function Run-PatchConfig { Invoke-AlphaPython -PyArgs @(".\scripts\patch_market_25_dynamic_metadata.py") }

if ($Mode -in @("bootstrap", "patch-config", "preflight", "one", "agent", "all", "check")) { Run-Bootstrap }
if ($Mode -eq "bootstrap") { Write-Host "[DONE] bootstrap" -ForegroundColor Green; exit 0 }
if ($Mode -in @("patch-config", "preflight", "one", "agent", "all")) { Run-PatchConfig }
if ($Mode -eq "patch-config") { Write-Host "[DONE] patch-config" -ForegroundColor Green; exit 0 }

if ($Mode -eq "preflight") {
    Write-Host "[CHECK] MARKET_WORKBOOK_URL env" -ForegroundColor Cyan
    if ([string]::IsNullOrWhiteSpace($env:MARKET_WORKBOOK_URL)) { Write-Host "MARKET_WORKBOOK_URL is empty in current shell. If .env is loaded by Python code, this can still be OK." -ForegroundColor Yellow }
    else { Write-Host "MARKET_WORKBOOK_URL is set." -ForegroundColor Green }
    Write-Host "[CHECK] local workbook candidates" -ForegroundColor Cyan
    $candidates = @(".\data\반도체\_sector_common\data\Market_통합.xlsx", ".\data\반도체\_sector_common\source_data\Market_통합.xlsx", ".\data\Market_통합.xlsx")
    foreach ($p in $candidates) { Write-Host "$p => $(Test-Path $p)" }
    Write-Host "[CHECK] dynamic metadata import" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-c", "from common.company_metadata import get_company_metadata; print(get_company_metadata('dbhitek', 'DB하이텍'))")
    Write-Host "[CHECK] market config import" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-c", "import market_agent.config as c; print('DB하이텍 ticker=', getattr(c, 'TICKERS', {}).get('DB하이텍')); print('dbhitek ticker=', getattr(c, 'TICKERS', {}).get('dbhitek'))")
    exit 0
}

if ($Mode -eq "check") {
    Write-Host "[CHECK] market outputs" -ForegroundColor Cyan
    $packets = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_market_agent_packet.json" -ErrorAction SilentlyContinue)
    Write-Host "market_agent_packet count: $($packets.Count)" -ForegroundColor Green
    $packets | Select-Object -First 50 FullName | Format-Table -AutoSize
    $jsons = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*market*.json" -ErrorAction SilentlyContinue)
    Write-Host "market json-like count: $($jsons.Count)" -ForegroundColor Green
    $jsons | Select-Object -First 50 FullName | Format-Table -AutoSize
    exit 0
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name
    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[MARKET] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray
    try {
        if ($Mode -in @("one", "agent", "all")) {
            Invoke-AlphaPython -PyArgs @(".\main.py", "market", "--company-dir", $slug, "--company", $name)
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red
        if (-not $ContinueOnError) { exit 1 }
    }
}
Write-Host "[ALL DONE] Market25 $Mode" -ForegroundColor Green
