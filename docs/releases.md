# SRD 版本与归档

## 版本命名

`data/srd.yaml` 的 `version` 是对外可见且写入每条反馈的内容版本。格式为 `srd-<上游版本>`；当前正文来自标题注明的 System Reference Document 1.0，因此版本为 `srd-1.0`。

同一上游 SRD 版本内的翻译校订不改变该值，具体修改由反馈时间与 Git 历史定位。整体导入新的上游 SRD 时，必须在同一个变更中更新该值。构建会拒绝空值和 `current` 占位值。

## 大版本归档

大版本首次通过生产验收后，在实际部署的提交上创建同名注释 tag，并推送 tag：

```bash
git tag -a srd-v1.0 -m "Daggerheart SRD 1.0 production archive"
git push origin srd-v1.0
```

随后在 GitHub 以该 tag 创建 Release，至少记录正文来源、发布日期、构建命令和验收结果。tag 必须指向已经部署并验收的提交，而不是导入前或尚未上线的提交。

## 归档验证与恢复

在下一次大版本整体替换前，用独立工作树验证旧 tag 能完整恢复和构建：

```bash
git worktree add ../Daggerheart_SRD-restore-check srd-v1.0
cd ../Daggerheart_SRD-restore-check
npm ci
python -m pip install -r requirements.txt
npm test
python -m pytest -p no:cacheprovider
python scripts/build_srd.py
```

验收旧版首页、章节数、双语切换、搜索和反馈锚点后移除该验证工作树。生产回滚时部署已验证 tag 对应的提交并重新构建；反馈数据库独立按 [`feedback-backups.md`](feedback-backups.md) 恢复。
