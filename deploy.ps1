# deploy.ps1 — Daggerheart HTML SRD 构建 + 部署
# 构建后将 public/ 内容复制到仓库根，commit + push master
# 用法: 在 PowerShell 中运行 .\deploy.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host "[1/2] 构建 SRD..." -ForegroundColor Cyan
python scripts/build_srd.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/2] 推送 master..." -ForegroundColor Cyan

# 复制构建产物到仓库根（用 robocopy 避免小文件过多报错）
if (-not (Test-Path "public")) {
    Write-Host "错误: public/ 不存在" -ForegroundColor Red
    exit 1
}
Get-ChildItem -Path "public" | Copy-Item -Destination $ProjectDir -Recurse -Force 2>&1 | Out-Null

git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git push
    Write-Host "已推送更新。" -ForegroundColor Green
} else {
    Write-Host "构建内容无变化，无需推送。" -ForegroundColor Yellow
}
