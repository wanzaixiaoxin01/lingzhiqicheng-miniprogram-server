export function attendanceSummary(morningPresent, afternoonPresent) {
  if (morningPresent && afternoonPresent) return ["全天已到", "is-full"];
  if (morningPresent) return ["上午已到", "is-half"];
  if (afternoonPresent) return ["下午已到", "is-half"];
  return ["今日未到", "is-none"];
}

export function attendanceRate(count, total) {
  return `${(total ? count / total * 100 : 0).toFixed(1)}%`;
}

export function periodButtonText(period, present) {
  const periodName = period === "morning" ? "上午" : "下午";
  return `${periodName}${present ? "已签" : "签到"}`;
}

export function updateAttendanceCard(card, state) {
  const periods = {
    morning: Boolean(state.morning_present),
    afternoon: Boolean(state.afternoon_present)
  };
  Object.entries(periods).forEach(([period, present]) => {
    const button = card.querySelector(`[data-period="${period}"]`);
    button.dataset.present = String(present);
    button.classList.toggle("is-present", present);
    button.querySelector("i").textContent = present ? "✓" : "";
    button.querySelector("span").textContent = periodButtonText(period, present);
  });

  const [label, className] = attendanceSummary(periods.morning, periods.afternoon);
  const summary = card.querySelector("[data-summary]");
  summary.textContent = label;
  summary.className = `student-card-status ${className}`;
}

function showToast(root, message, failed = false) {
  const toast = root.querySelector("[data-roll-call-toast]");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("is-error", failed);
  toast.classList.add("is-visible");
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove("is-visible"), 1800);
}

function updateTotals(root, payload) {
  const values = {
    expected: payload.expected_count,
    morning: payload.morning_count,
    afternoon: payload.afternoon_count,
    "full-day": payload.full_day_count
  };
  Object.entries(values).forEach(([key, value]) => {
    const element = root.querySelector(`[data-total="${key}"]`);
    if (element && Number.isFinite(value)) element.textContent = String(value);
  });
  const expected = Number(payload.expected_count) || 0;
  ["morning", "afternoon"].forEach((period) => {
    const element = root.querySelector(`[data-rate="${period}"]`);
    const count = Number(payload[`${period}_count`]) || 0;
    if (element) element.textContent = `到店率 ${attendanceRate(count, expected)}`;
  });
}

export function initAttendanceRollCall(root, fetchImpl = globalThis.fetch) {
  if (!root || !fetchImpl) return;
  const campusId = root.querySelector("[data-campus-id]")?.value || "";
  const attendanceDate = root.querySelector("[data-attendance-date]")?.value || "";
  const checkInUrl = root.dataset.checkInUrl;

  root.querySelectorAll("[data-student-card]").forEach((card) => {
    card.querySelectorAll("[data-period]").forEach((button) => {
      button.addEventListener("click", async () => {
        const morningButton = card.querySelector('[data-period="morning"]');
        const afternoonButton = card.querySelector('[data-period="afternoon"]');
        const previous = {
          morning_present: morningButton.dataset.present === "true",
          afternoon_present: afternoonButton.dataset.present === "true"
        };
        const period = button.dataset.period;
        const next = {
          ...previous,
          [`${period}_present`]: button.dataset.present !== "true"
        };
        updateAttendanceCard(card, next);
        morningButton.disabled = true;
        afternoonButton.disabled = true;

        const body = new URLSearchParams({
          student_id: card.dataset.studentId,
          campus_id: campusId,
          attendance_date: attendanceDate,
          period,
          present: String(next[`${period}_present`])
        });
        try {
          const response = await fetchImpl(checkInUrl, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
            body
          });
          if (!response.ok) throw new Error("save failed");
          const payload = await response.json();
          updateAttendanceCard(card, payload);
          updateTotals(root, payload);
          showToast(root, "点名已保存");
        } catch (error) {
          updateAttendanceCard(card, previous);
          showToast(root, "保存失败，请重试", true);
        } finally {
          morningButton.disabled = false;
          afternoonButton.disabled = false;
        }
      });
    });
  });
}

if (typeof document !== "undefined") {
  initAttendanceRollCall(document.querySelector("[data-roll-call-root]"));
}
