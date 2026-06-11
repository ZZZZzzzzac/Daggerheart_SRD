# build.ps1 — Daggerheart HTML SRD 一键构建
# 用法: 在 PowerShell 中运行 .\build.ps1

$ProjectDir = $PSScriptRoot

Set-Location $ProjectDir

Write-Host "构建 SRD（生成 content + Hugo）..." -ForegroundColor Cyan
python scripts/build_srd.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n构建完成！输出目录: $ProjectDir\public" -ForegroundColor Green
