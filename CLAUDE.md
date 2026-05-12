# Daggerheart HTML SRD

独立于 VPS 仓库的匕首之心 SRD 项目。中英双语 HTML 静态站，Hugo 构建。

在线地址：https://daggerheart.cn/SRD/

## 项目定位

原 daggerheart 灰机 wiki 站有版权风险可能下架，此站转正成为主站。

**范围**：
- SRD 文档内容（md 源码）
- 导航页 + 小工具源码（monorepo）
- 外链到第三方工具和网友自建服务
- 大项目（车卡器、战斗管理）保持独立仓库

**不在此项目内**：
- 运行中的服务（在 VPS 上）
- 外部依赖数据（DaggerHeart_CN 翻译项目）

## 目录结构

```
Daggerheart_SRD/
├── src/
│   ├── pages/           # 各章节 md 源文件（zh.md + en.md）
│   ├── DH-SRD-CN.md     # 完整译文 md（从 paratranz 导出）
│   ├── DH-SRD-EN.md     # 完整英文 md
│   └── scores.json
├── scripts/             # Python 构建脚本
├── layouts/             # Hugo 模板（chrome/ _default/）
├── static/              # CSS / JS / 图片 / 字体 / bootstrap
├── content/             # （生成）Python 生成的 Hugo 页面，已 gitignore
├── public/              # （生成）Hugo 最终输出，已 gitignore
├── config.yaml          # Hugo 配置
├── page-toc.yaml        # 页面结构目录
├── build.ps1            # Windows 构建
├── build.sh             # Linux 构建
├── deploy.ps1           # Windows 构建 + 部署（tar+scp 到服务器）
├── deploy.sh            # Linux 构建 + 部署（tar+scp 到服务器）
├── README.md
├── LICENSE
├── .gitignore
└── CLAUDE.md
```

## 构建

### 前置依赖
- Python 3 + pyyaml + markdown
- Hugo（非 extended 版即可）
- DaggerHeart_CN 仓库在同级目录（外部数据依赖）

### 命令
```
python scripts/build_srd.py   # md → Hugo content → 静态页输出到 public/
./build.ps1                    # Windows 一键
./build.sh                     # Linux 一键
```

### 构建决策（B 方案）
- 构建在本机或 CI 完成，服务器只 `git pull` 不构建
- `build_srd.py` 内部调 `hugo`，`config.yaml` 输出到 `public/`

## 协作流程

**流程**：贡献者 GitHub 网页上 Edit → Propose change → PR → 审核 → 合并 → 维护者本地构建并部署

**贡献者**：
- 初期：翻译组成员（会教 GitHub 网页操作，不要求会 git 命令行）
- 后期：一般网友 fork + PR

**编辑规范**：
- 中文改 `zh.md`，英文改 `en.md`，不要混改
- 大改动先开 issue 讨论
- PR review 由维护者负责

## 在线编辑（计划中）

未来可加一个纯前端 SPA 编辑器：
- 左边 CodeMirror 编辑 md
- 右边实时渲染（marked.js + 现有 CSS）
-「保存」调 GitHub API → 新 branch + commit + PR
- 不占服务器资源，Micro 实例足够

不计划做：
- 自建数据库保存内容（走 GitHub PR 审核流程）
- 实时协同编辑
- 服务端搜索（用客户端 lunr.js/flexsearch 即可）

## 服务器

**Daggerheart_Tools**（151.145.76.60, VM.Standard.E2.1.Micro, 1C1G）

现状负载：
- 内存 956M，已用 ~19%，可用 616M
- 磁盘 45G，已用 9%
- CPU load 0.00

当前方案（静态页 + 客户端搜索 + 纯前端编辑器）Micro 绰绰有余。
需要升配的信号：自建后端数据库、WebSocket 协同、服务端渲染。

### 部署方式
本地构建 → commit + push 到 master → SSH 上服务器 pull
- 运行 `./deploy.ps1`（Win）或 `./deploy.sh`（Linux）
- 构建产物复制到仓库根目录后一起提交，nginx `alias /var/www/SRD/;` 直接服务
- 需要 `Daggerheart_VPS` 仓库同级（SSH 密钥路径 `../Daggerheart_VPS/.ssh/`）

### 三台 VPS
| 服务器 | IP | 用途 |
|--------|----|------|
| SillyTavern | 140.245.85.33 | ST 酒馆 + SealChat + SealDice |
| API | 161.33.207.162 | MetaAPI AI 中转 |
| Daggerheart_Tools | 151.145.76.60 | daggerheart.cn 所有工具 + SRD |

所有服务器用户 `ubuntu`，SSH 密钥在 `~/.ssh/authorized_keys`。

## 外部依赖

```
../DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/
├── paratranz/DH-SRD-1.0-June-26-2025.md.json   # 翻译数据（build.sh 引用）
└── data/
    ├── adversaries.json                          # 敌人数据
    └── environments.json                         # 环境数据
```

预期 `DaggerHeart_CN` 与本仓库同级目录。脚本中的路径均为相对路径。

## 授权

© 2025 Critical Role LLC. Darrington Press 社群游戏授权条款，Public Game Content。
