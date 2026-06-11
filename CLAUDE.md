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
├── scripts/             # Python 构建脚本 + 服务端代理
│   ├── build_srd.py
│   ├── proxy_server.py  # GitHub API 代理（零依赖，纯 stdlib）
│   └── proxy_server.service  # systemd 单元文件模板
├── layouts/             # Hugo 模板（chrome/ _default/）
├── static/              # CSS / JS / 图片 / 字体 / bootstrap
├── content/             # （生成）Python 生成的 Hugo 页面，已 gitignore
├── public/              # Hugo 最终输出，直接提交 git（nginx 从此目录 serve）
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

## 在线编辑器

`/SRD/edit/` 提供在线编辑功能：
- 左边 CodeMirror 编辑 md，右边实时预览
-「保存」→ 创建 Git 分支 + commit + PR
- 两种提交模式：
  - **服务端代理**（默认）：前端调 `/SRD/api/submit-pr`，服务器 `proxy_server.py` 持有 GitHub token 代发 PR
  - **用户自有 token**：在 localStorage 中设置 `gh_token`，编辑器直接用此 token 调 GitHub API

### 代理服务器

`scripts/proxy_server.py` — 零外部依赖，纯 Python stdlib HTTP 服务器：
- 监听 `127.0.0.1:5000`，由 nginx `proxy_pass` 暴露为 `/SRD/api/submit-pr`
- 安全检查：只允许编辑 `src/pages/` 路径下的文件
- Token 通过 systemd 环境变量注入，不入任何文件

### 服务端配置

**systemd**：`/etc/systemd/system/proxy_server.service`
```
Environment=GH_TOKEN=<fine-grained PAT>
ExecStart=/usr/bin/python3 /var/www/SRD/scripts/proxy_server.py
```

**nginx**：在 `sites-enabled/daggerheart.conf` 的 `/SRD/` location 之前：
```nginx
location ^~ /SRD/api/ {
    proxy_pass http://127.0.0.1:5000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**部署**：`deploy.ps1` / `deploy.sh` 的最后一步会自动 `systemctl restart proxy_server`。

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

当前方案（静态页 + 客户端搜索 + 编辑器服务端代理）Micro 绰绰有余。
需要升配的信号：自建后端数据库、WebSocket 协同、服务端渲染。

### 部署方式
本地构建 → commit + push 到 master → SSH 上服务器 pull
- 运行 `./deploy.ps1`（Win）或 `./deploy.sh`（Linux）
- 构建产物落在 `public/` 目录，直接提交 git，nginx `alias /var/www/SRD/public/;` serve
- 需要 SSH 密钥（`deploy.ps1` 默认读 `~/.ssh/ssh-key-2026-03-20.key`，可在脚本中修改路径）

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
