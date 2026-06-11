## Problem Statement

当前 SRD 内容更新流程过于繁琐：贡献者通过在线编辑器提交 PR → 维护者 GitHub 审核合并 → 维护者本地 pull、build、commit 构建产物、push → 服务器 git pull。一次简单的内容修改需要经过 4 个手动环节，整个流程可能耗时数小时甚至数天。

维护者希望：信任用户（翻译组成员）编辑后直接看到结果，无需经过审核和手动部署。同时不信任的用户只能读不能改。

## Solution

将部署架构从"本地构建 + git 推送"改为"服务端即时构建"：

- 在线编辑器的保存操作直接从写 GitHub API 改为写服务器本地文件系统，保存后自动触发 Hugo 重建
- 编辑器页面和保存 API 由 nginx `auth_basic` 保护，只有知道密码的信任用户可以编辑
- `public/` 构建产物不再提交 git，由服务器自行生成
- 代码更新（脚本、模板、CSS 等）仍走 git push → 手动 SSH `git pull` 的传统流

## User Stories

1. 作为翻译组成员，我希望在 `/SRD/edit/` 编辑后点击保存，修改能在几秒内出现在网站上，不需要等待维护者审核和部署
2. 作为翻译组成员，我希望进入编辑器时只需输入一次密码，后续编辑多个页面时不必重复认证
3. 作为翻译组成员，我希望编辑器能实时预览 markdown 渲染效果，方便校对
4. 作为翻译组成员，我希望保存操作有明确的成功/失败反馈，失败时能知道原因
5. 作为维护者，我希望信任用户的每次保存自动 git commit + push 到 GitHub，以便追溯修改历史和必要时回滚
6. 作为维护者，我希望普通访客访问 `/SRD/edit/` 时看到的是只读版本或被拒绝访问
7. 作为维护者，我希望代码更新（脚本、模板等）不经过在线编辑器，仍走 git 流，避免信任用户误改基础设施
8. 作为维护者，我希望编辑器只能修改 `src/pages/` 下的 markdown 文件，不能访问系统其他文件
9. 作为维护者，我希望保存 API 在后端做路径安全检查，防止路径遍历攻击
10. 作为维护者，我希望构建失败时（如 markdown 语法错误导致 Hugo 报错），能收到明确的错误信息反馈

## Implementation Decisions

### 架构变更

- **构建位置**：从本地构建迁至服务器构建（服务器需安装 Hugo）
- **内容源**：服务器 `src/pages/` 成为内容真相源，`public/` 由服务器即时生成
- **认证方式**：nginx `auth_basic` 保护编辑页面和保存 API，共享密码方案，不引入应用层认证

### 代理服务器（proxy_server.py）重构

- 移除所有 GitHub API 调用（分支创建、blob 写入、tree 构建、commit 创建、PR 创建）
- 新增三个 REST 端点替代旧的 `/api/submit-pr`：
  - `GET /api/page-list` — 扫描本地 `src/pages/` 返回文件列表（替代旧 GitHub tree API）
  - `GET /api/get-file?path=...` — 读取本地文件内容（替代旧 GitHub contents API）
  - `POST /api/save` — 接收 `{path, content}`，写入文件后调 `build_srd.py` 重建站点
- 路径安全检查：验证 `path` 以 `src/pages/` 开头，使用 `os.path.normpath` 防路径遍历
- 可选 git 备份：`GH_TOKEN` 环境变量为可选，设置后每次保存自动 `git add` + `git commit` + `git push`
- 不再要求 `GH_TOKEN` 环境变量，服务可无条件启动

### 编辑器前端简化

- 移除 GitHub Token 输入、Token 存储（localStorage）、PR 创建弹窗等所有 PR 相关 UI 和逻辑
- 保存按钮直接调用 `POST /api/save`，不再弹窗收集修改说明
- 文件加载从 GitHub API/raw CDN 改为调本地 `GET /api/get-file`

### 部署脚本变更

- `deploy.ps1` / `deploy.sh` 去掉 SSH 到服务器执行 `git pull` + `systemctl restart` 的步骤
- 部署脚本仅做：本地构建验证 + git push 代码到 GitHub
- 服务器端代码更新改为维护者手动 SSH `git pull`

### Git 仓库变更

- `public/` 加入 `.gitignore`，不再提交构建产物
- 需手动执行 `git rm --cached -r public/` 从 git 跟踪中移除（文件不删）

### nginx 配置变更

- 编辑器页面 `/SRD/edit/` 和保存 API `/SRD/api/save` 由 `auth_basic` 保护
- `/api/page-list` 和 `/api/get-file` 保持公开（编辑器加载时需读取）

## Testing Decisions

### 测试原则

- 只测试外部行为（HTTP 状态码、响应格式、文件写入结果），不测试实现细节
- 手动验收为主，项目当前无自动化测试框架

### 验收测试场景

1. **认证测试**：无密码访问 `/SRD/edit/` 返回 401
2. **保存流程测试**：编辑 markdown → 保存 → 确认文件已写入 `src/pages/` → 确认网站已更新
3. **安全测试**：尝试保存路径 `../etc/passwd`，确认被拒绝
4. **构建失败测试**：保存有语法错误的 markdown，确认返回错误信息
5. **语言切换测试**：编辑器在中/英文文件间切换，确认内容正确加载

## Out of Scope

- 每人独立密码（当前共享密码方案）
- 应用内用户管理或角色权限系统
- 编辑器的实时协同编辑功能
- 内容审核工作流（信任用户直接发布，不审核）
- 服务端全文搜索（已有计划用客户端搜索）
- 移动端编辑器适配（编辑器已有基本的响应式布局）

## Further Notes

### 服务器迁移步骤（首次部署）

1. SSH 到服务器，安装 Hugo（单二进制，~50MB）
2. 配置 nginx `auth_basic`（编辑页面 + `/api/save` 端点）
3. 创建密码文件：`htpasswd -c /etc/nginx/.htpasswd_daggerheart editor`
4. 手动运行一次 `python3 scripts/build_srd.py` 生成初始 `public/`
5. 更新 systemd unit（`GH_TOKEN` 改为可选——不设也能跑）
6. 本地 `git rm --cached -r public/` 后再 `./deploy.ps1` 推送新代码
7. 服务器 `git pull` 获取新代码，`systemctl restart proxy_server`

### 回滚方案

如果出问题，可以通过 git 回滚服务器代码（手动 SSH `git checkout` 旧版本），恢复旧的 PR 审核流程。内容文件（`src/pages/`）的修改历史也在 git 中保留了。
