param(
    [string]$UniverseCsv = ".\data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",
    [ValidateSet("New25", "All30", "Base5")]
    [string]$Mode = "New25",
    [string]$Field = "반도체",
    [string]$Components = "bibliographic,claims,citation,family",
    [int]$MaxPatents = 0,
    [double]$SleepSec = 0.6,
    [int]$Timeout = 60,
    [switch]$ForceFetch,
    [switch]$RunChair,
    [switch]$ChairRunIntake,
    [switch]$StopOnError,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Get-ColValue($Row, [string[]]$Names, [string]$Default = "") {
    foreach ($name in $Names) {
        if ($Row.PSObject.Properties.Name -contains $name) {
            $value = [string]$Row.$name
            if (-not [string]::IsNullOrWhiteSpace($value)) { return $value.Trim() }
        }
    }
    return $Default
}

if (-not (Test-Path $UniverseCsv)) {
    throw "Universe CSV를 찾지 못했습니다: $UniverseCsv"
}

# Windows 한글 경로/출력 안정화
try { chcp 65001 | Out-Null } catch {}
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

$baseSlugs = @("nepes", "hanmi", "hansol", "duksan", "ltc")
$rows = Import-Csv -Path $UniverseCsv | Where-Object {
    $include = Get-ColValue $_ @("include_in_evaluation", "include") "1"
    $include -in @("1", "true", "TRUE", "Y", "y", "yes", "YES")
}

if ($Mode -eq "New25") {
    $targets = $rows | Where-Object { (Get-ColValue $_ @("company_dir", "slug")) -notin $baseSlugs }
} elseif ($Mode -eq "Base5") {
    $targets = $rows | Where-Object { (Get-ColValue $_ @("company_dir", "slug")) -in $baseSlugs }
} else {
    $targets = $rows
}

$targets = @($targets)
if ($targets.Count -eq 0) {
    throw "실행 대상 기업이 없습니다. Mode=$Mode, UniverseCsv=$UniverseCsv"
}

Write-Step "Tech KIPRIS Plus Pipeline 시작: Mode=$Mode, Targets=$($targets.Count), Components=$Components"
Write-Host "KIPRIS_PLUS_API_KEY set: $([bool]$env:KIPRIS_PLUS_API_KEY)"
Write-Host "KIPRIS_PLUS_BIBLIO_ENDPOINT(S) set: $([bool]($env:KIPRIS_PLUS_BIBLIO_ENDPOINT -or $env:KIPRIS_PLUS_BIBLIO_ENDPOINTS -or $env:KIPRIS_PLUS_PUBLIC_REGISTER_ENDPOINT -or $env:KIPRIS_PLUS_PUBLIC_REGISTER_ENDPOINTS))"
Write-Host "KIPRIS_PLUS_CLAIMS_ENDPOINT set: $([bool]$env:KIPRIS_PLUS_CLAIMS_ENDPOINT)"
Write-Host "KIPRIS_PLUS_CITATION_ENDPOINT set: $([bool]($env:KIPRIS_PLUS_CITATION_ENDPOINT -or $env:KIPRIS_CITATION_ENDPOINT -or $env:KIPRIS_PLUS_CITING_ENDPOINT))"
Write-Host "KIPRIS_PLUS_FAMILY_URL set: $([bool]($env:KIPRIS_PLUS_FAMILY_URL -or $env:KIPRIS_FAMILY_URL))"

$logDir = ".\data\반도체\_sector_common\tech_kipris_plus_run_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$summaryPath = Join-Path $logDir "tech_25_kipris_plus_run_summary_$stamp.csv"
$results = New-Object System.Collections.Generic.List[object]

foreach ($row in $targets) {
    $slug = Get-ColValue $row @("company_dir", "slug")
    $company = Get-ColValue $row @("company_name", "display_name", "corp_name", "company")
    if ([string]::IsNullOrWhiteSpace($slug) -or [string]::IsNullOrWhiteSpace($company)) {
        Write-Warning "company_dir/company_name 누락 행 스킵: $($row | ConvertTo-Json -Compress)"
        continue
    }

    Write-Step "[$company / $slug] Tech Intake → Tech Agent"
    $started = Get-Date
    $status = "OK"
    $exitCode = 0
    $chairStatus = "SKIPPED"
    $cmd = @(
        "main.py", "data-intake",
        "--agents", "tech",
        "--field", $Field,
        "--company-dir", $slug,
        "--company", $company,
        "--tech-max-patents", [string]$MaxPatents,
        "--tech-sleep-sec", [string]$SleepSec,
        "--tech-timeout", [string]$Timeout,
        "--tech-kipris-plus-components", $Components
    )
    if ($ForceFetch) { $cmd += "--tech-force-fetch" }
    if ($StopOnError) { $cmd += "--stop-on-error" }

    Write-Host "COMMAND: $Python $($cmd -join ' ')"
    & $Python @cmd
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $status = "FAILED_DATA_INTAKE"
        Write-Warning "[$company] data-intake 실패 exitCode=$exitCode"
        if ($StopOnError) { throw "[$company] data-intake 실패" }
    }

    if ($RunChair -and $exitCode -eq 0) {
        Write-Step "[$company / $slug] Chair 실행"
        $chairCmd = @("main.py", "chair", "--company-dir", $slug, "--company", $company)
        if ($ChairRunIntake) {
            $chairCmd += "--run-intake"
        } else {
            $chairCmd += "--no-intake"
        }
        Write-Host "COMMAND: $Python $($chairCmd -join ' ')"
        & $Python @chairCmd
        $chairExit = $LASTEXITCODE
        if ($chairExit -eq 0) {
            $chairStatus = "OK"
        } else {
            $chairStatus = "FAILED_CHAIR_$chairExit"
            if ($status -eq "OK") { $status = "WARN_CHAIR_FAILED" }
            if ($StopOnError) { throw "[$company] chair 실패 exitCode=$chairExit" }
        }
    }

    $techDir = Join-Path ".\data\반도체" (Join-Path $company "tech")
    $manifestPath = Join-Path $techDir "tech_intake_manifest.json"
    $summaryJson = Join-Path $techDir "tech_chair_summary.json"
    $compositeJson = Join-Path $techDir "tech_ip_evidence_composite.json"
    $sourceCsv = Join-Path $techDir "$($slug)_kipris_bibliographic_normalized.csv"
    $chairReport = Join-Path ".\data\반도체" (Join-Path $company "chair\$($slug)_chair_report.md")

    $results.Add([pscustomobject]@{
        mode = $Mode
        company = $company
        company_dir = $slug
        status = $status
        data_intake_exit_code = $exitCode
        chair_status = $chairStatus
        started_at = $started.ToString("s")
        ended_at = (Get-Date).ToString("s")
        source_csv_exists = Test-Path $sourceCsv
        tech_manifest_exists = Test-Path $manifestPath
        tech_summary_exists = Test-Path $summaryJson
        ip_composite_exists = Test-Path $compositeJson
        chair_report_exists = Test-Path $chairReport
        manifest_path = $manifestPath
    }) | Out-Null

    $results | Export-Csv -Path $summaryPath -NoTypeInformation -Encoding UTF8
}

Write-Step "완료"
Write-Host "요약 CSV: $summaryPath"
$results | Format-Table -AutoSize
