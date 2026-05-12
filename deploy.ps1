# deploy.ps1 — Daggerheart HTML SRD 构建 + 部署
# 构建后自动推送到 GitHub 并同步到服务器
# 用法: 在 PowerShell 中运行 .\deploy.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host "[1/3] 构建 SRD..." -ForegroundColor Cyan
python scripts/build_srd.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] 推送 master..." -ForegroundColor Cyan
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

Write-Host "[3/3] 同步到服务器..." -ForegroundColor Cyan
$SSH_KEY = Resolve-Path "$ProjectDir\..\Daggerheart_VPS\.ssh\ssh-key-2026-03-20.key"
$SERVER = "ubuntu@151.145.76.60"
ssh -i "$SSH_KEY" $SERVER @'
  cd /var/www/SRD
  sudo chown -R ubuntu:ubuntu .
  git pull
  sudo chown -R www-data:www-data .
  sudo chmod -R 755 .
'@
if ($LASTEXITCODE -eq 0) {
    Write-Host "服务器已更新。" -ForegroundColor Green
}

Write-Host "完成！" -ForegroundColor Green
