# Google Sheets history backend 전환 후 로컬 DB 산출물을 정리합니다.
# 삭제 전 먼저 화면에 대상 목록을 보여줍니다.

$ErrorActionPreference = "Stop"
Set-Location "C:\Agent_6.8"

$targets = @(
  ".\data\agent_history.db",
  ".\data\agent_history.db-shm",
  ".\data\agent_history.db-wal",
  ".\data\반도체\_sector_common\history_db_exports"
)

Write-Host "[cleanup candidates]"
foreach ($t in $targets) {
  if (Test-Path $t) {
    Write-Host "FOUND: $t"
  }
}

$answer = Read-Host "위 항목을 삭제할까요? 삭제하려면 YES 입력"
if ($answer -ne "YES") {
  Write-Host "취소했습니다."
  exit 0
}

foreach ($t in $targets) {
  if (Test-Path $t) {
    Remove-Item $t -Recurse -Force
    Write-Host "DELETED: $t"
  }
}

Write-Host "정리 완료"
