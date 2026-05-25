param(
    [ValidateSet("smoke", "intake", "finance", "market", "issue", "macro", "valuation", "tech-local", "agents", "chair-no-intake", "full-chair")]
    [string]$Mode = "smoke",

    [string]$Csv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [string]$OnlyCompanyDir = "",

    [switch]$ContinueOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Invoke-AlphaPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$PyArgs
    )

    Write-Host ("[PY] python " + ($PyArgs -join " ")) -ForegroundColor DarkGray
    & python @PyArgs

    if ($LASTEXITCODE -ne 0) {
        throw "python failed. exit_code=$LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $Csv)) {
    throw "Universe CSV not found: $Csv"
}

# IMPORTANT:
# Import-Csv | Where-Object returns a scalar PSCustomObject when only one row matches.
# With Set-StrictMode, PSCustomObject.Count can fail.
# Always wrap pipeline results with @(...).
$companies = @(
    Import-Csv -LiteralPath $Csv | Where-Object {
        [string]$_.include_in_evaluation -eq "1"
    }
)

if ($Mode -eq "smoke" -and [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
    $OnlyCompanyDir = "dbhitek"
}

if (-not [string]::IsNullOrWhiteSpace($OnlyCompanyDir)) {
    $companies = @(
        $companies | Where-Object {
            [string]$_.company_dir -eq $OnlyCompanyDir
        }
    )
}

Write-Host "[AlphaProve] Mode: $Mode" -ForegroundColor Cyan
Write-Host "[AlphaProve] CSV: $Csv" -ForegroundColor DarkGray
Write-Host "[AlphaProve] Target count: $($companies.Count)" -ForegroundColor Cyan

if ($companies.Count -eq 0) {
    throw "No target companies found. Check -OnlyCompanyDir or include_in_evaluation in CSV."
}

foreach ($c in $companies) {
    $slug = [string]$c.company_dir
    $name = [string]$c.company_name

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "[RUN] $name / $slug" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray

    try {
        if ($Mode -eq "smoke") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "valuation-intake", "--company-dir", $slug, "--company", $name)
            Invoke-AlphaPython -PyArgs @(".\main.py", "valuation", "--company-dir", $slug, "--company", $name)
        }
        elseif ($Mode -eq "intake") {
            Invoke-AlphaPython -PyArgs @(
                ".\main.py", "intake",
                "--company-dir", $slug,
                "--company", $name,
                "--agents", "macro,finance,tech,valuation",
                "--tech-max-patents", "0",
                "--tech-skip-network",
                "--tech-skip-agent"
            )
        }
        elseif ($Mode -eq "finance") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "finance", "--company", $name)
        }
        elseif ($Mode -eq "market") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "market", "--company-dir", $slug, "--company", $name)
        }
        elseif ($Mode -eq "issue") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "issue", "--company-dir", $slug, "--company", $name)
        }
        elseif ($Mode -eq "macro") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "macro", "--company-dir", $slug, "--company", $name, "--no-llm")
        }
        elseif ($Mode -eq "valuation") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "valuation-intake", "--company-dir", $slug, "--company", $name)
            Invoke-AlphaPython -PyArgs @(".\main.py", "valuation", "--company-dir", $slug, "--company", $name)
        }
        elseif ($Mode -eq "tech-local") {
            Invoke-AlphaPython -PyArgs @(
                ".\main.py", "intake",
                "--company-dir", $slug,
                "--company", $name,
                "--agents", "tech",
                "--tech-max-patents", "0",
                "--tech-skip-network",
                "--tech-skip-agent"
            )
            Invoke-AlphaPython -PyArgs @(".\main.py", "tech", "--company-dir", $slug, "--company", $name)
        }
        elseif ($Mode -eq "agents") {
            Invoke-AlphaPython -PyArgs @(
                ".\main.py", "intake",
                "--company-dir", $slug,
                "--company", $name,
                "--agents", "macro,finance,tech,valuation",
                "--tech-max-patents", "0",
                "--tech-skip-network",
                "--tech-skip-agent"
            )
            Invoke-AlphaPython -PyArgs @(".\main.py", "finance", "--company", $name)
            Invoke-AlphaPython -PyArgs @(".\main.py", "market", "--company-dir", $slug, "--company", $name)
            Invoke-AlphaPython -PyArgs @(".\main.py", "issue", "--company-dir", $slug, "--company", $name)
            Invoke-AlphaPython -PyArgs @(".\main.py", "macro", "--company-dir", $slug, "--company", $name, "--no-llm")
            Invoke-AlphaPython -PyArgs @(".\main.py", "valuation", "--company-dir", $slug, "--company", $name)
            Invoke-AlphaPython -PyArgs @(".\main.py", "tech", "--company-dir", $slug, "--company", $name)
        }
        elseif ($Mode -eq "chair-no-intake") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "chair", "--company-dir", $slug, "--company", $name, "--no-intake")
        }
        elseif ($Mode -eq "full-chair") {
            Invoke-AlphaPython -PyArgs @(".\main.py", "chair", "--company-dir", $slug, "--company", $name)
        }
        else {
            throw "Unknown mode: $Mode"
        }
    }
    catch {
        Write-Host "[ERROR] $name / $slug : $_" -ForegroundColor Red
        if (-not $ContinueOnError) {
            exit 1
        }
    }
}

Write-Host "[ALL DONE] $Mode" -ForegroundColor Green
