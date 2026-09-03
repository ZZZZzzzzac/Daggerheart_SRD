# 反馈数据库备份与恢复

反馈数据库位于 `/var/www/SRD/var/feedback.db`。备份使用 Python `sqlite3.Connection.backup()` 在线备份 API，在服务仍接收写入时也能生成一致快照；快照完成后执行 `PRAGMA quick_check`，通过后才原子改名为正式备份。

## 安装定时备份

生产配置每天 UTC 03:20（北京时间 11:20）运行，保留 30 天。备份写入 `/var/backups/daggerheart-srd/`，位于 `/var/www/SRD` Web 根目录和 Git 仓库之外，文件权限由 `UMask=0077` 限制。

```bash
sudo install -d -o ubuntu -g ubuntu -m 0700 /var/backups/daggerheart-srd
sudo install -m 0644 scripts/feedback-backup.service /etc/systemd/system/
sudo install -m 0644 scripts/feedback-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now feedback-backup.timer
sudo systemctl start feedback-backup.service
sudo systemctl status feedback-backup.service
sudo systemctl list-timers feedback-backup.timer
```

检查最新快照：

```bash
sudo -u ubuntu sqlite3 /var/backups/daggerheart-srd/feedback-YYYYMMDDTHHMMSSZ.sqlite3 'PRAGMA quick_check; SELECT count(*) FROM feedback;'
```

## 恢复

先选择并校验一个快照。恢复期间停止写入服务，再保留当前数据库副本，然后替换数据库并启动服务：

```bash
sudo systemctl stop proxy_server.service
sudo -u ubuntu sqlite3 /var/backups/daggerheart-srd/feedback-YYYYMMDDTHHMMSSZ.sqlite3 'PRAGMA integrity_check;'
sudo -u ubuntu cp -p /var/www/SRD/var/feedback.db /var/backups/daggerheart-srd/feedback-before-restore.sqlite3
sudo -u ubuntu cp /var/backups/daggerheart-srd/feedback-YYYYMMDDTHHMMSSZ.sqlite3 /var/www/SRD/var/feedback.db
sudo -u ubuntu chmod 600 /var/www/SRD/var/feedback.db
sudo systemctl start proxy_server.service
sudo systemctl status proxy_server.service
```

在后台打开 `/SRD/admin/`，核对反馈数量、状态和备注。确认无误前不要删除 `feedback-before-restore.sqlite3`。
