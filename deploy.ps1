# deploy.ps1 — Daggerheart HTML SRD 构建 + 部署
# 构建后直接同步到服务器
# 用法: 在 PowerShell 中运行 .\deploy.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host "[1/2] 构建 SRD..." -ForegroundColor Cyan
python scripts/build_srd.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/2] 同步到服务器..." -ForegroundColor Cyan
$SSH_KEY = Resolve-Path "$ProjectDir\..\Daggerheart_VPS\.ssh\ssh-key-2026-03-20.key"
$SERVER = "ubuntu@151.145.76.60"
$REMOTE_DIR = "/var/www/SRD"

$remoteInit = "set -e; sudo chown ubuntu:ubuntu $REMOTE_DIR; rm -rf $REMOTE_DIR/*; cd $REMOTE_DIR; tar xzf -; sudo chown -R www-data:www-data $REMOTE_DIR; sudo chmod -R 755 $REMOTE_DIR"

tar czf - -C public . | ssh -i "$SSH_KEY" $SERVER $remoteInit

Write-Host "完成！" -ForegroundColor Green