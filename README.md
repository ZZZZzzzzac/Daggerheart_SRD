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
├── scripts/            # 构建脚本
├── layouts/            # Hugo 模板
├── static/             # CSS / JS / 图片 / 字体
├── content/            # （生成）Python 脚本生成的 Hugo 页面
├── public/             # （生成）最终静态站输出
├── config.yaml         # Hugo 配置
├── page-toc.yaml       # 页面结构目录
├── build.ps1           # Windows 构建脚本
└── build.sh            # Linux 构建脚本
```

## 构建

### 前置依赖

- Python 3 + `pyyaml` `markdown`
- [Hugo](https://gohugo.io/)（非 extended 版即可）

### 构建命令

```bash
python scripts/build_srd.py    # md → Hugo content → 静态页
# 或一键脚本
./build.ps1   # Windows
./build.sh    # Linux
```

输出在 `public/` 目录。

## 协作流程

1. **编辑内容**：修改 `src/pages/` 下的 `zh.md`（中文）或 `en.md`（英文）
2. **提交 PR**：在 GitHub 上创建 Pull Request
3. **审核**：维护者 review 后合并
4. **发布**：维护者合并后本地构建，将 `public/` 部署到服务器

### 对贡献者的要求

- 中文内容修改请只改 `zh.md`，英文只改 `en.md`
- 大范围改动前先开 issue 讨论

## 外部依赖

构建依赖以下外部数据（不在本仓库中）：
- `DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/paratranz/DH-SRD-1.0-June-26-2025.md.json` — 翻译数据
- `DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/data/adversaries.json` — 敌人数据
- `DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/data/environments.json` — 环境数据

预期 `DaggerHeart_CN` 与本仓库同级目录。

## 授权

© 2025 Critical Role LLC. 依据 [Darrington Press 社群游戏授权条款](https://www.darringtonpress.com/license) 发布，视为 Public Game Content。
