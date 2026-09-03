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
├── data/                # 唯一章节清单 + 专用规则术语表
├── layouts/             # Hugo 模板
├── static/              # 阅读端、编辑器、反馈后台、图片
├── content/             # （生成）Python 生成的 Hugo 页面，已 gitignore
├── public/              # （生成）Hugo 最终输出，nginx 从此目录 serve
├── config.yaml          # Hugo 配置
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
- Python 3 + pyyaml
- Node.js 24 LTS
- Hugo（非 extended 版即可）
- DaggerHeart_CN 仓库在同级目录（外部数据依赖）

### 命令
```
python scripts/build_srd.py   # md → Hugo content → 静态页输出到 public/
./build.ps1                    # Windows 一键
./build.sh                     # Linux 一键
```

### 构建决策（C 方案）
- 内容编辑通过在线编辑器 `/SRD/edit/` 完成，服务器即时构建
- 代码更新（脚本、模板、CSS 等）本地完成后 push 到 GitHub，手动 SSH 到服务器 `git pull`
- `public/` 不再提交 git，服务器自行生成
- `proxy_server.py` 的 `/api/save` 端点保存后自动调 `build_srd.py` → `hugo`

## 协作流程

**内容流程**：信任用户登录 `/SRD/edit/` → 预览 → 完整候选构建 → 原子发布 → 本地 Git commit → 后台 push。

**代码流程**：脚本、模板和样式仍通过 GitHub PR 审核，部署时服务器拉取代码并重新构建。

**贡献者**：
- 初期：翻译组成员（会教 GitHub 网页操作，不要求会 git 命令行）
- 后期：一般网友 fork + PR

**编辑规范**：
- 中文改 `zh.md`，英文改 `en.md`，不要混改
- 大改动先开 issue 讨论
- PR review 由维护者负责

## 在线编辑器

`/SRD/edit/` 提供在线编辑功能：
- 左边编辑 Markdown，右边使用正式构建规则预览
-「保存」→ 版本检查 → 临时完整构建 → 原子替换正式内容与站点
- 成功发布先本地 Git commit，再异步 push；远端失败不阻塞发布
- 编辑器页面和保存 API 由 nginx `auth_basic` 保护，需要密码才能编辑

### 代理服务器

`scripts/proxy_server.py` — 零外部依赖，纯 Python stdlib HTTP 服务器：
- 监听 `127.0.0.1:5000`，由 nginx `proxy_pass` 暴露为 `/SRD/api/`
- 端点：`GET /api/page-list`、`GET /api/get-file`、`POST /api/save`
- `/api/save` 只接受现有 `src/pages/` 页面，并执行冲突检查与候选构建
- `/api/feedback` 接收公开文字反馈，`/api/admin/feedback` 管理 SQLite 收件箱
- 安全检查：只允许编辑 `src/pages/` 路径下的文件
- Git 备份：每次成功发布都自动 commit，并用服务器上已经配置好的非交互式 Git 凭据后台 push

### 服务端配置

**systemd**：`/etc/systemd/system/proxy_server.service`
```
ExecStart=/usr/bin/python3 /var/www/SRD/scripts/proxy_server.py
```

**nginx**：使用 `scripts/nginx_proxy_snippet.conf`。公开反馈接口不要求登录；编辑器、反馈后台、发布接口和管理接口统一使用公用密码。

不计划做：
- 实时协同编辑
- 服务端搜索（当前使用无第三方依赖的浏览器端索引）

## 服务器

**Daggerheart_Tools**（151.145.76.60, VM.Standard.E2.1.Micro, 1C1G）

现状负载：
- 内存 956M，已用 ~19%，可用 616M
- 磁盘 45G，已用 9%
- CPU load 0.00

当前方案（静态页 + 客户端搜索 + 编辑器服务端代理）Micro 绰绰有余。
需要升配的信号：自建后端数据库、WebSocket 协同、服务端渲染。

### 部署方式
内容更新走在线编辑器，代码更新手动部署：
- 运行 `./deploy.ps1`（Win）或 `./deploy.sh`（Linux）推送代码到 GitHub
- SSH 到服务器手动 `git pull` 拉取代码更新
- `public/` 不再提交 git，服务器自行构建

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

## Agent skills

### Issue tracker

GitHub Issues（`ZZZZzzzzac/Daggerheart_SRD`）。见 `docs/agents/issue-tracker.md`。

### Triage labels

全部使用默认标签名。见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文（根目录 `CONTEXT.md` + `docs/adr/`）。当前文件不存在，技能静默跳过。见 `docs/agents/domain.md`。
