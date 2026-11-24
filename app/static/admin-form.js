function showAdminToast(message) {
  let toast = document.querySelector('[data-admin-toast]');
  if (!toast) {
    toast = document.createElement('div');
    toast.dataset.adminToast = 'true';
    toast.className = 'admin-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message || '提交失败，请稍后重试';
  toast.classList.add('is-visible', 'is-error');
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove('is-visible'), 2600);
}

function errorMessage(payload) {
  if (typeof payload?.detail === 'string') return payload.detail;
  if (Array.isArray(payload?.detail)) return payload.detail.map(item => item.msg).filter(Boolean).join('；');
  return '提交失败，请检查表单后重试';
}

document.addEventListener('submit', async event => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || form.dataset.nativeSubmit === 'true') return;
  event.preventDefault();
  const submitter = event.submitter;
  const button = submitter instanceof HTMLButtonElement ? submitter : form.querySelector('button[type="submit"], button:not([type])');
  if (button) button.disabled = true;
  try {
    const action = submitter?.formAction || form.action;
    const response = await fetch(action, {
      method: (form.method || 'post').toUpperCase(),
      body: new FormData(form),
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (response.ok) {
      if (response.redirected) window.location.assign(response.url);
      else window.location.reload();
      return;
    }
    let payload = null;
    try { payload = await response.json(); } catch (_) { /* handled by fallback text */ }
    showAdminToast(errorMessage(payload));
  } catch (_) {
    showAdminToast('网络异常，请稍后重试');
  } finally {
    if (button) button.disabled = false;
  }
});
