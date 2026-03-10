(function () {
  var STORAGE_KEY = "oleaTaxcoTheme";
  var root = document.documentElement;
  var button = document.querySelector("[data-theme-toggle]");
  if (!button) return;

  if (!button.dataset.toggleReady) {
    button.innerHTML =
      '<span class="toggle-label toggle-label-light">Day</span>' +
      '<span class="toggle-track" aria-hidden="true"><span class="toggle-thumb"></span></span>' +
      '<span class="toggle-label toggle-label-dark">Night</span>';
    button.dataset.toggleReady = "true";
  }

  function getPreferredTheme() {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    var isDark = theme === "dark";
    root.setAttribute("data-theme", theme);
    button.setAttribute("aria-pressed", isDark ? "true" : "false");
    button.setAttribute("aria-label", "Toggle day/night mode");
  }

  var currentTheme = getPreferredTheme();
  applyTheme(currentTheme);

  button.addEventListener("click", function () {
    currentTheme = currentTheme === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE_KEY, currentTheme);
    applyTheme(currentTheme);
  });
})();
