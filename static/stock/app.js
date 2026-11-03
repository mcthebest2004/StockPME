(() => {
  const root = document.documentElement;
  let theme = {primary: '#C9A6D9', bg: '#FAF7F2', mode: 'system'};
  try { Object.assign(theme, JSON.parse(localStorage.getItem('stockpme_theme')) || {}); } catch (_) {}
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  function apply() {
    const dark = theme.mode === 'dark' || (theme.mode === 'system' && system.matches);
    root.dataset.theme = dark ? 'dark' : 'light';
    if (/^#[0-9a-f]{6}$/i.test(theme.primary)) root.style.setProperty('--primary', theme.primary);
    if (/^#[0-9a-f]{6}$/i.test(theme.bg)) root.style.setProperty('--bg', dark ? '#242220' : theme.bg);
    root.style.setProperty('--primary-ink', dark ? '#E8CEE8' : '#4A2E52');
    // Buttons use dark text against their pastel backgrounds in both modes.
    document.querySelectorAll('.swatch').forEach(b => b.classList.toggle('active', b.dataset.primary === theme.primary));
    for (const [id, key] of [['customPrimary','primary'], ['customBg','bg'], ['modeSelect','mode']]) {
      const input = document.getElementById(id); if (input) input.value = theme[key];
    }
    try {localStorage.setItem('stockpme_theme', JSON.stringify(theme));} catch (_) {}
  }
  apply(); system.addEventListener('change', apply);
  document.getElementById('themeBtn')?.addEventListener('click', () => document.getElementById('themeDialog').showModal());
  document.querySelectorAll('.swatch').forEach(b => b.addEventListener('click', () => {theme.primary=b.dataset.primary;theme.bg=b.dataset.bg;apply();}));
  for (const [id,key] of [['customPrimary','primary'],['customBg','bg'],['modeSelect','mode']]) {
    document.getElementById(id)?.addEventListener('input', e => {theme[key]=e.target.value;apply();});
  }
  let previewURL;
  document.getElementById('id_photo')?.addEventListener('change', e => {
    const preview = document.getElementById('photoPreview');
    if (previewURL) URL.revokeObjectURL(previewURL);
    const file = e.target.files[0];
    preview.hidden = !file;
    if (file) {previewURL=URL.createObjectURL(file);preview.src=previewURL;}
  });
})();
