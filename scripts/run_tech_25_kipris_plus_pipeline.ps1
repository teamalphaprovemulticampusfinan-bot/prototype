param(
    [ValidateSet("All30", "New25", "Base5")]
    [string]$Mode = "All30",

    [string]$Components = "bibliographic,claims,citation,family",

    [int]$MaxPatents = 0,

    [double]$SleepSec = 0.8,

    [int]$Timeout = 90,

    [switch]$ForceFetch,

    [switch]$RunChair,

    [string]$UniverseCsv = "",

    [switch]$StopOnError
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "============================================================"
    Write-Host $Message
    Write-Host "============================================================"
}

function Get-FirstNonEmpty {
    param(
        [object]$Row,
        [string[]]$Names
    )

    foreach ($name in $Names) {
        if ($Row.PSObject.Properties.Name -contains $name) {
            $value = [string]$Row.$name
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return $value.Trim()
            }
        }
    }
    return ""
}

function Resolve-UniverseCsv {
    param([string]$GivenPath)

    if (-not [string]::IsNullOrWhiteSpace($GivenPath)) {
        $p = Resolve-Path $GivenPath -ErrorAction Stop
        return $p.Path
    }

    $preferred = Get-ChildItem -Path ".\data" -Recurse -File -Filter "universe_30_semiconductor_20260514.csv" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($preferred) {
        return $preferred.FullName
    }

    $fallback = Get-ChildItem -Path ".\data" -Recurse -File -Filter "*universe*30*semiconductor*.csv" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($fallback) {
        return $fallback.FullName
    }

    throw "Universe CSV not found. Pass -UniverseCsv explicitly."
}

function Resolve-FieldName {
    param([string]$UniversePath)

    $file = Get-Item $UniversePath
    $dir = $file.Directory

    # Expected: data/<field>/_sector_common/universe/file.csv
    if ($dir -and $dir.Parent -and $dir.Parent.Parent) {
        return $dir.Parent.Parent.Name
    }

    return "반도체"
}

function Invoke-Checked {
    param(
        [string]$Title,
        [string]$Exe,
        [string[]]$ArgsList
    )

    Write-Host ""
    Write-Host "[RUN] $Title"
    Write-Host ($Exe + " " + ($ArgsList -join " "))

    & $Exe @ArgsList
    $code = $LASTEXITCODE

    if ($null -eq $code) {
        $code = 0
    }

    if ($code -ne 0) {
        throw "$Title failed with exit code $code"
    }
}

Write-Step "AlphaProve Tech KIPRIS Plus pipeline"

$universePath = Resolve-UniverseCsv -GivenPath $UniverseCsv
$fieldName = Resolve-FieldName -UniversePath $universePath

Write-Host "[Universe CSV] $universePath"
Write-Host "[Field] $fieldName"
Write-Host "[Mode] $Mode"
Write-Host "[Components] $Components"
Write-Host "[MaxPatents] $MaxPatents"
Write-Host "[SleepSec] $SleepSec"
Write-Host "[Timeout] $Timeout"
Write-Host "[ForceFetch] $ForceFetch"
Write-Host "[RunChair] $RunChair"

$rows = Import-Csv $universePath
if (-not $rows -or $rows.Count -eq 0) {
    throw "Universe CSV has no rows: $universePath"
}

$base5 = @("nepes", "hanmi", "hansol", "duksan", "ltc")

$targets = @()
foreach ($row in $rows) {
    $slug = Get-FirstNonEmpty -Row $row -Names @("company_dir", "slug", "ticker_slug")
    $company = Get-FirstNonEmpty -Row $row -Names @("company_name", "display_name", "corp_name", "company")

    if ([string]::IsNullOrWhiteSpace($slug) -or [string]::IsNullOrWhiteSpace($company)) {
        continue
    }

    if ($Mode -eq "New25" -and ($base5 -contains $slug)) {
        continue
    }

    if ($Mode -eq "Base5" -and -not ($base5 -contains $slug)) {
        continue
    }

    $targets += [pscustomobject]@{
        slug = $slug
        company = $company
    }
}

Write-Host "[Target count] $($targets.Count)"

if ($targets.Count -eq 0) {
    throw "No targets selected. Check Mode or universe CSV columns."
}

$logRoot = Join-Path (Split-Path $universePath -Parent) "tech_kipris_plus_run_logs"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$summaryPath = Join-Path $logRoot "kipris_plus_${Mode}_${timestamp}_summary.csv"

$summary = New-Object System.Collections.Generic.List[object]

$i = 0
foreach ($target in $targets) {
    $i += 1
    $slug = $target.slug
    $company = $target.company

    Write-Step "[$i/$($targets.Count)] $company / $slug"

    $status = "OK"
    $message = ""

    try {
        $cmdArgs = @(
            "main.py",
            "data-intake",
            "--agents", "tech",
            "--field", $fieldName,
            "--company-dir", $slug,
            "--company", $company,
            "--tech-kipris-plus-components", $Components,
            "--tech-max-patents", [string]$MaxPatents,
            "--tech-sleep-sec", [string]$SleepSec,
            "--tech-timeout", [string]$Timeout
        )

        if ($ForceFetch) {
            $cmdArgs += "--tech-force-fetch"
        }

        if ($StopOnError) {
            $cmdArgs += "--stop-on-error"
        }

        Invoke-Checked -Title "Tech data-intake: $company" -Exe "python" -ArgsList $cmdArgs

        if ($RunChair) {
            $chairArgs = @(
                "main.py",
                "chair",
                "--company-dir", $slug,
                "--company", $company,
                "--no-intake"
            )
            Invoke-Checked -Title "Chair no-intake: $company" -Exe "python" -ArgsList $chairArgs
        }
    }
    catch {
        $status = "FAIL"
        $message = $_.Exception.Message
        Write-Host "[FAIL] $company / $slug"
        Write-Host $message

        if ($StopOnError) {
            throw
        }
    }

    $summary.Add([pscustomobject]@{
        index = $i
        mode = $Mode
        field = $fieldName
        company_dir = $slug
        company_name = $company
        components = $Components
        max_patents = $MaxPatents
        status = $status
        message = $message
        finished_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }) | Out-Null
}

$summary | Export-Csv -Path $summaryPath -NoTypeInformation -Encoding UTF8

Write-Step "DONE"
Write-Host "[Summary CSV] $summaryPath"
