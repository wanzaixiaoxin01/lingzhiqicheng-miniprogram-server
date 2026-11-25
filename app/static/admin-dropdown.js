(() => {
  const selectors = 'select:not(.lead-status-native):not([data-dropdown-ready])';
  const close = (dropdown) => {
    dropdown.classList.remove('is-open');
    dropdown._adminMenu?.classList.remove('is-open');
    dropdown.querySelector('.admin-select-trigger')?.setAttribute('aria-expanded', 'false');
    const menu = dropdown._adminMenu;
    if (menu) {
      menu.style.left = '';
      menu.style.top = '';
      menu.style.minWidth = '';
    }
  };
  const position = (dropdown) => {
    if (!dropdown.classList.contains('is-open')) return;
    const trigger = dropdown.querySelector('.admin-select-trigger');
    const menu = dropdown._adminMenu;
    if (!trigger || !menu) return;
    const rect = trigger.getBoundingClientRect();
    const padding = 8;
    menu.style.minWidth = `${Math.max(rect.width, 180)}px`;
    const menuHeight = menu.offsetHeight;
    const below = rect.bottom + 6;
    const above = rect.top - menuHeight - 6;
    const top = window.innerHeight - below >= menuHeight + padding || above < padding ? below : above;
    const left = Math.min(Math.max(padding, rect.left), Math.max(padding, window.innerWidth - menu.offsetWidth - padding));
    menu.style.left = `${left}px`;
    menu.style.top = `${Math.min(Math.max(padding, top), Math.max(padding, window.innerHeight - menu.offsetHeight - padding))}px`;
  };

  document.querySelectorAll(selectors).forEach((select) => {
    select.dataset.dropdownReady = 'true';
    const wrapper = document.createElement('div');
    wrapper.className = 'admin-select';
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);
    select.classList.add('admin-select-native');

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'admin-select-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-label', select.getAttribute('aria-label') || select.name || '选择');
    wrapper.insertBefore(trigger, select);

    const menu = document.createElement('div');
    menu.className = 'admin-select-menu';
    menu.setAttribute('role', 'listbox');
    menu.setAttribute('aria-label', trigger.getAttribute('aria-label'));
    document.body.appendChild(menu);
    wrapper._adminMenu = menu;

    const sync = () => {
      const selected = select.options[select.selectedIndex];
      trigger.innerHTML = `<span>${selected?.textContent || ''}</span><span class="admin-select-chevron" aria-hidden="true">⌄</span>`;
      menu.querySelectorAll('.admin-select-option').forEach((option) => {
        const active = option.dataset.value === select.value;
        option.classList.toggle('is-selected', active);
        option.setAttribute('aria-selected', String(active));
      });
    };
    Array.from(select.options).forEach((option) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'admin-select-option';
      item.dataset.value = option.value;
      item.setAttribute('role', 'option');
      item.textContent = option.textContent;
      item.addEventListener('click', () => {
        select.value = option.value;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        close(wrapper);
        trigger.focus();
      });
      menu.appendChild(item);
    });
    select.addEventListener('change', sync);
    sync();
    trigger.addEventListener('click', (event) => {
      event.stopPropagation();
      document.querySelectorAll('.admin-select.is-open').forEach((other) => { if (other !== wrapper) close(other); });
      const open = wrapper.classList.toggle('is-open');
      menu.classList.toggle('is-open', open);
      trigger.setAttribute('aria-expanded', String(open));
      if (open) position(wrapper);
    });
    trigger.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        trigger.click();
      }
      if (event.key === 'Escape') close(wrapper);
    });
    wrapper.addEventListener('click', (event) => event.stopPropagation());
  });

  document.addEventListener('click', () => document.querySelectorAll('.admin-select.is-open').forEach(close));
  window.addEventListener('resize', () => document.querySelectorAll('.admin-select.is-open').forEach(position));
  window.addEventListener('scroll', () => document.querySelectorAll('.admin-select.is-open').forEach(position), true);
})();
