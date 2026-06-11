# deploy.ps1 — Daggerheart HTML SRD 部署
# 本地构建 + 推送代码到 GitHub（服务器不做 git pull）
# 内容编辑走在线编辑器 /SRD/edit/，服务器自行构建
# 代码更新（脚本/模板等）推送后，手动 SSH 到服务器 git pull
# 用法: 在 PowerShell 中运行 .\deploy.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host "[1/2] 构建 SRD..." -ForegroundColor Cyan
python scripts/build_srd.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/2] 推送代码..." -ForegroundColor Cyan

git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git push
    Write-Host "已推送更新。" -ForegroundColor Green
} else {
    Write-Host "无变化，无需推送。" -ForegroundColor Yellow
}

Write-Host "完成！服务器需手动 git pull 以更新代码。" -ForegroundColor Green
