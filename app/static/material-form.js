export function materialTitleFromFilename(filename) {
  return String(filename || "").replace(/\.[^./\\]+$/, "");
}

export function initMaterialTitleAutofill(root = document) {
  const titleInput = root.querySelector("[data-material-title]");
  const fileInput = root.querySelector("[data-material-file]");
  if (!titleInput || !fileInput) {
    return;
  }

  fileInput.addEventListener("change", () => {
    if (titleInput.value.trim() || !fileInput.files || !fileInput.files.length) {
      return;
    }
    titleInput.value = materialTitleFromFilename(fileInput.files[0].name);
  });
}

if (typeof document !== "undefined") {
  initMaterialTitleAutofill();
}
