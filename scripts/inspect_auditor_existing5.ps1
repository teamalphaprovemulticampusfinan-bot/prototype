param(
    [switch]$IncludeAll30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null

$targets = @(
  @{name="네패스"; slug="nepes"},
  @{name="한미반도체"; slug="hanmi"},
  @{name="한솔케미칼"; slug="hansol"},
  @{name="덕산테코피아"; slug="duksan"},
  @{name="엘티씨"; slug="ltc"}
)

if ($IncludeAll30) {
    $csv = ".\data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv"
    if (Test-Path $csv) {
        $targets = @(
            Import-Csv $csv | Where-Object { [string]$_.include_in_evaluation -eq "1" } |
            ForEach-Object { @{name=[string]$_.company_name; slug=[string]$_.company_dir} }
        )
    }
}

function Get-PropValue {
    param(
        [Parameter(Mandatory=$false)]$Object,
        [Parameter(Mandatory=$true)][string]$Name,
        $Default = $null
    )

    if ($null -eq $Object) {
        return $Default
    }

    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) {
        return $Default
    }

    return $prop.Value
}

function Join-IfArray {
    param($Value)

    if ($null -eq $Value) {
        return ""
    }

    if ($Value -is [System.Array]) {
        return ($Value -join ", ")
    }

    return [string]$Value
}

function Show-JsonSummary {
    param(
        [string]$Label,
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        Write-Host "  - $Label 없음: $Path" -ForegroundColor Yellow
        return
    }

    Write-Host "  - $Label 있음: $Path" -ForegroundColor Green

    try {
        $j = Get-Content $Path -Encoding UTF8 | ConvertFrom-Json
        $keys = ($j.PSObject.Properties.Name -join ", ")
        Write-Host "    top-level keys: $keys" -ForegroundColor DarkGray

        $result = Get-PropValue -Object $j -Name "result"
        if ($null -ne $result) {
            $resultKeys = ($result.PSObject.Properties.Name -join ", ")
            Write-Host "    result keys: $resultKeys" -ForegroundColor DarkGray
        }

        $policy = Get-PropValue -Object $j -Name "policy"
        $quant = Get-PropValue -Object $j -Name "quantitative_decision"

        # New/current receipt schemas often keep status under result.
        $passed = Get-PropValue -Object $j -Name "passed"
        if ($null -eq $passed) { $passed = Get-PropValue -Object $result -Name "passed" }
        if ($null -eq $passed) { $passed = Get-PropValue -Object $result -Name "overall_passed" }
        if ($null -eq $passed) { $passed = Get-PropValue -Object $result -Name "raw_passed" }

        $mode = Get-PropValue -Object $j -Name "mode"
        if ($null -eq $mode) { $mode = Get-PropValue -Object $j -Name "three_stage_policy" }
        if ($null -eq $mode) { $mode = Get-PropValue -Object $policy -Name "mode" }

        $failOpen = Get-PropValue -Object $j -Name "fail_open"
        if ($null -eq $failOpen) { $failOpen = Get-PropValue -Object $j -Name "fail_open_enabled" }
        if ($null -eq $failOpen) { $failOpen = Get-PropValue -Object $result -Name "fail_open" }
        if ($null -eq $failOpen) { $failOpen = Get-PropValue -Object $policy -Name "fail_open" }

        $threshold = Get-PropValue -Object $j -Name "threshold"
        if ($null -eq $threshold) { $threshold = Get-PropValue -Object $j -Name "pass_threshold" }
        if ($null -eq $threshold) { $threshold = Get-PropValue -Object $result -Name "threshold" }
        if ($null -eq $threshold) { $threshold = Get-PropValue -Object $result -Name "pass_threshold" }

        $minActual = Get-PropValue -Object $j -Name "min_actual_match"
        if ($null -eq $minActual) { $minActual = Get-PropValue -Object $result -Name "min_actual_match" }
        if ($null -eq $minActual) { $minActual = Get-PropValue -Object $result -Name "min_actual_match_pct" }

        $avgActual = Get-PropValue -Object $j -Name "avg_actual_match"
        if ($null -eq $avgActual) { $avgActual = Get-PropValue -Object $result -Name "avg_actual_match" }
        if ($null -eq $avgActual) { $avgActual = Get-PropValue -Object $result -Name "avg_actual_match_pct" }

        $failedAgents = Get-PropValue -Object $j -Name "failed_agents"
        if ($null -eq $failedAgents) { $failedAgents = Get-PropValue -Object $result -Name "failed_agents" }

        $finalRecommendation = Get-PropValue -Object $j -Name "final_recommendation"
        if ($null -eq $finalRecommendation) { $finalRecommendation = Get-PropValue -Object $result -Name "final_recommendation" }
        if ($null -eq $finalRecommendation) { $finalRecommendation = Get-PropValue -Object $quant -Name "final_recommendation" }
        if ($null -eq $finalRecommendation) { $finalRecommendation = Get-PropValue -Object $quant -Name "auditor_recommendation" }
        if ($null -eq $finalRecommendation) { $finalRecommendation = Get-PropValue -Object $quant -Name "final_label" }

        $weightedSignal = Get-PropValue -Object $j -Name "weighted_signal"
        if ($null -eq $weightedSignal) { $weightedSignal = Get-PropValue -Object $result -Name "weighted_signal" }
        if ($null -eq $weightedSignal) { $weightedSignal = Get-PropValue -Object $quant -Name "weighted_signal" }

        [PSCustomObject]@{
            schema_hint = if ($null -ne $result) { "nested_result_schema" } elseif ($null -ne $quant) { "chair_packet_schema" } else { "top_level_or_unknown" }
            passed = $passed
            mode = $mode
            fail_open = $failOpen
            threshold = $threshold
            min_actual_match = $minActual
            avg_actual_match = $avgActual
            failed_agents = (Join-IfArray $failedAgents)
            final_recommendation = $finalRecommendation
            weighted_signal = $weightedSignal
        } | Format-List
    }
    catch {
        Write-Host "    JSON 처리 실패: $_" -ForegroundColor Red
    }
}

foreach ($c in $targets) {
    $name = $c.name
    $slug = $c.slug
    $root = ".\data\반도체\$name\auditor"

    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "$name / $slug" -ForegroundColor Cyan

    if (-not (Test-Path $root)) {
        Write-Host "auditor 폴더 없음: $root" -ForegroundColor Yellow
        continue
    }

    Show-JsonSummary -Label "first_auditor_receipt" -Path (Join-Path $root "first_auditor\first_auditor_receipt.json")
    Show-JsonSummary -Label "auditor_chair_packet" -Path (Join-Path $root "first_auditor\compact_agent_packets\auditor_chair_packet.json")

    $jsons = @(Get-ChildItem $root -Recurse -Filter "*.json" -ErrorAction SilentlyContinue)
    Write-Host "  json count: $($jsons.Count)" -ForegroundColor DarkGray
    $jsons | Select-Object -First 12 FullName | Format-Table -AutoSize
}
