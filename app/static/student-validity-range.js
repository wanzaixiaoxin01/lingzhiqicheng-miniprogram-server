function parseDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : null;
}

function formatDate(value) {
  const pad = (number) => String(number).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
}

export function presetEndDate(start, { days = 0, months = 0 } = {}) {
  const end = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  if (days) {
    end.setDate(end.getDate() + days - 1);
    return end;
  }
  const targetMonth = start.getMonth() + months;
  const lastDay = new Date(start.getFullYear(), targetMonth + 1, 0).getDate();
  end.setFullYear(start.getFullYear(), targetMonth, Math.min(start.getDate(), lastDay));
  end.setDate(end.getDate() - 1);
  return end;
}

export function initStudentValidityRange(root, LitepickerClass = globalThis.Litepicker) {
  if (!root || !LitepickerClass) return null;
  const startInput = root.querySelector('[name="started_on"]');
  const endInput = root.querySelector('[name="ended_on"]');
  if (!startInput || !endInput) return null;

  const picker = new LitepickerClass({
    element: startInput,
    elementEnd: endInput,
    singleMode: false,
    numberOfMonths: 2,
    numberOfColumns: 2,
    splitView: true,
    autoApply: true,
    allowRepick: true,
    format: "YYYY-MM-DD",
    lang: "zh-CN",
    firstDay: 1,
    startDate: startInput.value || null,
    endDate: endInput.value || null,
    tooltipText: { one: "天", other: "天" },
    tooltipNumber: (days) => days
  });

  root.querySelectorAll("[data-validity-days], [data-validity-months]").forEach((button) => {
    button.addEventListener("click", () => {
      const start = parseDate(startInput.value) || new Date();
      const end = presetEndDate(start, {
        days: Number(button.dataset.validityDays || 0),
        months: Number(button.dataset.validityMonths || 0)
      });
      startInput.value = formatDate(start);
      endInput.value = formatDate(end);
      picker.setDateRange(startInput.value, endInput.value);
    });
  });
  return picker;
}

if (typeof document !== "undefined") {
  initStudentValidityRange(document.querySelector("[data-validity-range]"));
}
