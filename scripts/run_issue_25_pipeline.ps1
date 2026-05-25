param(
    [ValidateSet("list", "bootstrap", "patch-config", "preflight", "one", "agent", "all", "check")]
    [string]$Mode = "list",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [string]$OnlyCompanyDir = "",

    [switch]$IncludeOriginal5,

    [switch]$DisableNaverNews,

    [switch]$EnableNewsApi,

    [switch]$ContinueOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

# NewsAPI는 429가 잦으므로 기본 OFF 유지.
if ($EnableNewsApi) {
    $env:ISSUE_ENABLE_NEWS_API = "1"
}
else {
    $env:ISSUE_ENABLE_NEWS_API = "0"
}

# 네이버 뉴스는 기본 ON이지만, 25개 일괄 실행이 느리면 -DisableNaverNews 사용.
if ($DisableNaverNews) {
    $env:ISSUE_ENABLE_NAVER_NEWS = "0"
}

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
    throw "Universe CSV not found: $Csv. ZIP 안의 universe CSV를 먼저 적용하세요."
}

$companies = @(
    Import-Csv -LiteralPath $Csv | Where-Object {
        [string]$_.include_in_evaluation -eq "1"
    }
)

if (-not $IncludeOriginal5) {
    $companies = @(
        $companies | Where-Object {
            $ORIGINAL_5 -notcontains ([string]$_.company_dir)
        }
    )
}

if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
    $companies = @(
        $companies | Where-Object {
            [string]$_.company_dir -eq $OnlyCompanyDir
        }
    )
}

Write-Host "[AlphaProve Issue25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Issue25] Target count: $($companies.Count)" -ForegroundColor Cyan
Write-Host "[AlphaProve Issue25] DisableNaverNews: $DisableNaverNews, EnableNewsApi: $EnableNewsApi" -ForegroundColor DarkGray

if ($companies.Count -eq 0) {
    throw "No target companies. Check -OnlyCompanyDir or CSV."
}

if ($Mode -eq "list") {
    $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize
    exit 0
}

function Run-Bootstrap {
    $bootstrapArgs = @(".\scripts\bootstrap_issue_25_universe.py", "--csv", $Csv)

    if (-not $IncludeOriginal5) {
        $bootstrapArgs += "--only-new-25"
    }

    Invoke-AlphaPython -PyArgs $bootstrapArgs
}

function Run-PatchConfig {
    Invoke-AlphaPython -PyArgs @(".\scripts\patch_issue_25_dynamic_metadata.py")
}

if ($Mode -in @("bootstrap", "patch-config", "preflight", "one", "agent", "all", "check")) {
    Run-Bootstrap
}

if ($Mode -eq "bootstrap") {
    Write-Host "[DONE] bootstrap" -ForegroundColor Green
    exit 0
}

if ($Mode -in @("patch-config", "preflight", "one", "agent", "all")) {
    Run-PatchConfig
}

if ($Mode -eq "patch-config") {
    Write-Host "[DONE] patch-config" -ForegroundColor Green
    exit 0
}

if ($Mode -eq "preflight") {
    Write-Host "[CHECK] compile scripts" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-m", "py_compile", ".\scripts\bootstrap_issue_25_universe.py")
    Invoke-AlphaPython -PyArgs @("-m", "py_compile", ".\scripts\patch_issue_25_dynamic_metadata.py")

    Write-Host "[CHECK] dynamic metadata import" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-c", "from common.company_metadata import get_company_metadata; print(get_company_metadata('dbhitek', 'DB하이텍'))")

    Write-Host "[CHECK] issue config import and keywords" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-c", "import issue_agent.config as c; print('default_company=', c.SETTINGS.default_company); print('DB하이텍 keywords=', c.COMPANY_RSS_KEYWORDS.get('DB하이텍')); print('dbhitek keywords=', c.COMPANY_RSS_KEYWORDS.get('dbhitek'))")

    Write-Host "[CHECK] Issue_Integration workbook env/path" -ForegroundColor Cyan
    Invoke-AlphaPython -PyArgs @("-c", "from issue_agent.excel_loader import LOCAL_EXCEL_PATH, EXCEL_URL; print('LOCAL_EXCEL_PATH=', LOCAL_EXCEL_PATH); print('exists=', LOCAL_EXCEL_PATH.exists()); print('EXCEL_URL=', EXCEL_URL[:80] if EXCEL_URL else '')")
    exit 0
}

if ($Mode -eq "check") {
    Write-Host "[CHECK] issue outputs" -ForegroundColor Cyan

    $packets = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_issue_agent_packet.json" -ErrorAction SilentlyContinue)
    Write-Host "issue_agent_packet count: $($packets.Count)" -ForegroundColor Green
    $packets | Select-Object -First 60 FullName | Format-Table -AutoSize

    $reports = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_issue_report.md" -ErrorAction SilentlyContinue)
    Write-Host "issue_report md count: $($reports.Count)" -ForegroundColor Green
    $reports | Select-Object -First 60 FullName | Format-Table -AutoSize
    exit 0
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[ISSUE] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        if ($Mode -in @("one", "agent", "all")) {
            Invoke-AlphaPython -PyArgs @(
                ".\main.py", "issue",
                "--company-dir", $slug,
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

Write-Host "[ALL DONE] Issue25 $Mode" -ForegroundColor Green
