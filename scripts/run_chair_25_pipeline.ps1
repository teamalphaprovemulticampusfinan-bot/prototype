param(
    [ValidateSet("list", "bootstrap", "preflight", "inputs", "one", "agent", "all", "check")]
    [string]$Mode = "list",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [string]$OnlyCompanyDir = "",

    [switch]$IncludeOriginal5,

    [switch]$RequireAuditorPacket,

    # report가 이미 있는 기업은 Chair 재실행 없이 skip
    [switch]$SkipExisting,

    # 이미 있는 report도 강제로 다시 생성
    [switch]$ForceRebuild,

    # 핵심 추가:
    # 기본값은 no-intake 실행.
    # 즉 Chair가 intake/전문 에이전트/auditor를 다시 돌리지 않고,
    # 이미 auditor 단계에서 만들어진 산출물을 읽어 report만 생성하도록 유도한다.
    [switch]$FullCycle,

    # report가 너무 짧거나 깨진 경우에는 "정상 결과"로 보지 않고 다시 실행
    [int]$MinReportChars = 800,

    [switch]$FastMode,

    [switch]$ContinueOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

# Chair report 생성 품질 기본값
if ([string]::IsNullOrWhiteSpace($env:CHAIR_REPORT_MAX_TOKENS)) {
    $env:CHAIR_REPORT_MAX_TOKENS = "9000"
}

if ([string]::IsNullOrWhiteSpace($env:CHAIR_MIN_REPORT_CHARS)) {
    $env:CHAIR_MIN_REPORT_CHARS = "2800"
}

if ([string]::IsNullOrWhiteSpace($env:CHAIR_REPORT_MAX_RETRIES)) {
    $env:CHAIR_REPORT_MAX_RETRIES = "2"
}

if ([string]::IsNullOrWhiteSpace($env:MAX_CONTEXT_CHARS)) {
    $env:MAX_CONTEXT_CHARS = "12000"
}

if ([string]::IsNullOrWhiteSpace($env:REQUEST_TIMEOUT)) {
    $env:REQUEST_TIMEOUT = "80"
}

# Chair는 이미 만들어진 auditor_chair_packet을 읽는 흐름이 기본.
# Auditor 실패 여부는 auditor 단계에서 기록하고, Chair 생성 자체는 막지 않도록 함.
if ([string]::IsNullOrWhiteSpace($env:AUDITOR_FIRST_FAIL_OPEN)) {
    $env:AUDITOR_FIRST_FAIL_OPEN = "1"
}

if ($FastMode) {
    $env:CHAIR_REPORT_MAX_TOKENS = "6000"
    $env:CHAIR_MIN_REPORT_CHARS = "1800"
    $env:CHAIR_REPORT_MAX_RETRIES = "1"
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

# all/agent 모드는 누적 실행이므로 기존 report가 있으면 빠르게 skip.
# one 모드는 사용자가 특정 기업 재생성을 의도할 수 있으므로 -SkipExisting이 있을 때만 skip.
$AutoSkipExisting = $false
if (($Mode -in @("all", "agent")) -and (-not $ForceRebuild)) {
    $AutoSkipExisting = $true
}

$EffectiveSkipExisting = $SkipExisting -or $AutoSkipExisting
$ChairCycleMode = if ($FullCycle) { "FULL-CYCLE: intake/agents/auditor may rerun" } else { "NO-INTAKE: reuse existing auditor/agent outputs" }

Write-Host "[AlphaProve Chair25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Chair25] Target count: $($companies.Count)" -ForegroundColor Cyan
Write-Host "[AlphaProve Chair25] RequireAuditorPacket: $RequireAuditorPacket, SkipExisting: $EffectiveSkipExisting, ForceRebuild: $ForceRebuild, FastMode: $FastMode, MinReportChars: $MinReportChars" -ForegroundColor DarkGray
Write-Host "[AlphaProve Chair25] Chair cycle: $ChairCycleMode" -ForegroundColor Yellow
Write-Host "[Chair runtime]" -ForegroundColor Cyan
Write-Host "  CHAIR_REPORT_MAX_TOKENS=$env:CHAIR_REPORT_MAX_TOKENS" -ForegroundColor DarkGray
Write-Host "  CHAIR_MIN_REPORT_CHARS=$env:CHAIR_MIN_REPORT_CHARS" -ForegroundColor DarkGray
Write-Host "  CHAIR_REPORT_MAX_RETRIES=$env:CHAIR_REPORT_MAX_RETRIES" -ForegroundColor DarkGray
Write-Host "  MAX_CONTEXT_CHARS=$env:MAX_CONTEXT_CHARS" -ForegroundColor DarkGray
Write-Host "  AUDITOR_FIRST_FAIL_OPEN=$env:AUDITOR_FIRST_FAIL_OPEN" -ForegroundColor DarkGray

if ($companies.Count -eq 0) {
    throw "No target companies. Check -OnlyCompanyDir or CSV."
}

if ($Mode -eq "list") {
    $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize
    exit 0
}

function Run-Bootstrap {
    if (Test-Path ".\scripts\bootstrap_chair_25_universe.py") {
        $bootstrapArgs = @(".\scripts\bootstrap_chair_25_universe.py", "--csv", $Csv)

        if (-not $IncludeOriginal5) {
            $bootstrapArgs += "--only-new-25"
        }

        Invoke-AlphaPython -PyArgs $bootstrapArgs
    }
    else {
        Write-Host "[SKIP] bootstrap_chair_25_universe.py not found." -ForegroundColor Yellow
    }
}

if ($Mode -in @("bootstrap", "preflight", "inputs", "one", "agent", "all", "check")) {
    Run-Bootstrap
}

if ($Mode -eq "bootstrap") {
    Write-Host "[DONE] bootstrap" -ForegroundColor Green
    exit 0
}

function Run-InputCheck {
    $args = @(".\scripts\check_chair_25_inputs.py", "--csv", $Csv)

    if ($IncludeOriginal5) {
        $args += "--include-original5"
    }

    if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
        $args += @("--only-company-dir", $OnlyCompanyDir)
    }

    if ($RequireAuditorPacket) {
        $args += "--require-auditor-packet"
    }

    Invoke-AlphaPython -PyArgs $args
}

if ($Mode -eq "preflight") {
    Write-Host "[CHECK] compile scripts" -ForegroundColor Cyan

    foreach ($p in @(
        ".\src\common\company_metadata.py",
        ".\scripts\bootstrap_chair_25_universe.py",
        ".\scripts\check_chair_25_inputs.py",
        ".\scripts\summarize_chair_25_reports.py",
        ".\scripts\verify_company_metadata_resolution.py"
    )) {
        if (Test-Path $p) {
            Invoke-AlphaPython -PyArgs @("-m", "py_compile", $p)
        }
    }

    if (Test-Path ".\scripts\verify_company_metadata_resolution.py") {
        Write-Host "[CHECK] company metadata resolution" -ForegroundColor Cyan
        Invoke-AlphaPython -PyArgs @(".\scripts\verify_company_metadata_resolution.py")
    }

    Write-Host "[CHECK] chair import smoke" -ForegroundColor Cyan
    & python -c "import sys; print('python=', sys.version); import chair_agent; print('chair_agent import OK')"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] chair_agent import smoke failed. main.py chair may still work if package init is unusual." -ForegroundColor Yellow
    }

    Write-Host "[CHECK] Chair inputs overview" -ForegroundColor Cyan
    Run-InputCheck
    exit 0
}

if ($Mode -eq "inputs") {
    Run-InputCheck
    exit 0
}

function Report-Path {
    param(
        [Parameter(Mandatory=$true)][string]$CompanyName,
        [Parameter(Mandatory=$true)][string]$Slug
    )
    return ".\data\반도체\$CompanyName\chair\$($Slug)_chair_report.md"
}

function Get-ReportCharCount {
    param([Parameter(Mandatory=$true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }

    try {
        $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        if ($null -eq $text) {
            return 0
        }
        return $text.Length
    }
    catch {
        return 0
    }
}

function Has-ValidChairReport {
    param(
        [Parameter(Mandatory=$true)][string]$CompanyName,
        [Parameter(Mandatory=$true)][string]$Slug,
        [Parameter(Mandatory=$true)][int]$MinChars
    )

    $report = Report-Path -CompanyName $CompanyName -Slug $Slug
    $chars = Get-ReportCharCount -Path $report

    return ($chars -ge $MinChars)
}

function Run-Chair {
    param(
        [Parameter(Mandatory=$true)][string]$Slug,
        [Parameter(Mandatory=$true)][string]$Name
    )

    $args = @(
        ".\main.py", "chair",
        "--company-dir", $Slug,
        "--company", $Name
    )

    # 핵심:
    # 기본은 --no-intake를 붙인다.
    # 이렇게 해야 Chair가 intake부터 다시 돌지 않고,
    # 이미 auditor/agent 단계에서 만들어진 산출물을 재사용한다.
    if (-not $FullCycle) {
        $args += "--no-intake"
    }

    Invoke-AlphaPython -PyArgs $args
}

if ($Mode -eq "check") {
    Write-Host "[CHECK] Chair reports" -ForegroundColor Cyan

    if (Test-Path ".\scripts\summarize_chair_25_reports.py") {
        $summaryArgs = @(".\scripts\summarize_chair_25_reports.py", "--csv", $Csv)

        if ($IncludeOriginal5) {
            $summaryArgs += "--include-original5"
        }

        if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
            $summaryArgs += @("--only-company-dir", $OnlyCompanyDir)
        }

        Invoke-AlphaPython -PyArgs $summaryArgs
    }

    $reports = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_chair_report.md" -ErrorAction SilentlyContinue)
    Write-Host "chair_report count: $($reports.Count)" -ForegroundColor Green
    $reports | Select-Object -First 80 FullName, Length | Format-Table -AutoSize
    exit 0
}

$processed = 0
$skipped = 0
$failed = 0

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name
    $report = Report-Path -CompanyName $name -Slug $slug
    $existingChars = Get-ReportCharCount -Path $report

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[CHAIR] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        if ($EffectiveSkipExisting -and (Has-ValidChairReport -CompanyName $name -Slug $slug -MinChars $MinReportChars)) {
            Write-Host "[FAST-SKIP] existing Chair report found ($existingChars chars): $report" -ForegroundColor Yellow
            $skipped += 1
            continue
        }

        if ($EffectiveSkipExisting -and (Test-Path -LiteralPath $report) -and ($existingChars -lt $MinReportChars)) {
            Write-Host "[REBUILD] existing report is too short ($existingChars chars < $MinReportChars): $report" -ForegroundColor Yellow
        }

        if ($RequireAuditorPacket) {
            Invoke-AlphaPython -PyArgs @(
                ".\scripts\check_chair_25_inputs.py",
                "--csv", $Csv,
                "--only-company-dir", $slug,
                "--require-auditor-packet"
            )
        }

        if ($Mode -in @("one", "agent", "all")) {
            Run-Chair -Slug $slug -Name $name

            $newChars = Get-ReportCharCount -Path $report
            if (Test-Path -LiteralPath $report) {
                Write-Host "[OK] Chair report ($newChars chars): $report" -ForegroundColor Green
                $processed += 1
            }
            else {
                Write-Host "[WARN] Chair command finished but expected report not found: $report" -ForegroundColor Yellow
                $failed += 1
            }
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red
        $failed += 1

        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host "[ALL DONE] Chair25 $Mode" -ForegroundColor Green
Write-Host "[SUMMARY] processed=$processed skipped=$skipped failed=$failed" -ForegroundColor Cyan
