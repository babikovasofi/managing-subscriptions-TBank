/* theme.js — единый механизм переключения темы для всех экранов.
   Подключается в <head> с обычным <script src="theme.js"></script>
   (синхронно, до first paint). Без зависимостей. */
(function () {
  // 1) Pre-paint: применяем сохранённую тему до того, как CSS начнёт рисовать.
  try {
    var saved = localStorage.getItem('tb-theme');
    if (saved === 'light' || saved === 'dark') {
      document.documentElement.setAttribute('data-theme', saved);
    }
  } catch (e) {}

  function attach() {
    document.querySelectorAll('[data-theme-toggle], #theme-toggle').forEach(function (btn) {
      if (btn.dataset.themeBound) return;
      btn.dataset.themeBound = '1';
      btn.addEventListener('click', function () {
        var cur = document.documentElement.getAttribute('data-theme') || 'dark';
        var next = cur === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        try { localStorage.setItem('tb-theme', next); } catch (e) {}
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }
})();
