import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  initMaterialTitleAutofill,
  materialTitleFromFilename
} from "../app/static/material-form.js";

const testRoot = dirname(fileURLToPath(import.meta.url));
const resourceForm = readFileSync(resolve(testRoot, "../app/templates/resource_form.html"), "utf8");

test("new material form accepts multiple files and explains generated titles", () => {
  assert.match(resourceForm, /name="file"[^>]*data-material-file[^>]*multiple/);
  assert.match(resourceForm, /每个文件将创建一条公告记录，标题自动取文件名/);
});

test("material title uses the selected filename without its extension", () => {
  assert.equal(
    materialTitleFromFilename("2026-2027学年期中试卷七上地理.pdf"),
    "2026-2027学年期中试卷七上地理"
  );
});

test("material file selection fills an empty title", () => {
  const listeners = {};
  const titleInput = { value: "" };
  const fileInput = {
    files: [{ name: "七上地理期中试卷.pdf" }],
    addEventListener(event, handler) {
      listeners[event] = handler;
    }
  };
  const root = {
    querySelector(selector) {
      return selector === "[data-material-title]" ? titleInput : fileInput;
    }
  };

  initMaterialTitleAutofill(root);
  listeners.change();

  assert.equal(titleInput.value, "七上地理期中试卷");
});

test("material file selection preserves an existing title", () => {
  const listeners = {};
  const titleInput = { value: "运营填写的标题" };
  const fileInput = {
    files: [{ name: "new-file.pdf" }],
    addEventListener(event, handler) {
      listeners[event] = handler;
    }
  };
  const root = {
    querySelector(selector) {
      return selector === "[data-material-title]" ? titleInput : fileInput;
    }
  };

  initMaterialTitleAutofill(root);
  listeners.change();

  assert.equal(titleInput.value, "运营填写的标题");
});
