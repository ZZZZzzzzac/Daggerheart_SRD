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
├── data/
│   ├── srd.yaml         # 唯一章节清单
│   └── glossary.yaml    # 专用规则术语表（默认关闭）
├── layouts/             # Hugo 模板
├── static/              # 阅读端、编辑器和反馈后台资源
├── content/             # （生成）Python 生成的 Hugo 页面，已 gitignore
├── public/              # （生成）Hugo 最终输出，已 gitignore
├── config.yaml          # Hugo 配置
├── build.ps1            # Windows 构建
├── build.sh             # Linux 构建
├── deploy.ps1           # Windows 构建 + 推送代码到 GitHub
└── deploy.sh            # Linux 构建 + 推送代码到 GitHub
```

## 构建

### 前置依赖

- Python 3 + `pyyaml` `markdown`
- [Hugo](https://gohugo.io/)（非 extended 版即可）

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

### 构建命令

```bash
python scripts/build_srd.py    # md → Hugo content → 静态页
# 或一键脚本
./build.ps1   # Windows（仅构建）
./build.sh    # Linux（仅构建）
```

输出在 `public/` 目录。

### 本地预览

```bash
python scripts/preview_server.py
```

打开 `http://127.0.0.1:8765/SRD/`。同一条命令同时启动阅读站、编辑接口和反馈收件箱。终端会显示本次随机生成的管理密码；编辑器、反馈后台和管理接口统一使用账号 `admin` 登录。需要固定测试密码时可运行 `python scripts/preview_server.py --admin-password 你的密码`。正式服务器仍由 nginx 配置公用密码。

### 部署

```bash
./deploy.ps1   # Windows（构建 + 推送代码到 GitHub）
./deploy.sh    # Linux（构建 + 推送代码到 GitHub）
```

服务器端自行构建 `public/`，代码更新需手动 SSH 到服务器 `git pull`。

## 在线编辑器

`/SRD/edit/` 提供在线编辑功能：
- 左侧编辑 Markdown，右侧使用与正式构建相同的规则预览
- 保存时检查页面版本，防止覆盖其他管理员的修改
- 候选内容在临时项目中完整构建；成功后才替换正式正文和站点
- 每次成功发布先创建本地 Git 版本，再异步推送 GitHub
- 编辑器页面有密码保护（nginx auth_basic），信任用户可编辑

## 反馈收件箱

读者可从正文提交站内反馈。反馈保存在服务器的 SQLite 数据库中；管理员通过 `/SRD/admin/` 查看、备注并更新处理状态。管理路径和管理 API 必须使用 nginx 公用密码保护，配置示例见 `scripts/nginx_proxy_snippet.conf`。

## 测试

```bash
python -m pytest -q
node --test tests/search_core.test.js
```

Python 测试覆盖构建、页面发布、版本冲突和反馈收件箱；Node 测试覆盖本地搜索的排序与语言筛选。

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
