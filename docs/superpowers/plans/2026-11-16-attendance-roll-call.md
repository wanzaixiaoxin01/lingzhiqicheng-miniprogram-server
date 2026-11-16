# Student Attendance Roll Call Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace manual attendance entry with a campus/date roster where teachers toggle morning and afternoon attendance inside each student's card.

**Architecture:** Keep one `AttendanceRecord` per student, campus, date, and service type, adding morning/afternoon booleans. Build a roster query from active enrollments, expose an idempotent check-in endpoint, render ten student cards per page, and return the two attendance flags to parents.

**Tech Stack:** FastAPI, SQLAlchemy 2, Jinja2, vanilla JavaScript, SQLite/PostgreSQL compatibility SQL, Python unittest.

---

### Task 1: Attendance period persistence and compatibility migration

**Files:**
- Modify: `app/models.py`
- Modify: `app/db.py`
- Test: `tests/test_attendance_roll_call.py`

- [ ] Add a failing model test that creates one record with `morning_present=True`, reloads it, and asserts morning is true and afternoon is false.
- [ ] Add a migration test against a legacy `attendance_records` table and assert existing rows become morning and afternoon present.
- [ ] Add non-null boolean columns to `AttendanceRecord` with Python and server defaults of false.
- [ ] Extend `_ensure_schema_compatibility()` so missing attendance columns are added and existing rows are updated to true exactly once.
- [ ] Run `../../.venv/bin/python -m unittest tests.test_attendance_roll_call` and confirm the persistence and migration tests pass.

### Task 2: Build the scoped roll-call roster

**Files:**
- Modify: `app/repositories.py`
- Modify: `app/routes/operations_admin.py`
- Test: `tests/test_attendance_roll_call.py`

- [ ] Add failing tests for campus scoping, keyword matching, attendance state merging, total counts, and ten-item pagination.
- [ ] Add a focused roster result type containing enrollment, student, optional attendance record, and aggregate counts.
- [ ] Query active students through active enrollments for one permitted campus, de-duplicate students, and merge records for the selected date.
- [ ] Update `GET /admin/visits` to select a permitted campus, default to today, and render roster cards rather than existing attendance rows.
- [ ] Run the roster tests and confirm unauthorized campuses return 403 while valid filters return the expected students and counts.

### Task 3: Add idempotent morning and afternoon check-in

**Files:**
- Modify: `app/routes/operations_admin.py`
- Test: `tests/test_attendance_roll_call.py`

- [ ] Add failing request tests for morning check-in, afternoon check-in, half-day attendance, revocation, deletion when both flags are false, invalid period, and unauthorized campus/student combinations.
- [ ] Add `POST /admin/visits/check-in` accepting `student_id`, `campus_id`, `attendance_date`, `period`, and explicit `present`.
- [ ] Revalidate campus permission and active enrollment on every request, then create or update the daily record.
- [ ] Return the saved morning/afternoon values, the card summary label, and refreshed campus totals as JSON.
- [ ] Run the endpoint tests and confirm repeated identical requests are idempotent.

### Task 4: Implement the approved student-card roll-call UI

**Files:**
- Create: `app/templates/attendance_roll_call.html`
- Create: `app/static/attendance-roll-call.js`
- Modify: `app/static/admin.css`
- Modify: `app/routes/operations_admin.py`
- Test: `tests/attendance-roll-call.test.js`
- Test: `tests/test_attendance_roll_call.py`

- [ ] Add a failing template response test asserting the page contains student cards, guardian details, two period controls, filters, statistics, and no “新增” button.
- [ ] Add failing JavaScript tests for success state changes, aggregate updates, repeated-click prevention, and rollback after a failed request.
- [ ] Implement the approved four-column desktop card grid with responsive columns, ten students per page, status chips, and morning/afternoon buttons.
- [ ] Implement fetch-based explicit check-in requests, loading states, success updates, error rollback, and toast feedback.
- [ ] Run Python and JavaScript tests, then visually compare a local screenshot with `docs/prototypes/attendance-roll-call-grid-prototype.png`.

### Task 5: Expose attendance periods to parents

**Files:**
- Modify: `app/domain/parent_dashboard.py`
- Modify: `app/schemas.py`
- Test: `tests/test_parent_dashboard.py`
- Test: `tests/test_parent_api.py`

- [ ] Add failing tests that expect `morning_present`, `afternoon_present`, and `attendance_period_label` for full-day and half-day records.
- [ ] Add the two booleans and derived label to the parent dashboard payload and response schema.
- [ ] Keep `attendance_count` as the number of attended days rather than the number of attended periods.
- [ ] Run parent dashboard and API tests and confirm existing response fields remain unchanged.

### Task 6: Full verification and documentation sync

**Files:**
- Modify: `docs/superpowers/specs/2026-11-16-attendance-roll-call-design.md`
- Verify: all changed files

- [ ] Run `../../.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` and confirm the full suite passes.
- [ ] Run the JavaScript test files and confirm they pass.
- [ ] Run `git diff --check` and inspect the final diff for unrelated changes.
- [ ] Restart the local API, perform morning and afternoon check-in through the real page, refresh, and confirm persistence.
- [ ] Verify the parent dashboard API returns the correct period label for the checked-in student.
