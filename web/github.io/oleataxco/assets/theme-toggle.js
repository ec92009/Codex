(function () {
  var STORAGE_KEY = "oleaTaxcoTheme";
  var root = document.documentElement;
  var button = document.querySelector("[data-theme-toggle]");
  if (!button) return;

  if (!button.dataset.toggleReady) {
    button.innerHTML =
      '<span class="toggle-label toggle-label-light">Light</span>' +
      '<span class="toggle-track" aria-hidden="true"><span class="toggle-thumb"></span></span>' +
      '<span class="toggle-label toggle-label-dark">Dark</span>';
    button.dataset.toggleReady = "true";
  }

  function getPreferredTheme() {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
    /* Default to dark — the executive deck look */
    return "dark";
  }

  function applyTheme(theme) {
    var isLight = theme === "light";
    if (isLight) {
      root.setAttribute("data-theme", "light");
    } else {
      root.removeAttribute("data-theme");
    }
    /* aria-pressed true = light mode active (toggle is "on") */
    button.setAttribute("aria-pressed", isLight ? "true" : "false");
    button.setAttribute("aria-label", "Toggle light/dark mode");
  }

  var currentTheme = getPreferredTheme();
  applyTheme(currentTheme);

  button.addEventListener("click", function () {
    currentTheme = currentTheme === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE_KEY, currentTheme);
    applyTheme(currentTheme);
  });
})();
