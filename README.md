# 匕首之心 HTML SRD

[Daggerheart](https://www.daggerheart.com/) 系统参考文档的 HTML 静态站，中英双语。

在线地址：https://daggerheart.cn/SRD/

## 目录结构

```
Daggerheart_SRD/
├── src/
│   ├── pages/          # 各章节 md 源文件（zh.md + en.md）
│   ├── DH-SRD-CN.md    # 完整译文 md（从 paratranz 导出）
│   ├── DH-SRD-EN.md    # 完整英文 md
│   └── scores.json
├── scripts/             # Python 构建脚本 + 服务端代理
├── layouts/             # Hugo 模板（chrome/ _default/）
├── static/              # CSS / JS / 图片 / 字体 / bootstrap
├── content/             # （生成）Python 生成的 Hugo 页面，已 gitignore
├── public/              # （生成）Hugo 最终输出，已 gitignore
├── config.yaml          # Hugo 配置
├── page-toc.yaml        # 页面结构目录
├── build.ps1            # Windows 构建
├── build.sh             # Linux 构建
├── deploy.ps1           # Windows 构建 + 推送代码到 GitHub
└── deploy.sh            # Linux 构建 + 推送代码到 GitHub
```

## 构建

### 前置依赖

- Python 3 + `pyyaml` `markdown`
- [Hugo](https://gohugo.io/)（非 extended 版即可）

### 构建命令

```bash
python scripts/build_srd.py    # md → Hugo content → 静态页
# 或一键脚本
./build.ps1   # Windows（仅构建）
./build.sh    # Linux（仅构建）
```

输出在 `public/` 目录。

### 部署

```bash
./deploy.ps1   # Windows（构建 + 推送代码到 GitHub）
./deploy.sh    # Linux（构建 + 推送代码到 GitHub）
```

服务器端自行构建 `public/`，代码更新需手动 SSH 到服务器 `git pull`。

## 在线编辑器

`/SRD/edit/` 提供在线编辑功能：
- 左侧 CodeMirror 编辑 markdown，右侧实时预览
- 点击「保存」→ 直接写入服务器文件 → 自动 Hugo 构建 → 立即生效
- 编辑器页面有密码保护（nginx auth_basic），信任用户可编辑

## 协作流程

**内容编辑**：信任用户通过在线编辑器 `/SRD/edit/` 直写，即时生效。

**代码贡献**：编辑 `src/pages/` 以外的文件（脚本、模板、样式等）→ GitHub Fork/PR → 审核 → 合并。

## 外部依赖

构建依赖以下外部数据（不在本仓库中）：
- `DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/paratranz/DH-SRD-1.0-June-26-2025.md.json` — 翻译数据
- `DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/data/adversaries.json` — 敌人数据
- `DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/data/environments.json` — 环境数据

预期 `DaggerHeart_CN` 与本仓库同级目录。

## 授权

© 2025 Critical Role LLC. 依据 [Darrington Press 社群游戏授权条款](https://www.darringtonpress.com/license) 发布，视为 Public Game Content。
