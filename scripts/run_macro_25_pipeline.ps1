param(
    [ValidateSet("list", "bootstrap", "intake-once", "agent", "all", "one", "check")]
    [string]$Mode = "list",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [string]$OnlyCompanyDir = "",

    [string]$IntakeCompanyDir = "dbhitek",

    [switch]$IncludeOriginal5,

    [switch]$UseLLM,

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
    throw "Universe CSV not found: $Csv. ZIP 안의 universe CSV를 먼저 적용하세요."
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

Write-Host "[AlphaProve Macro25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Macro25] Target count: $($companies.Count)" -ForegroundColor Cyan
Write-Host "[AlphaProve Macro25] UseLLM: $UseLLM" -ForegroundColor DarkGray

if ($companies.Count -eq 0) {
    throw "No target companies. Check -OnlyCompanyDir or CSV."
}

if ($Mode -eq "list") {
    $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize
    exit 0
}

# Always ensure metadata before running intake/agent.
if ($Mode -in @("bootstrap", "intake-once", "agent", "all", "one", "check")) {
    $bootstrapArgs = @(".\scripts\bootstrap_macro_25_universe.py", "--csv", $Csv)
    if (-not $IncludeOriginal5) { $bootstrapArgs += "--only-new-25" }
    Invoke-AlphaPython -PyArgs $bootstrapArgs
}

if ($Mode -eq "bootstrap") {
    Write-Host "[DONE] bootstrap" -ForegroundColor Green
    exit 0
}

function Get-CompanyRowBySlug {
    param([Parameter(Mandatory = $true)][string]$Slug)

    $row = @(
        Import-Csv -LiteralPath $Csv | Where-Object {
            [string]$_.company_dir -eq $Slug
        }
    )

    if ($row.Count -eq 0) {
        throw "IntakeCompanyDir not found in CSV: $Slug"
    }

    return $row[0]
}

if ($Mode -in @("intake-once", "all")) {
    $intakeRow = Get-CompanyRowBySlug -Slug $IntakeCompanyDir
    $intakeName = [string]$intakeRow.company_name
    $intakeField = if ([string]::IsNullOrWhiteSpace([string]$intakeRow.field)) { "반도체" } else { [string]$intakeRow.field }

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[MACRO INTAKE ONCE] $intakeName / $IntakeCompanyDir" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        Invoke-AlphaPython -PyArgs @(
            ".\main.py", "intake",
            "--company-dir", $IntakeCompanyDir,
            "--company", $intakeName,
            "--field", $intakeField,
            "--agents", "macro"
        )
    }
    catch {
        Write-Host "[ERROR] macro intake once failed: $_" -ForegroundColor Red
        if (-not $ContinueOnError) {
            exit 1
        }
    }

    if ($Mode -eq "intake-once") {
        Write-Host "[DONE] macro intake once" -ForegroundColor Green
        exit 0
    }
}

if ($Mode -eq "check") {
    Write-Host "[CHECK] data\common\macro" -ForegroundColor Cyan
    if (Test-Path ".\data\common\macro") {
        Get-ChildItem ".\data\common\macro" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 30 Name, Length, LastWriteTime | Format-Table -AutoSize
    }
    else {
        Write-Host "data\common\macro does not exist yet." -ForegroundColor Yellow
    }

    Write-Host "[CHECK] existing macro agent packets" -ForegroundColor Cyan
    $packets = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_macro_agent_packet.json" -ErrorAction SilentlyContinue)
    Write-Host "macro_agent_packet count: $($packets.Count)" -ForegroundColor Green
    $packets | Select-Object -First 30 FullName | Format-Table -AutoSize
    exit 0
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name
    $field = if ([string]::IsNullOrWhiteSpace([string]$c.field)) { "반도체" } else { [string]$c.field }

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[MACRO] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        if ($Mode -in @("agent", "all", "one")) {
            if ($UseLLM) {
                Invoke-AlphaPython -PyArgs @(
                    ".\main.py", "macro",
                    "--company-dir", $slug,
                    "--company", $name
                )
            }
            else {
                Invoke-AlphaPython -PyArgs @(
                    ".\main.py", "macro",
                    "--company-dir", $slug,
                    "--company", $name,
                    "--no-llm"
                )
            }
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red
        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host "[ALL DONE] Macro25 $Mode" -ForegroundColor Green
