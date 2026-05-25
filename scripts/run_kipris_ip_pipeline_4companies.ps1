param(
    [int]$MaxPatents = 0,
    [double]$SleepSec = 0.3,
    [switch]$RunChair
)

$ErrorActionPreference = "Stop"

$Field = "반도체"

$Companies = @(
    @{ Name = "한미반도체"; Slug = "hanmi" },
    @{ Name = "한솔케미칼"; Slug = "hansol" },
    @{ Name = "덕산테코피아"; Slug = "duksan" },
    @{ Name = "엘티씨"; Slug = "ltc" }
)

function Find-Script {
    param([string[]]$Candidates)

    foreach ($p in $Candidates) {
        if (Test-Path $p) {
            return $p
        }
    }
    return $null
}

function Run-Cmd {
    param(
        [string]$Title,
        [scriptblock]$Block
    )

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "[RUN] $Title" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    & $Block

    if ($LASTEXITCODE -ne 0) {
        throw "[FAILED] $Title / exit=$LASTEXITCODE"
    }
}

$ClaimScript = Find-Script @(
    ".\scripts\fetch_kipris_plus_claims.py"
)

$CitationScript = Find-Script @(
    ".\scripts\fetch_kipris_plus_citations.py",
    ".\scripts\fetch_kipris_plus_citation.py"
)

$FamilyScript = Find-Script @(
    ".\scripts\fetch_kipris_plus_family.py"
)

$CompositeScript = Find-Script @(
    ".\scripts\build_tech_ip_evidence_composite.py"
)

$LegalScript = Find-Script @(
    ".\scripts\normalize_kipris_ip_legal.py",
    ".\scripts\build_tech_ip_legal_features.py"
)

if (-not $ClaimScript) { throw "fetch_kipris_plus_claims.py를 찾지 못했습니다." }
if (-not $CitationScript) { throw "fetch_kipris_plus_citations.py 또는 fetch_kipris_plus_citation.py를 찾지 못했습니다." }
if (-not $FamilyScript) { throw "fetch_kipris_plus_family.py를 찾지 못했습니다." }
if (-not $CompositeScript) { throw "build_tech_ip_evidence_composite.py를 찾지 못했습니다." }

# Family API는 네패스 때 확인한 정상 조합을 강제
$env:KIPRIS_PLUS_FAMILY_APP_PARAM = "applicationNumber"
$env:KIPRIS_PLUS_KEY_PARAM = "ServiceKey"

Write-Host ""
Write-Host "[CONFIG]" -ForegroundColor Yellow
Write-Host "- Field: $Field"
Write-Host "- MaxPatents: $MaxPatents"
Write-Host "- SleepSec: $SleepSec"
Write-Host "- Claims script: $ClaimScript"
Write-Host "- Citation script: $CitationScript"
Write-Host "- Family script: $FamilyScript"
Write-Host "- Composite script: $CompositeScript"
Write-Host "- Legal script: $LegalScript"
Write-Host ""

foreach ($c in $Companies) {
    $Name = $c.Name
    $Slug = $c.Slug
    $TechDir = ".\data\$Field\$Name\tech"

    Write-Host ""
    Write-Host "############################################################" -ForegroundColor Green
    Write-Host "# COMPANY: $Name ($Slug)" -ForegroundColor Green
    Write-Host "############################################################" -ForegroundColor Green

    if (-not (Test-Path $TechDir)) {
        throw "Tech 폴더가 없습니다: $TechDir"
    }

    $BibCsv = Join-Path $TechDir "$Slug`_kipris_bibliographic_normalized.csv"
    $PatentCsv = Join-Path $TechDir "$Slug`_kipris_patents_normalized.csv"

    if (-not (Test-Path $BibCsv) -and -not (Test-Path $PatentCsv)) {
        throw "KIPRIS normalized CSV가 없습니다: $BibCsv 또는 $PatentCsv"
    }

    $LegalFeature = Join-Path $TechDir "tech_ip_legal_features.json"

    if (-not (Test-Path $LegalFeature)) {
        if ($LegalScript) {
            Run-Cmd "Legal/IP stability feature 생성 - $Name" {
                python $LegalScript `
                    --field $Field `
                    --company-name $Name `
                    --company-slug $Slug `
                    --force
            }
        }
        else {
            throw "Legal feature가 없고 generic legal script도 없습니다: $LegalFeature"
        }
    }
    else {
        Write-Host "[SKIP] Legal feature exists: $LegalFeature" -ForegroundColor DarkYellow
    }

    Run-Cmd "KIPRIS Plus Claims 수집 - $Name" {
        python $ClaimScript `
            --field $Field `
            --company-name $Name `
            --company-slug $Slug `
            --max-patents $MaxPatents `
            --sleep-sec $SleepSec `
            --force
    }

    Run-Cmd "KIPRIS Plus Citation 수집 - $Name" {
        python $CitationScript `
            --field $Field `
            --company-name $Name `
            --company-slug $Slug `
            --max-patents $MaxPatents `
            --sleep-sec $SleepSec `
            --force
    }

    Run-Cmd "KIPRIS Plus Family 수집 - $Name" {
        python $FamilyScript `
            --field $Field `
            --company-name $Name `
            --company-slug $Slug `
            --max-patents $MaxPatents `
            --sleep-sec $SleepSec `
            --force `
            --key-param ServiceKey `
            --app-param applicationNumber
    }

    Run-Cmd "IP Evidence Composite 생성 - $Name" {
        python $CompositeScript `
            --field $Field `
            --company-name $Name `
            --company-slug $Slug
    }

    Run-Cmd "Tech Agent 실행 및 IP Evidence Bridge 반영 - $Name" {
        python main.py tech --company-dir $Slug --company $Name
    }

    if ($RunChair) {
        $ChairDir = ".\data\$Field\$Name\chair"
        Remove-Item "$ChairDir\*" -Recurse -Force -ErrorAction SilentlyContinue

        Run-Cmd "Chair Agent 실행 - $Name" {
            python main.py chair --company-dir $Slug --company $Name
        }
    }

    Write-Host ""
    Write-Host "[DONE] $Name ($Slug)" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "[ALL DONE] 4개 기업 KIPRIS IP Evidence pipeline 완료" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

