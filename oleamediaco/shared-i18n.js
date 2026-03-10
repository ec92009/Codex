(function () {
  function initOleaI18n(defaultLang) {
    var translations = window.OLEA_TRANSLATIONS || {};
    var current = defaultLang || 'en';
    var langButtons = Array.from(document.querySelectorAll('.lang-flag[data-lang]'));

    function applyLang(lang) {
      var dict = translations[lang];
      if (!dict) return;
      document.documentElement.lang = lang.toLowerCase();
      document.querySelectorAll('[data-i18n]').forEach(function (el) {
        var key = el.getAttribute('data-i18n');
        if (dict[key] != null) el.textContent = dict[key];
      });
      langButtons.forEach(function (btn) {
        var active = btn.dataset.lang === lang;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-pressed', String(active));
      });
      current = lang;
      document.body.setAttribute('data-lang', lang);
    }

    langButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var next = btn.dataset.lang;
        if (next && next !== current) applyLang(next);
      });
    });

    applyLang(current);
    return { applyLang: applyLang };
  }

  window.initOleaI18n = initOleaI18n;
})();
