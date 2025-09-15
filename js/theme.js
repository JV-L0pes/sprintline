// Theme toggling with persistence and event broadcast
(function () {
  const THEME_KEY = 'theme';

  function getSystemPrefersDark() {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function applyTheme(theme) {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
    } else {
      root.removeAttribute('data-theme');
    }
  }

  function getInitialTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return getSystemPrefersDark() ? 'dark' : 'light';
  }

  function updateToggleIcon(button, theme) {
    if (!button) return;
    const icon = button.querySelector('i');
    if (!icon) return;
    // moon for light (to switch to dark), sun for dark (to switch to light)
    icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    button.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
  }

  function setTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
    applyTheme(theme);
    const btn = document.getElementById('theme-toggle');
    updateToggleIcon(btn, theme);
    // Broadcast to the page/app
    const evt = new CustomEvent('themechange', { detail: { theme } });
    window.dispatchEvent(evt);
  }

  function toggleTheme() {
    const current = (document.documentElement.getAttribute('data-theme') === 'dark') ? 'dark' : 'light';
    setTheme(current === 'dark' ? 'light' : 'dark');
  }

  document.addEventListener('DOMContentLoaded', function () {
    const initial = getInitialTheme();
    applyTheme(initial);
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      updateToggleIcon(btn, initial);
      btn.addEventListener('click', toggleTheme);
    }
  });

  // Sync across tabs
  window.addEventListener('storage', function (e) {
    if (e.key === THEME_KEY && e.newValue) {
      applyTheme(e.newValue);
      const btn = document.getElementById('theme-toggle');
      updateToggleIcon(btn, e.newValue);
      const evt = new CustomEvent('themechange', { detail: { theme: e.newValue } });
      window.dispatchEvent(evt);
    }
  });
})();


