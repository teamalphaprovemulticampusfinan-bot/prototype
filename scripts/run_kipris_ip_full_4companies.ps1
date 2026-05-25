param(
  [int]$MaxPatents = 0,
  [double]$SleepSec = 0.6,
  [int]$Timeout = 30,
  [switch]$RunChair,
  [switch]$ForceFetch,
  [switch]$SkipNetwork,
  [switch]$SkipTech,
  [switch]$ContinueOnError,
  [string[]]$Only = @()
)

$ErrorActionPreference = "Stop"

# 프로젝트 루트 기준으로 실행되어야 합니다.
# 예: cd C:\Agent_6.8
#     .\scripts\run_kipris_ip_full_4companies.ps1 -MaxPatents 0

chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# 네패스 성공 케이스와 동일하게 KIPRIS Plus key parameter는 ServiceKey를 우선 사용합니다.
# 실제 키 값은 .env에만 두고 여기에는 절대 쓰지 않습니다.
if (-not $env:KIPRIS_PLUS_KEY_PARAM) { $env:KIPRIS_PLUS_KEY_PARAM = "ServiceKey" }
if (-not $env:KIPRIS_PLUS_API_KEY_PARAM) { $env:KIPRIS_PLUS_API_KEY_PARAM = "ServiceKey" }
if (-not $env:KIPRIS_PLUS_CLAIMS_KEY_PARAM) { $env:KIPRIS_PLUS_CLAIMS_KEY_PARAM = "ServiceKey" }
if (-not $env:KIPRIS_PLUS_FAMILY_KEY_PARAM) { $env:KIPRIS_PLUS_FAMILY_KEY_PARAM = "ServiceKey" }

$argsList = @(
  "scripts/run_kipris_ip_full_4companies.py",
  "--field", "반도체",
  "--max-patents", "$MaxPatents",
  "--sleep-sec", "$SleepSec",
  "--timeout", "$Timeout"
)

foreach ($item in $Only) {
  if ($item -and $item.Trim().Length -gt 0) {
    $argsList += @("--only", $item.Trim())
  }
}

if ($RunChair) { $argsList += "--run-chair" }
if ($ForceFetch) { $argsList += "--force-fetch" }
if ($SkipNetwork) { $argsList += "--skip-network" }
if ($SkipTech) { $argsList += "--skip-tech" }
if ($ContinueOnError) { $argsList += "--continue-on-error" }

Write-Host "================================================================================"
Write-Host "KIPRIS IP Evidence Full Pipeline - 4 companies"
Write-Host "================================================================================"
Write-Host "MaxPatents = $MaxPatents  (0 = normalized CSV 전체 특허)"
Write-Host "SleepSec   = $SleepSec"
Write-Host "Timeout    = $Timeout"
Write-Host "RunChair   = $RunChair"
Write-Host "ForceFetch = $ForceFetch"
Write-Host "SkipNetwork= $SkipNetwork"
Write-Host "SkipTech   = $SkipTech"
Write-Host "Only       = $($Only -join ', ')"
Write-Host "================================================================================"

python @argsList
