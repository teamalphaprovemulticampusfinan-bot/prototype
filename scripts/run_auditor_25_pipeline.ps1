param(
    [ValidateSet("list", "bootstrap", "preflight", "inputs", "one", "agent", "all", "check")]
    [string]$Mode = "list",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [string]$OnlyCompanyDir = "",

    [switch]$IncludeOriginal5,

    [switch]$RequireAllInputs,

    [switch]$SkipExisting,

    [switch]$JsonOutput,

    [switch]$FastMode,

    # 핵심 추가:
    # Auditor 검증은 실행하되, threshold fail 때문에 pipeline을 중단하지 않게 함.
    # 기존 5개처럼 Chair 연결/자동화 확인이 우선일 때 사용.
    [switch]$FailOpen,

    [switch]$ContinueOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

# Auditor runtime policy
if ($FastMode) {
    $env:AUDITOR_FAST_MODE = "1"
    $env:AUDITOR_FIRST_MAX_ROUNDS = "1"
}
else {
    $env:AUDITOR_FAST_MODE = "0"
    if ([string]::IsNullOrWhiteSpace($env:AUDITOR_FIRST_MAX_ROUNDS)) {
        $env:AUDITOR_FIRST_MAX_ROUNDS = "1"
    }
}

# 이전 v1에서는 여기서 blank일 때 무조건 0을 넣어서,
# 사용자가 원래 의도했던 fail-open 흐름이 VS 터미널 초기화 후 꺼질 수 있었음.
# 이제는 -FailOpen을 줄 때만 강제로 1로 켠다.
if ($FailOpen) {
    $env:AUDITOR_FIRST_FAIL_OPEN = "1"
}

if ([string]::IsNullOrWhiteSpace($env:AUDITOR_FIRST_PASS_THRESHOLD)) {
    $env:AUDITOR_FIRST_PASS_THRESHOLD = "0.85"
}

Write-Host "[Auditor runtime]" -ForegroundColor Cyan
Write-Host "  AUDITOR_FAST_MODE=$env:AUDITOR_FAST_MODE" -ForegroundColor DarkGray
Write-Host "  AUDITOR_FIRST_MAX_ROUNDS=$env:AUDITOR_FIRST_MAX_ROUNDS" -ForegroundColor DarkGray
Write-Host "  AUDITOR_FIRST_FAIL_OPEN=$env:AUDITOR_FIRST_FAIL_OPEN" -ForegroundColor DarkGray
Write-Host "  AUDITOR_FIRST_PASS_THRESHOLD=$env:AUDITOR_FIRST_PASS_THRESHOLD" -ForegroundColor DarkGray

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
    throw "Universe CSV not found: $Csv. 먼저 universe CSV를 적용하세요."
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

Write-Host "[AlphaProve Auditor25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Auditor25] Target count: $($companies.Count)" -ForegroundColor Cyan
Write-Host "[AlphaProve Auditor25] RequireAllInputs: $RequireAllInputs, SkipExisting: $SkipExisting, FastMode: $FastMode, FailOpen: $FailOpen" -ForegroundColor DarkGray

if ($companies.Count -eq 0) {
    throw "No target companies. Check -OnlyCompanyDir or CSV."
}

if ($Mode -eq "list") {
    $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize
    exit 0
}

function Run-Bootstrap {
    if (Test-Path ".\scripts\bootstrap_auditor_25_universe.py") {
        $bootstrapArgs = @(".\scripts\bootstrap_auditor_25_universe.py", "--csv", $Csv)

        if (-not $IncludeOriginal5) {
            $bootstrapArgs += "--only-new-25"
        }

        Invoke-AlphaPython -PyArgs $bootstrapArgs
    }
    else {
        Write-Host "[SKIP] bootstrap_auditor_25_universe.py not found." -ForegroundColor Yellow
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
    if (-not (Test-Path ".\scripts\check_auditor_25_inputs.py")) {
        Write-Host "[SKIP] check_auditor_25_inputs.py not found." -ForegroundColor Yellow
        return
    }

    $args = @(".\scripts\check_auditor_25_inputs.py", "--csv", $Csv)

    if ($IncludeOriginal5) {
        $args += "--include-original5"
    }

    if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
        $args += @("--only-company-dir", $OnlyCompanyDir)
    }

    if ($RequireAllInputs) {
        $args += "--require-all"
    }

    Invoke-AlphaPython -PyArgs $args
}

if ($Mode -eq "preflight") {
    Write-Host "[CHECK] compile scripts" -ForegroundColor Cyan

    if (Test-Path ".\src\common\company_metadata.py") {
        Invoke-AlphaPython -PyArgs @("-m", "py_compile", ".\src\common\company_metadata.py")
    }

    foreach ($p in @(
        ".\scripts\bootstrap_auditor_25_universe.py",
        ".\scripts\check_auditor_25_inputs.py",
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

    Write-Host "[CHECK] auditor import smoke" -ForegroundColor Cyan
    & python -c "import sys; print('python=', sys.version); import auditor_agent; print('auditor_agent import OK')"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] auditor_agent import smoke failed. main.py auditor may still work if package init is unusual." -ForegroundColor Yellow
    }

    Write-Host "[CHECK] input packets overview" -ForegroundColor Cyan
    Run-InputCheck
    exit 0
}

if ($Mode -eq "inputs") {
    Run-InputCheck
    exit 0
}

function Get-CompanyRoot {
    param([Parameter(Mandatory=$true)][string]$CompanyName)
    return ".\data\반도체\$CompanyName"
}

function Has-AuditorOutputs {
    param([Parameter(Mandatory=$true)][string]$CompanyName)

    $root = Get-CompanyRoot -CompanyName $CompanyName
    $auditorDir = Join-Path $root "auditor"

    if (-not (Test-Path -LiteralPath $auditorDir)) {
        return $false
    }

    $found = @(Get-ChildItem $auditorDir -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match "auditor_chair_packet\.json|first_auditor.*\.json|audit.*\.json|compact_agent_packets"
        })

    return ($found.Count -gt 0)
}

function Run-Auditor {
    param(
        [Parameter(Mandatory=$true)][string]$Slug,
        [Parameter(Mandatory=$true)][string]$Name
    )

    $args = @(
        ".\main.py", "auditor",
        "--company-dir", $Slug,
        "--company", $Name
    )

    if ($JsonOutput) {
        $args += "--json"
    }

    Invoke-AlphaPython -PyArgs $args
}

if ($Mode -eq "check") {
    Write-Host "[CHECK] auditor outputs" -ForegroundColor Cyan

    $auditorPackets = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "auditor_chair_packet.json" -ErrorAction SilentlyContinue)
    Write-Host "auditor_chair_packet count: $($auditorPackets.Count)" -ForegroundColor Green
    $auditorPackets | Select-Object -First 80 FullName | Format-Table -AutoSize

    $compactDirs = @(Get-ChildItem ".\data\반도체" -Recurse -Directory -Filter "compact_agent_packets" -ErrorAction SilentlyContinue)
    Write-Host "compact_agent_packets dir count: $($compactDirs.Count)" -ForegroundColor Green
    $compactDirs | Select-Object -First 80 FullName | Format-Table -AutoSize

    $auditJsons = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*auditor*.json" -ErrorAction SilentlyContinue)
    Write-Host "auditor json-like count: $($auditJsons.Count)" -ForegroundColor Green
    $auditJsons | Select-Object -First 80 FullName | Format-Table -AutoSize
    exit 0
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[AUDITOR] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        if ($RequireAllInputs -and (Test-Path ".\scripts\check_auditor_25_inputs.py")) {
            Invoke-AlphaPython -PyArgs @(
                ".\scripts\check_auditor_25_inputs.py",
                "--csv", $Csv,
                "--only-company-dir", $slug,
                "--require-all"
            )
        }

        if ($SkipExisting -and (Has-AuditorOutputs -CompanyName $name)) {
            Write-Host "[SKIP] auditor outputs already exist: $name / $slug" -ForegroundColor Yellow
            continue
        }

        if ($Mode -in @("one", "agent", "all")) {
            Run-Auditor -Slug $slug -Name $name
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red

        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host "[ALL DONE] Auditor25 $Mode" -ForegroundColor Green
