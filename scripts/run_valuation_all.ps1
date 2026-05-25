param(
    [int]$Years = 5,
    [switch]$SkipNetwork
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$companies = @(
    @{dir="nepes"; name="네패스"},
    @{dir="hanmi"; name="한미반도체"},
    @{dir="hansol"; name="한솔케미칼"},
    @{dir="duksan"; name="덕산테코피아"},
    @{dir="ltc"; name="LTC"}
)

foreach ($c in $companies) {
    Write-Host "`n================================================================================"
    Write-Host "[Valuation] $($c.name) / $($c.dir)"
    Write-Host "================================================================================"
    if ($SkipNetwork) {
        python main.py valuation-intake --company-dir $c.dir --company $c.name --years $Years --skip-network
        python main.py valuation --company-dir $c.dir --company $c.name --years $Years --skip-network
    } else {
        python main.py valuation-intake --company-dir $c.dir --company $c.name --years $Years
        python main.py valuation --company-dir $c.dir --company $c.name --years $Years
    }
}

Write-Host "`n[ALL DONE] Valuation Agent workbook/report/dashboard payload generated."
