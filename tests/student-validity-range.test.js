import test from "node:test";
import assert from "node:assert/strict";

import { presetEndDate } from "../app/static/student-validity-range.js";

function iso(date) {
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

test("validity presets include both the start and end day", () => {
  const start = new Date(2026, 10, 24);
  assert.equal(iso(presetEndDate(start, { days: 7 })), "2026-11-30");
  assert.equal(iso(presetEndDate(start, { months: 1 })), "2026-12-23");
  assert.equal(iso(presetEndDate(start, { months: 3 })), "2027-02-23");
  assert.equal(iso(presetEndDate(start, { months: 6 })), "2027-05-23");
  assert.equal(iso(presetEndDate(start, { months: 12 })), "2027-11-23");
});

test("month presets clamp dates at month boundaries", () => {
  assert.equal(iso(presetEndDate(new Date(2028, 1, 29), { months: 12 })), "2029-02-27");
  assert.equal(iso(presetEndDate(new Date(2026, 0, 31), { months: 1 })), "2026-02-27");
});
