param(
    [ValidateSet("bootstrap", "dry-run", "chair-no-intake", "valuation", "tech-local", "full-chair", "pipeline")]
    [string]$Mode = "pipeline",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [switch]$ContinueOnError,
    [switch]$FailOpen
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path $Csv)) {
    throw "기업 universe CSV를 찾을 수 없습니다: $Csv"
}

function Resolve-CompanyDir($row) {
    foreach ($key in @("company_dir", "slug", "company_slug", "기업폴더", "폴더")) {
        if ($row.PSObject.Properties.Name -contains $key) {
            $value = [string]$row.$key
            if (-not [string]::IsNullOrWhiteSpace($value)) { return $value.Trim() }
        }
    }
    return ""
}

function Resolve-CompanyName($row) {
    foreach ($key in @("company", "company_name", "name", "기업명", "회사명")) {
        if ($row.PSObject.Properties.Name -contains $key) {
            $value = [string]$row.$key
            if (-not [string]::IsNullOrWhiteSpace($value)) { return $value.Trim() }
        }
    }
    return ""
}

$companies = Import-Csv -Path $Csv -Encoding UTF8
if ($companies.Count -eq 0) {
    throw "CSV에 실행 대상 기업이 없습니다: $Csv"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Universe runner: $Mode / count=$($companies.Count)" -ForegroundColor Cyan
Write-Host "CSV: $Csv" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

foreach ($row in $companies) {
    $slug = Resolve-CompanyDir $row
    $name = Resolve-CompanyName $row

    if ([string]::IsNullOrWhiteSpace($slug) -or [string]::IsNullOrWhiteSpace($name)) {
        $msg = "company_dir/company 해석 실패. CSV 컬럼은 company_dir,company 또는 slug,company_name 형태여야 합니다."
        if ($ContinueOnError) {
            Write-Host "[SKIP] $msg" -ForegroundColor Yellow
            continue
        }
        throw $msg
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "$name / $slug" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green

    try {
        if ($Mode -eq "dry-run") {
            Write-Host "python main.py pipeline --company-dir $slug --company `"$name`""
        }
        elseif ($Mode -eq "bootstrap") {
            python .\scripts\bootstrap_semiconductor_universe_30.py --csv $Csv
        }
        elseif ($Mode -eq "chair-no-intake") {
            $argsList = @("main.py", "chair", "--company-dir", $slug, "--company", $name, "--no-intake")
            if ($FailOpen) { $argsList += "--fail-open" }
            & python @argsList
        }
        elseif ($Mode -eq "valuation") {
            & python main.py valuation-intake --company-dir $slug --company $name
            & python main.py valuation --company-dir $slug --company $name
        }
        elseif ($Mode -eq "tech-local") {
            & python main.py tech --company-dir $slug --company $name
        }
        elseif ($Mode -eq "full-chair") {
            $argsList = @("main.py", "chair", "--company-dir", $slug, "--company", $name)
            if ($FailOpen) { $argsList += "--fail-open" }
            & python @argsList
        }
        elseif ($Mode -eq "pipeline") {
            $argsList = @("main.py", "pipeline", "--company-dir", $slug, "--company", $name)
            if ($FailOpen) { $argsList += "--fail-open" }
            & python @argsList
        }
        else {
            throw "Unknown mode: $Mode"
        }

        if ($LASTEXITCODE -ne 0) {
            throw "python 종료 코드: $LASTEXITCODE"
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red
        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host ""
Write-Host "[ALL DONE] $Mode" -ForegroundColor Green
