(function () {
  var STORAGE_KEY = "oleaTaxcoTheme";
  var root = document.documentElement;
  var button = document.querySelector("[data-theme-toggle]");
  if (!button) return;

  function getPreferredTheme() {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    button.textContent = theme === "dark" ? "Day mode" : "Night mode";
    button.setAttribute("aria-label", theme === "dark" ? "Switch to day mode" : "Switch to night mode");
  }

  var currentTheme = getPreferredTheme();
  applyTheme(currentTheme);

  button.addEventListener("click", function () {
    currentTheme = currentTheme === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE_KEY, currentTheme);
    applyTheme(currentTheme);
  });
})();
