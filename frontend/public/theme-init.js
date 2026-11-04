// Runs before the page draws, so dark mode never flashes white first. A file
// rather than an inline script so the Content-Security-Policy can forbid
// inline scripts. Kept in step with src/lib/theme.ts.
(function () {
  var choice = "system";
  try { choice = localStorage.getItem("studymate-theme") || "system"; } catch (e) {}
  var dark = choice === "dark" || (choice !== "light" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  if (dark) document.documentElement.classList.add("dark");
})();
