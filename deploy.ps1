# deploy.ps1 — Daggerheart HTML SRD 构建 + 部署
# 构建后把 public/ 内容 commit + push 到 master
# 服务器 nginx 配置指向 public/ 子目录，git pull 即更新
# 用法: 在 PowerShell 中运行 .\deploy.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host "[1/2] 构建 SRD..." -ForegroundColor Cyan
python scripts/build_srd.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/2] commit + push master..." -ForegroundColor Cyan
git add -f public/
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git push
    Write-Host "已推送更新。" -ForegroundColor Green
} else {
    Write-Host "构建内容无变化，无需推送。" -ForegroundColor Yellow
}
