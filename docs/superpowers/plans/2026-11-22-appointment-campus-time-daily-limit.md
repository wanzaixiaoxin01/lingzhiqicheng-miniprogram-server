# Appointment Campus, Time, and Daily Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require a valid WeChat parent, campus, and future appointment time for every appointment, cap each WeChat parent at 10 submissions per Beijing day, and expose campus filtering in Admin.

**Architecture:** Store campus and appointment time as first-class `leads` columns. Serialize submissions per parent with a database row lock, then count persisted leads inside Beijing-day UTC boundaries before inserting. Reuse the published-campus API for the mini-program selector and the existing Admin list query for campus filtering.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL/SQLite tests, Jinja2, native WeChat Mini Program JavaScript/WXML, Python unittest, Node test runner.

---

### Task 1: Appointment persistence and validation

**Files:**
- Modify: `app/models.py`
- Modify: `app/domain/leads.py`
- Modify: `app/repositories.py`
- Modify: `app/schemas.py`
- Test: `tests/test_appointment_constraints.py`
- Test: `tests/test_lead_validation.py`

- [ ] Write failing tests asserting `campus_id` and `appointment_at` are required, `appointment_at` is timezone-aware and in the future, and the database columns are non-null.
- [ ] Run `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p 'test_appointment_constraints.py'` and verify failures describe missing fields/columns.
- [ ] Add `appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)`, make `campus_id` non-null, parse ISO appointment time in `validate_lead_input`, and persist/serialize both fields.
- [ ] Re-run the focused tests and verify they pass.

### Task 2: Authenticated daily quota

**Files:**
- Modify: `app/repositories.py`
- Modify: `app/routes/public_api.py`
- Test: `tests/test_parent_api.py`

- [ ] Write failing tests showing anonymous submissions return 401, the first 10 authenticated submissions succeed, the 11th returns 429, and another parent still succeeds.
- [ ] Run `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p 'test_parent_api.py'` and verify the new tests fail for the missing quota.
- [ ] Add a repository function that locks the parent row with `SELECT ... FOR UPDATE`, counts `Lead.user_id` within Beijing-day UTC boundaries, and raises a domain exception at 10. Require the parent session in the route and translate the exception to HTTP 429 with `每天最多提交10条预约，请明天再试`.
- [ ] Re-run the focused tests and verify they pass.

### Task 3: Campus validity and Admin filtering

**Files:**
- Modify: `app/routes/public_api.py`
- Modify: `app/repositories.py`
- Modify: `app/routes/admin_pages.py`
- Modify: `app/templates/resource_list.html`
- Modify: `app/templates/dashboard.html`
- Test: `tests/test_parent_api.py`
- Test: `tests/test_lead_admin.py`

- [ ] Write failing tests for rejecting missing/hidden campuses and for filtering Admin leads by `campus_id`.
- [ ] Run the two focused test modules and verify the expected failures.
- [ ] Validate the campus through `get_published_campus`, add `campus_id` to `list_admin_leads`, pass campus choices through the Admin route, add the filter select, and render campus name plus appointment time in both Admin views.
- [ ] Re-run focused tests and verify they pass.

### Task 4: Mini-program campus and datetime selectors

**Files:**
- Modify: `../../apps/miniprogram/pages/appointment/index.js`
- Modify: `../../apps/miniprogram/pages/appointment/index.wxml`
- Modify: `../../apps/miniprogram/pages/appointment/index.wxss`
- Test: `../../apps/miniprogram/tests/appointment-page.test.js`
- Test: `../../apps/miniprogram/tests/appointment-behavior.test.js`

- [ ] Write failing tests for loading published campuses, requiring campus/date/time, combining the values as `YYYY-MM-DDTHH:mm:00+08:00`, and displaying campus and appointment time in history.
- [ ] Run `node --test ../../apps/miniprogram/tests/appointment-page.test.js ../../apps/miniprogram/tests/appointment-behavior.test.js` and verify failures.
- [ ] Load campuses with `getCampuses`, add native campus/date/time pickers, preserve query preselection, validate future time, submit `appointment_at`, and render the returned campus/time in history.
- [ ] Re-run the focused JavaScript tests and verify they pass.

### Task 5: Full verification and deployment

**Files:**
- Modify: deployment copy under `/opt/lingzhi-qicheng/services/api`
- Database: Tencent Cloud PostgreSQL `lingzhi_qicheng`

- [ ] Run `PYTHONPATH=services/api services/api/.venv/bin/python -m unittest discover -s services/api/tests` and verify zero failures.
- [ ] Run `node --test apps/miniprogram/tests/*.test.js services/api/tests/*.test.js` and verify zero failures.
- [ ] Back up PostgreSQL, API code, and uploads; sync changed API files; rebuild the not-yet-live schema and restart `lingzhi-api`.
- [ ] Verify production/test HTTPS health, required database columns, 10 successful submissions and an HTTP 429 on the 11th, Admin campus filtering, and cleanup of verification records.
