# SRD 站点收尾交接

更新时间：2026-09-03

## 当前状态

- GitHub issue #10《PRD：SRD 站点完整翻新》的主体功能已经上线。
- 本轮工程收尾已部署生产，发布提交为 `cbfbaa9`；生产技术验收已经通过。
- 生产站点：<https://daggerheart.cn/SRD/>。
- 当前正文版本已正式标记为 `srd-1.0`，来源文件标题为 System Reference Document 1.0。

## 本轮已完成

### 稳定锚点

- 正式双语正文中的现有标题都已写入显式 `{#anchor}`，标题文字变化不再改变链接。
- 重复显式锚点会导致构建失败，不再静默追加后缀。
- 同一位置的中英文显式锚点不一致也会导致构建失败。
- `scripts/pin_heading_anchors.py` 可在导入新大版本后固定首次生成的锚点。
- 已增加标题改名、重复锚点和中英文不一致的回归测试。

### 孤儿正文

- `adversaries-and-environments` 父目录下的中英文文件是拆分前的完整合并稿，与四个正式子页内容重叠。
- 两份合并稿已移至 `archive/legacy-pages/adversaries-and-environments/`，不会发布，但可从文件和 Git 历史恢复。
- 构建现在会拒绝 `src/pages/` 中未被 `data/srd.yaml` 引用的 Markdown，避免再次无声遗漏。

### 反馈数据库备份

- 新增 `scripts/backup_feedback.py`，使用 SQLite 在线备份 API 生成一致快照并执行 `PRAGMA quick_check`。
- 新增 `scripts/feedback-backup.service` 与 `scripts/feedback-backup.timer`：每天 UTC 03:20 运行，默认保留 30 天。
- 默认备份位置为 `/var/backups/daggerheart-srd/`，脚本拒绝把备份放入项目/Web 根目录。
- 安装、检查和恢复步骤见 `docs/feedback-backups.md`。
- systemd 模板已安装到生产服务器并启用，首次备份于 2026-09-03 成功生成。

### 版本与归档

- `data/srd.yaml` 已从 `current` 改为 `srd-1.0`；构建会拒绝空值和 `current`。
- 构建产物和新反馈会携带该真实版本；无法读取索引时记录 `unknown`，不再伪装成 `current`。
- 大版本 tag、GitHub Release、恢复验证流程见 `docs/releases.md`。
- `srd-v1.0` tag 在生产验收记录提交后创建，指向实际部署并验收的版本。

### 自动化测试

- `npm test` 已修正并会同时运行渲染核心与搜索测试。
- 新增 Playwright 真实 Chrome 测试，覆盖目录展开与当前小节高亮、搜索结果跳转、语言切换、主题切换和移动端抽屉。
- 浏览器测试发现并修复了“搜索结果跳到当前页锚点时对话框不关闭”的实际问题。
- 新增真实候选发布集成测试，覆盖正文编辑、完整构建、原子站点切换、搜索索引更新和反馈锚点可解析。
- 新增恶意反馈文本只通过 `textContent` 渲染的安全回归测试。

## 生产部署与验收结果

- 生产仓库已快进到 `cbfbaa9`，服务器构建成功，Git 工作区干净。
- `proxy_server.service` 与 Nginx 均为 active，`nginx -t` 通过。
- `feedback-backup.timer` 已启用；首次任务 `Result=success`、`ExecMainStatus=0`，生成了完整快照。
- 公网索引版本为 `srd-1.0`，共 17 个双语页面。
- 真实 Chrome 公网验收确认装备表 Markdown 加粗正确、同类表格列宽一致，新 CSS/JS 版本已生效。
- 公网页面返回 200，未授权管理接口返回 401，未知 API 返回 404。

## 后续非阻塞事项

### 等待维护者提供的资料

- 专用规则术语表：`data/glossary.yaml` 仍保持关闭，不阻塞当前站点运行。
- 新版完整 SRD 与章节目录：资料到齐后使用整体导入流程，不要为了缩短当前长页面临时重分章节。
- 定期按 `docs/feedback-backups.md` 做人工恢复演练，持续验证备份可恢复性。

## 被后续要求覆盖的 PRD 条目

PRD 原要求手机宽表格横向滚动；后续需求明确改为“不滚动，自动换行”，当前实现以最新需求为准。

## 当前本地验证基线

- `python -m pytest -p no:cacheprovider`：74 项通过。
- `npm test`：9 项通过，包含渲染核心与搜索测试。
- `npm run test:e2e`：4 项真实 Chrome 测试通过。
- `python scripts/build_srd.py`：17 个双语页面构建成功。
- `git diff --check`：通过。
