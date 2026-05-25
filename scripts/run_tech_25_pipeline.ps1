param(
    [ValidateSet("list", "bootstrap", "seed", "intake", "agent", "one", "all", "check")]
    [string]$Mode = "list",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [string]$OnlyCompanyDir = "",

    [switch]$IncludeOriginal5,

    [switch]$UseNetwork,

    [switch]$ForceFetch,

    [switch]$OverwriteSeed,

    [int]$MaxPatents = 0,

    [double]$SleepSec = 0.6,

    [int]$Timeout = 60,

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

Write-Host "[AlphaProve Tech25] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve Tech25] Target count: $($companies.Count)" -ForegroundColor Cyan
Write-Host "[AlphaProve Tech25] UseNetwork: $UseNetwork, ForceFetch: $ForceFetch, MaxPatents: $MaxPatents" -ForegroundColor DarkGray

if ($companies.Count -eq 0) {
    throw "No target companies. Check -OnlyCompanyDir or CSV."
}

if ($Mode -eq "list") {
    $companies | Select-Object company_name, stock_code, market, company_dir, peer_group | Format-Table -AutoSize
    exit 0
}

function Run-Bootstrap {
    $bootstrapArgs = @(".\scripts\bootstrap_tech_25_universe.py", "--csv", $Csv)

    if (-not $IncludeOriginal5) {
        $bootstrapArgs += "--only-new-25"
    }

    Invoke-AlphaPython -PyArgs $bootstrapArgs
}

function Run-SeedForSlug {
    param(
        [Parameter(Mandatory=$true)][string]$Slug,
        [switch]$ForceOverwrite
    )

    $seedArgs = @(".\scripts\seed_tech_25_local_proxy.py", "--csv", $Csv, "--only-company-dir", $Slug)

    if ($OverwriteSeed -or $ForceOverwrite) {
        $seedArgs += "--overwrite"
    }

    Invoke-AlphaPython -PyArgs $seedArgs
}

function Run-Seed {
    foreach ($c in $companies) {
        Run-SeedForSlug -Slug ([string]$c.company_dir)
    }
}

if ($Mode -in @("bootstrap", "seed", "intake", "agent", "one", "all", "check")) {
    Run-Bootstrap
}

if ($Mode -eq "bootstrap") {
    Write-Host "[DONE] bootstrap" -ForegroundColor Green
    exit 0
}

if ($Mode -in @("seed", "intake", "agent", "one", "all")) {
    Run-Seed
}

if ($Mode -eq "seed") {
    Write-Host "[DONE] seed" -ForegroundColor Green
    exit 0
}

function Run-TechIntake {
    param(
        [Parameter(Mandatory=$true)][string]$Slug,
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$Field
    )

    $args = @(
        ".\main.py", "intake",
        "--company-dir", $Slug,
        "--company", $Name,
        "--field", $Field,
        "--agents", "tech",
        "--tech-max-patents", "$MaxPatents",
        "--tech-sleep-sec", "$SleepSec",
        "--tech-timeout", "$Timeout",
        "--tech-skip-agent"
    )

    if (-not $UseNetwork) {
        $args += "--tech-skip-network"
    }

    if ($ForceFetch) {
        $args += "--tech-force-fetch"
    }

    Invoke-AlphaPython -PyArgs $args
}

function Run-TechAgent {
    param(
        [Parameter(Mandatory=$true)][string]$Slug,
        [Parameter(Mandatory=$true)][string]$Name
    )

    Invoke-AlphaPython -PyArgs @(
        ".\main.py", "tech",
        "--company-dir", $Slug,
        "--company", $Name
    )
}

if ($Mode -eq "check") {
    Write-Host "[CHECK] tech packets" -ForegroundColor Cyan
    $packets = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_tech_agent_packet.json" -ErrorAction SilentlyContinue)
    Write-Host "tech_agent_packet count: $($packets.Count)" -ForegroundColor Green
    $packets | Select-Object -First 40 FullName | Format-Table -AutoSize

    Write-Host "[CHECK] tech chair summaries" -ForegroundColor Cyan
    $summaries = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_tech_chair_summary.md" -ErrorAction SilentlyContinue)
    Write-Host "tech_chair_summary md count: $($summaries.Count)" -ForegroundColor Green
    $summaries | Select-Object -First 40 FullName | Format-Table -AutoSize

    Write-Host "[CHECK] local proxy seeds" -ForegroundColor Cyan
    $seeds = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "*_tech_local_proxy_evidence.md" -ErrorAction SilentlyContinue)
    Write-Host "local proxy seed count: $($seeds.Count)" -ForegroundColor Green
    $seeds | Select-Object -First 40 FullName | Format-Table -AutoSize

    Write-Host "[CHECK] quantified metrics rows" -ForegroundColor Cyan
    $metrics = @(Get-ChildItem ".\data\반도체" -Recurse -Filter "quantified_metrics.csv" -ErrorAction SilentlyContinue)

    $metricRows = @(
        foreach ($m in ($metrics | Select-Object -First 40)) {
            $rowCount = 0

            try {
                $rowCount = @((Import-Csv -LiteralPath $m.FullName)).Count
            }
            catch {
                $rowCount = -1
            }

            [PSCustomObject]@{
                Rows = $rowCount
                Path = $m.FullName
            }
        }
    )

    if ($metricRows.Count -gt 0) {
        $metricRows | Format-Table -AutoSize
    }
    else {
        Write-Host "No quantified_metrics.csv files found." -ForegroundColor Yellow
    }

    exit 0
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name
    $field = if ([string]::IsNullOrWhiteSpace([string]$c.field)) { "반도체" } else { [string]$c.field }

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[TECH] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        if ($Mode -in @("intake", "one", "all")) {
            Run-TechIntake -Slug $slug -Name $name -Field $field

            # IMPORTANT:
            # Existing Tech Intake can create 0-row quantified_metrics.csv for new 25 companies
            # that do not have dedicated rows in tech_template.xlsx.
            # Re-seed fallback evidence after intake so Tech Agent has non-empty bootstrap evidence.
            Write-Host "[RESEED] restore local proxy quantified metrics after Tech Intake: $name / $slug" -ForegroundColor Yellow
            Run-SeedForSlug -Slug $slug -ForceOverwrite
        }

        if ($Mode -in @("agent", "one", "all")) {
            Run-TechAgent -Slug $slug -Name $name
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red

        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host "[POST] Try syncing investor scorecards if script exists" -ForegroundColor Cyan

if (Test-Path ".\scripts\sync_tech_investor_scorecards.py") {
    try {
        Invoke-AlphaPython -PyArgs @(".\scripts\sync_tech_investor_scorecards.py", "--all")
    }
    catch {
        Write-Host "[WARN] sync_tech_investor_scorecards.py failed: $_" -ForegroundColor Yellow

        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host "[ALL DONE] Tech25 $Mode" -ForegroundColor Green
