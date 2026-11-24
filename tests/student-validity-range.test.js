import test from "node:test";
import assert from "node:assert/strict";

import { initStudentValidityRange } from "../app/static/student-validity-range.js";

function fixture() {
  const startInput = { value: "" };
  const endInput = { value: "" };
  let controlClick;
  const control = {
    addEventListener(event, callback) {
      assert.equal(event, "click");
      controlClick = callback;
    }
  };
  const root = {
    dataset: {},
    querySelector(selector) {
      return {
        '[name="started_on"]': startInput,
        '[name="ended_on"]': endInput,
        ".validity-range-control": control
      }[selector];
    }
  };

  return { root, startInput, endInput, getControlClick: () => controlClick };
}

class FakeLitepicker {
  constructor(options) {
    this.options = options;
    this.shownFor = [];
  }
  show(input) {
    this.shownFor.push(input);
  }
}

test("the compact range control opens one shared two-month picker", () => {
  const { root, startInput, endInput, getControlClick } = fixture();

  const picker = initStudentValidityRange(root, FakeLitepicker);
  assert.equal(picker.options.element, startInput);
  assert.equal(picker.options.elementEnd, endInput);
  assert.equal(picker.options.numberOfMonths, 2);
  assert.equal(picker.options.splitView, false);
  assert.equal(root.dataset.validityReady, "true");

  getControlClick()({ target: endInput });
  assert.deepEqual(picker.shownFor, [endInput]);
});

test("initialization accepts the namespace exposed by the vendored UMD build", () => {
  const { root } = fixture();
  const picker = initStudentValidityRange(root, { Litepicker: FakeLitepicker, default: FakeLitepicker });
  assert.ok(picker instanceof FakeLitepicker);
});
