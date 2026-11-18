# 生产环境部署

官网与小程序服务分开部署：

- `www.lingzhiqicheng.com`：官网，百度云
- `admin.lingzhiqicheng.com`：运营后台，腾讯云
- `api.lingzhiqicheng.com`：小程序正式 API，腾讯云
- `api-test.lingzhiqicheng.com`：小程序体验版 API，腾讯云

腾讯云使用 Docker Compose 运行 FastAPI、PostgreSQL 和 Caddy。Caddy 按域名隔离后台与公开 API，并自动申请、续期 HTTPS 证书。

## 服务器路径

- 项目：`/opt/lingzhi-qicheng`
- API：`/opt/lingzhi-qicheng/services/api`
- Compose：`/opt/lingzhi-qicheng/infra/docker-compose.yml`
- Caddy：`/opt/lingzhi-qicheng/infra/caddy/Caddyfile`
- 环境变量：`/opt/lingzhi-qicheng/services/api/.env`
- PostgreSQL：Docker 卷 `infra_postgres-data`
- 上传文件：Docker 卷 `infra_api-uploads`

## 日常发布

1. 备份 PostgreSQL 和上传文件卷。
2. 同步 API 代码到 `services/api`。
3. 在 `infra` 目录执行 `docker compose up -d --force-recreate api`。
4. 检查 `docker compose ps`、API `/health` 和 Caddy 日志。
5. 执行 `docker compose exec api python -m app.seed`，补齐内置兴趣活动并保留后台已有修改。

## 微信小程序域名

微信公众平台需要配置：

- request 合法域名：`https://api.lingzhiqicheng.com`、`https://api-test.lingzhiqicheng.com`
- downloadFile 合法域名：`https://api.lingzhiqicheng.com`、`https://api-test.lingzhiqicheng.com`

## 备份

必须同时备份 PostgreSQL 和 `infra_api-uploads` 卷。只备份数据库无法恢复学习资料与网点图片。
