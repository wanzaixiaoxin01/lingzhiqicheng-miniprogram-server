# 学生报名管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** 将后台学生管理改为每个学生一行的报名管理，并支持同一学生多条不重叠报名记录、按日期点名和家长端报名优先级展示。

**Architecture:** 保留 `Student` 学生档案和 `StudentEnrollment` 报名记录两层模型。后台学生列表只查询档案，学生详情负责报名历史和新增/编辑报名；日期判断集中在服务端 repository/domain 层，点名和家长端复用同一套有效区间规则。

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2, PostgreSQL/SQLite tests, WeChat Mini Program WXML/WXSS, Node `node:test`.

---

### Task 1: 报名日期规则与查询函数

**Files:**
- Modify: `services/api/app/repositories.py`
- Modify: `services/api/app/domain/parent_dashboard.py`
- Test: `services/api/tests/test_student_validity.py`
- Test: `services/api/tests/test_attendance_roll_call.py`
- Test: `services/api/tests/test_parent_dashboard.py`

- [ ] **Step 1: Write failing tests** for closed-interval overlap rejection, current-date enrollment filtering, and parent enrollment priority current -> future -> expired while preserving attendance history.
- [ ] **Step 2: Run focused tests and confirm they fail for missing behavior.**
- [ ] **Step 3: Implement shared date predicates and repository filtering.** Treat `started_on`/`ended_on` null legacy rows as non-matchable for date filtering; preserve them in history output.
- [ ] **Step 4: Implement parent selection ordering and sort attendance by date then creation time descending.**
- [ ] **Step 5: Run focused tests and confirm they pass.**

### Task 2: Server-side enrollment overlap validation

**Files:**
- Modify: `services/api/app/routes/operations_admin.py`
- Modify: `services/api/app/repositories.py`
- Test: `services/api/tests/test_student_validity.py`

- [ ] **Step 1: Write failing tests** for adding a non-overlapping renewal, rejecting boundary overlap, and editing an existing record without self-conflict.
- [ ] **Step 2: Run the focused test file and confirm the new tests fail.**
- [ ] **Step 3: Add a single validation function that excludes an optional enrollment id and raises a clear HTTP 400 message for overlap.**
- [ ] **Step 4: Call it from enrollment create and update paths, leaving student profile creation responsible only for creating the initial record.**
- [ ] **Step 5: Run all server tests.**

### Task 3: Admin student enrollment management UI

**Files:**
- Modify: `services/api/app/routes/operations_admin.py`
- Modify: `services/api/app/templates/operations_list.html`
- Modify: `services/api/app/templates/operations_form.html`
- Modify: `services/api/app/templates/attendance_roll_call.html`
- Modify: `services/api/app/templates/_nav.html`
- Modify: `services/api/app/static/admin.css`
- Test: `services/api/tests/test_student_validity.py`
- Test: `services/api/tests/test_admin_list_pagination.py`

- [ ] **Step 1: Write failing template/route tests** for “学生报名管理”, one-row student listing, detail enrollment history, and “新增报名记录”.
- [ ] **Step 2: Run focused tests and confirm failure.**
- [ ] **Step 3: Rename navigation/list labels while keeping `/admin/students` compatibility.**
- [ ] **Step 4: Add student detail route and enrollment create/edit routes using the existing date-range picker.**
- [ ] **Step 5: Render all enrollment records sorted by start date descending with calculated status labels.**
- [ ] **Step 6: Update point-in-time roster presentation and run server tests.**

### Task 4: Mini-program parent enrollment display

**Files:**
- Modify: `apps/miniprogram/pages/profile/index.wxml`
- Modify: `apps/miniprogram/pages/profile/index.js` only if API output shape requires selection metadata
- Modify: `apps/miniprogram/pages/profile/index.wxss` only if selected-state styling needs adjustment
- Test: `apps/miniprogram/tests/profile-page.test.js`

- [ ] **Step 1: Write failing page tests** asserting current/future/expired enrollment selection is represented by the active enrollment fields and historical attendance remains rendered.
- [ ] **Step 2: Run the focused test and confirm failure.**
- [ ] **Step 3: Render the server-selected enrollment’s start/end dates and keep attendance history unchanged.**
- [ ] **Step 4: Run all mini-program Node tests.**

### Task 5: Final verification, commits, and deployment

**Files:**
- Modify only files listed above.

- [ ] **Step 1: Run service tests, mini-program tests, and `git diff --check`.**
- [ ] **Step 2: Commit and push the server/Admin repository.**
- [ ] **Step 3: Commit and push the mini-program repository.**
- [ ] **Step 4: Back up server code, PostgreSQL, and uploads.**
- [ ] **Step 5: Sync only `services/api/app`, recreate the API container, and verify `/health`, logs, and deployed templates/static files.**
- [ ] **Step 6: Report commits, test counts, backup path, and deployment result.**
