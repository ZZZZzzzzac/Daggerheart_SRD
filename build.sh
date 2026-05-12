#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_JSON="$SCRIPT_DIR/../DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/paratranz/DH-SRD-1.0-June-26-2025.md.json"
TARGET_DIR="$SCRIPT_DIR"

cd "$TARGET_DIR"

cd "$TARGET_DIR"

# 1. 复制最新 paratranz JSON
cp "$SRC_JSON" "src/DH-SRD-1.0-June-26-2025.md.json"
echo "JSON 已复制"

# 2. 生成 Hugo content
python scripts/build_srd.py
echo "Content 已生成"

# 3. Hugo 构建
hugo
echo "Build 完成: $TARGET_DIR/public"
