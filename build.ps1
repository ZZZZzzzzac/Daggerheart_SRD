# build.ps1 — Daggerheart HTML SRD 一键构建
# 用法: 在 PowerShell 中运行 .\build.ps1

$ProjectDir = $PSScriptRoot

Set-Location $ProjectDir

Write-Host "[1/2] 从 CN/EN markdown 生成 Hugo content..." -ForegroundColor Cyan
python scripts/build_srd.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "  OK" -ForegroundColor Green

Write-Host "[2/2] Hugo 构建..." -ForegroundColor Cyan
hugo
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "  OK" -ForegroundColor Green

Write-Host "`n构建完成！输出目录: $ProjectDir\public" -ForegroundColor Green
Write-Host "预览: 运行 hugo server 然后访问 http://localhost:1313/SRD/" -ForegroundColor Cyan
