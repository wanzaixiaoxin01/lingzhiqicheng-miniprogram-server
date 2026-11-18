# 兴趣活动后台管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让兴趣活动由服务端初始化和管理，支持管理员 CRUD、显示隐藏与小程序动态展示。

**Architecture:** 复用 `Course` 与现有通用后台资源路由，增加课程封面存储和删除保护；公共接口把封面转换为绝对地址。小程序删除本地六项活动兜底，仅保留接口数据的轻量规范化。

**Tech Stack:** FastAPI、SQLAlchemy、Jinja2/Tabler、微信小程序原生 JavaScript、Python unittest、Node test。

---

### Task 1: 初始化六项兴趣活动

**Files:**
- Modify: `app/seed.py`
- Create: `app/static/courses/*.jpg`
- Test: `tests/test_interest_activity_seed.py`

- [ ] 写失败测试，断言初始化目录包含六项稳定 ID、当前文案、顺序和 `published` 状态。
- [ ] 运行 `python -m unittest tests.test_interest_activity_seed -v`，确认旧 seed 不满足测试。
- [ ] 实现幂等 upsert，并隐藏旧的“智习室/晚托”数据。
- [ ] 复制六张当前封面到服务端静态目录。
- [ ] 再次运行测试并确认通过。

### Task 2: 管理员权限与活动 CRUD

**Files:**
- Modify: `app/domain/staff_access.py`
- Modify: `app/templates/_nav.html`
- Modify: `app/templates/resource_list.html`
- Modify: `app/templates/resource_form.html`
- Modify: `app/routes/admin_pages.py`
- Test: `tests/test_interest_activity_admin.py`

- [ ] 写失败测试，断言仅管理员拥有 `courses` 权限，菜单存在“兴趣活动”，状态使用“显示/隐藏”。
- [ ] 运行目标测试确认失败。
- [ ] 开放管理员资源权限并复用通用列表、分页、查询、新增和编辑路由。
- [ ] 增加单项显示/隐藏操作及已关联活动删除保护。
- [ ] 运行目标测试确认通过。

### Task 3: 封面上传和公开接口

**Files:**
- Create: `app/domain/course_images.py`
- Create: `app/services/course_image_storage.py`
- Modify: `app/main.py`
- Modify: `app/routes/admin_pages.py`
- Modify: `app/routes/public_api.py`
- Test: `tests/test_interest_activity_images.py`
- Test: `tests/test_interest_activity_api.py`

- [ ] 写失败测试，覆盖 JPG/PNG/WEBP、10 MB 限制、随机存储名和绝对封面 URL。
- [ ] 运行目标测试确认失败。
- [ ] 实现 `/uploads/courses` 存储、表单上传/替换/清理和接口 URL 转换。
- [ ] 运行目标测试确认通过。

### Task 4: 小程序仅使用接口活动

**Files:**
- Modify: `utils/course-catalog.js`
- Modify: `pages/courses/index.js`
- Modify: `pages/courses/index.wxml`
- Modify: `tests/courses-page.test.js`

- [ ] 先修改测试，断言不存在本地六项兜底，远端空数组保持为空，`cover_url` 映射为卡片图片。
- [ ] 运行 `node --test tests/courses-page.test.js` 确认失败。
- [ ] 删除本地活动常量和合并逻辑，增加加载失败状态与重新加载入口。
- [ ] 运行目标测试确认通过。

### Task 5: 数据初始化与全量验证

**Files:**
- Modify: local development database through `python -m app.seed`

- [ ] 运行 API 全部 Python 测试。
- [ ] 运行小程序全部 Node 测试。
- [ ] 对两个仓库执行 `git diff --check`。
- [ ] 运行 seed，验证本地 4000 接口只返回六项显示活动及可访问封面。
- [ ] 提交并推送 API 与小程序改动。
