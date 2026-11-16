import test from "node:test";
import assert from "node:assert/strict";

import {
  attendanceSummary,
  attendanceRate,
  periodButtonText,
  updateAttendanceCard
} from "../app/static/attendance-roll-call.js";

test("attendance rate formats one decimal place", () => {
  assert.equal(attendanceRate(1, 3), "33.3%");
  assert.equal(attendanceRate(0, 0), "0.0%");
});

test("attendance summary distinguishes full day and half day", () => {
  assert.deepEqual(attendanceSummary(true, true), ["全天已到", "is-full"]);
  assert.deepEqual(attendanceSummary(true, false), ["上午已到", "is-half"]);
  assert.deepEqual(attendanceSummary(false, true), ["下午已到", "is-half"]);
  assert.deepEqual(attendanceSummary(false, false), ["今日未到", "is-none"]);
});

test("period button text reflects saved state", () => {
  assert.equal(periodButtonText("morning", false), "上午签到");
  assert.equal(periodButtonText("morning", true), "上午已签");
  assert.equal(periodButtonText("afternoon", false), "下午签到");
  assert.equal(periodButtonText("afternoon", true), "下午已签");
});

test("card update changes both buttons and summary", () => {
  const summary = { textContent: "", className: "" };
  const buttonParts = {
    morning: {
      dataset: { period: "morning", present: "false" },
      classList: { toggle(_name, value) { this.present = value; } },
      querySelector(selector) {
        return selector === "i" ? this.icon : this.label;
      },
      icon: { textContent: "" },
      label: { textContent: "" }
    },
    afternoon: {
      dataset: { period: "afternoon", present: "false" },
      classList: { toggle(_name, value) { this.present = value; } },
      querySelector(selector) {
        return selector === "i" ? this.icon : this.label;
      },
      icon: { textContent: "" },
      label: { textContent: "" }
    }
  };
  const card = {
    querySelector(selector) {
      if (selector === "[data-summary]") return summary;
      const period = selector.includes("morning") ? "morning" : "afternoon";
      return buttonParts[period];
    }
  };

  updateAttendanceCard(card, { morning_present: false, afternoon_present: true });

  assert.equal(summary.textContent, "下午已到");
  assert.equal(summary.className, "student-card-status is-half");
  assert.equal(buttonParts.morning.label.textContent, "上午签到");
  assert.equal(buttonParts.afternoon.label.textContent, "下午已签");
  assert.equal(buttonParts.afternoon.dataset.present, "true");
  assert.equal(buttonParts.afternoon.classList.present, true);
});
