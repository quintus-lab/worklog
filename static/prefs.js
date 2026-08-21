/* One preference table for theme + text size. Boot before CSS to avoid flash. */
(function (global) {
  "use strict";

  var PREFS = {
    theme: {
      key: "worklog-theme",
      attr: "data-theme",
      steps: ["paper", "dark"],
      labels: { paper: "Paper", dark: "Dark" },
      toasts: {
        paper: "Paper theme",
        dark: "Dark mode",
      },
      fallback: function () {
        return "paper";
      },
    },
    font: {
      key: "worklog-font",
      attr: "data-font-size",
      steps: ["md", "lg", "xl"],
      labels: { md: "Md", lg: "Lg", xl: "Xl" },
      toasts: {
        md: "Default text size",
        lg: "Larger text",
        xl: "Largest text",
      },
      fallback: function () {
        return "md";
      },
    },
  };

  function stored(spec) {
    try {
      var v = localStorage.getItem(spec.key);
      if (spec.attr === "data-theme" && v === "light") v = "paper";
      if (spec.steps.indexOf(v) !== -1) return v;
    } catch (e) {}
    return spec.fallback();
  }

  function apply(name, value, persist) {
    var spec = PREFS[name];
    if (!spec) return value;
    if (spec.steps.indexOf(value) === -1) value = spec.fallback();
    document.documentElement.setAttribute(spec.attr, value);
    if (name === "theme") {
      document.documentElement.style.colorScheme =
        value === "dark" ? "dark" : "light";
      var themeColor = value === "dark" ? "#0f1218" : "#f5f4ed";
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", themeColor);
    }
    if (persist) {
      try {
        localStorage.setItem(spec.key, value);
      } catch (e) {}
    }
    return value;
  }

  function boot() {
    apply("theme", stored(PREFS.theme), false);
    apply("font", stored(PREFS.font), false);
    try {
      if (localStorage.getItem(PREFS.theme.key) === "light") {
        localStorage.setItem(PREFS.theme.key, "paper");
      }
    } catch (e) {}
  }

  function paintButton(name, value) {
    var spec = PREFS[name];
    var btn = document.getElementById(name + "-toggle");
    var label = document.getElementById(name + "-toggle-label");
    if (label) label.textContent = spec.labels[value] || value;
    if (btn) {
      btn.setAttribute("aria-label", (spec.labels[value] || value) + " (click to change)");
      btn.title = spec.labels[value] || value;
    }
  }

  function bind(onChange) {
    Object.keys(PREFS).forEach(function (name) {
      var spec = PREFS[name];
      var btn = document.getElementById(name + "-toggle");
      if (!btn) return;
      var current =
        document.documentElement.getAttribute(spec.attr) || stored(spec);
      current = apply(name, current, false);
      paintButton(name, current);
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        var cur = document.documentElement.getAttribute(spec.attr);
        var i = spec.steps.indexOf(cur);
        var next = spec.steps[(i + 1) % spec.steps.length];
        apply(name, next, true);
        paintButton(name, next);
        if (onChange) onChange(name, next, spec.toasts[next] || next);
      });
    });
  }

  global.WorklogPrefs = { boot: boot, bind: bind, apply: apply };
})(typeof window !== "undefined" ? window : this);
