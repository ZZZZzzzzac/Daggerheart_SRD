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
├── scripts/             # 构建、导入、校验与服务端运行脚本
│   ├── build_srd.py
│   ├── sync_para.py     # 与 ParaTranz 的双向文本同步
│   ├── proxy_server.py  # GitHub API 代理（零依赖，纯 stdlib）
│   └── proxy_server.service  # systemd 单元文件模板
├── data/                # 唯一章节清单 + 专用规则术语表 + para-sync 状态
├── layouts/             # Hugo 模板
├── static/              # 阅读端、编辑器、反馈后台、图片
├── tests/               # Python、Node.js 与浏览器测试
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
- 监听 `127.0.0.1:5002`，由 nginx `proxy_pass` 暴露为 `/SRD/api/`
- 端点：`GET /api/page-list`、`GET /api/get-file`、`POST /api/save`
- `/api/save` 只接受现有 `src/pages/` 页面，并执行冲突检查与候选构建
- `/api/feedback` 接收公开文字反馈，`/api/admin/feedback` 管理 SQLite 收件箱
- 安全检查：只允许编辑 `src/pages/` 路径下的文件
- Git 备份：每次成功发布都自动 commit，并用服务器上已经配置好的非交互式 Git 凭据后台 push

### 服务端配置

**systemd**：`/etc/systemd/system/srd-production.service`
```
User=srd
WorkingDirectory=/srv/srd-production
ExecStart=/srv/bandwagon-preview/venv/bin/python /srv/srd-production/scripts/proxy_server.py
```

**nginx**：使用 `scripts/nginx_proxy_snippet.conf`。公开反馈接口不要求登录；编辑器、反馈后台、发布接口和管理接口统一使用公用密码。

不计划做：
- 实时协同编辑
- 服务端搜索（当前使用无第三方依赖的浏览器端索引）

## 服务器

生产站运行在搬瓦工 `192.243.116.94` 的 `/srv/srd-production`，服务用户 `srd`，systemd 单元 `srd-production.service`。Nginx 提供 `public/` 静态文件并反代回环端口 5002。连接与现役配置以同级 `Daggerheart_VPS/servers/bandwagon-192.243.116.94/AGENTS.md` 为准；旧 Oracle 入口已退役。

代码发布：先推送 GitHub，再以 `srd` 用户拉取并在候选目录完整构建。确认生产目录没有新编辑后快进代码，替换构建产物并重启 `srd-production.service`，验证两个域名的阅读页和受保护接口。保留上一版站点以便恢复；`var/feedback.db`、运行配置及凭据不随代码覆盖。无需修改 Nginx 配置。

## 大版本内容导入

日常构建只读取本仓库中的 `src/pages/`，不依赖外部仓库。导入新的完整 SRD 版本时使用以下外部资料：

```
../DaggerHeart_CN/projects/Daggerheart-Core-Rulebook/
├── paratranz/DH-SRD-1.0-June-26-2025.md.json   # 翻译数据（build.sh 引用）
└── data/
    ├── adversaries.json                          # 敌人数据
    └── environments.json                         # 环境数据
```

预期 `DaggerHeart_CN` 与本仓库同级目录。脚本中的路径均为相对路径。

## ParaTranz 双向同步

`scripts/sync_para.py` 维护本站与 ParaTranz 项目 14448（`SRD/DH_SRD_2_2026_08_25.md.json` = 3347716、
`SRD/DH_SRD_2_Equipment_Items.json` = 3409913）的文本一致性，两边互为主源。

判定用**基线**（`data/para-sync/baseline.json`，句子归一化后的哈希）做三方合并，不看 ParaTranz 的
`updatedAt`——整包导入会把它刷成最新，2026-10-30 就是因此把人工修订冲回了站点的旧文本。

- 只有一边偏离基线 → 那边是改动方，同步到另一边
- 两边都偏离基线 → 冲突，写进 `data/para-sync/conflicts.md`。这份文件是**当前未解决冲突的快照**，
  裁决完下次 `check` 会自动把它去掉，所以「文件非空」就等于「还有待裁决的冲突」
- 只存在于一边的句子（本站表格化内容、「站点补充：非SRD2.0条目」的敌人、ParaTranz 独有段落）只计数不写

```bash
python scripts/sync_para.py check              # 只读；0=干净，1=有冲突或待同步
python scripts/sync_para.py check --json       # 结构化结果输出到 stdout
python scripts/sync_para.py apply --to-site    # ParaTranz 的改动写进本站（改 md 并 commit）
python scripts/sync_para.py apply --to-para    # 本站的改动写回 ParaTranz（PUT /strings，保 stage）
python scripts/sync_para.py snapshot           # 人工裁决后重建基线
```

安全阀：相似度 ≥ 0.90、骰子与数值必须完全一致、最优与次优匹配差距 ≥ 0.03（否则视为歧义不配对）、
单句自动替换 ≤ 24 字符。写回后回读校验归一化文本必须一致。

定时巡查分两处：

- **有 token 的机器**（本地）定时跑 `check`，把 `data/para-sync/` 一起提交推送。
- **服务器上的巡查只读文件**：`data/para-sync/conflicts.md` 里「未解决冲突」不为 0 即有未裁决项，
  `data/para-sync/latest.json` 的 `generatedAt` 用来判断这份检查有多旧。不需要 token，不需要联网。

`check` 幂等。token 依次取环境变量 `PARATRANZ_TOKEN`、本仓库 `.env`、同级 `DaggerHeart_CN/.env`。

## 授权

© 2025 Critical Role LLC. Darrington Press 社群游戏授权条款，Public Game Content。

## Agent skills

### Issue tracker

GitHub Issues（`ZZZZzzzzac/Daggerheart_SRD`）。见 `docs/agents/issue-tracker.md`。

### Triage labels

全部使用默认标签名。见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文（根目录 `CONTEXT.md` + `docs/adr/`）。见 `docs/agents/domain.md`。
