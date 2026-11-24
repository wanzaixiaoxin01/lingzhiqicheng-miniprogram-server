export function initStudentValidityRange(root, LitepickerExport = globalThis.Litepicker) {
  const LitepickerClass = typeof LitepickerExport === "function"
    ? LitepickerExport
    : LitepickerExport?.Litepicker || LitepickerExport?.default;
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
    splitView: false,
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

  const control = root.querySelector(".validity-range-control");
  control?.addEventListener("click", (event) => {
    picker.show(event.target === endInput ? endInput : startInput);
  });
  root.dataset.validityReady = "true";
  return picker;
}

if (typeof document !== "undefined") {
  initStudentValidityRange(document.querySelector("[data-validity-range]"));
}
