/* ByteBodega — interface behaviour */
(function () {
  "use strict";

  /* Sidebar (mobile) -------------------------------------------------- */
  var sidebar = document.getElementById("sidebar");
  var overlay = document.querySelector("[data-sidebar-close]");

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("is-open");
    if (overlay) {
      overlay.classList.remove("is-open");
      overlay.hidden = true;
    }
  }

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add("is-open");
    if (overlay) {
      overlay.hidden = false;
      window.requestAnimationFrame(function () {
        overlay.classList.add("is-open");
      });
    }
  }

  document.querySelectorAll("[data-sidebar-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (sidebar && sidebar.classList.contains("is-open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  });
  if (overlay) overlay.addEventListener("click", closeSidebar);
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeSidebar();
  });

  /* Password visibility ----------------------------------------------- */
  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      var wrap = button.closest(".input-wrap");
      var input = wrap ? wrap.querySelector("input") : null;
      if (!input) return;
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      var on = button.querySelector("[data-eye-on]");
      var off = button.querySelector("[data-eye-off]");
      if (on) on.hidden = show;
      if (off) off.hidden = !show;
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
      input.focus();
    });
  });

  /* Toast messages ---------------------------------------------------- */
  function dismiss(toast) {
    toast.classList.add("is-leaving");
    window.setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 220);
  }

  document.querySelectorAll(".toast").forEach(function (toast) {
    var close = toast.querySelector("[data-dismiss]");
    if (close) close.addEventListener("click", function () { dismiss(toast); });
    window.setTimeout(function () { dismiss(toast); }, 6000);
  });

  /* Destructive action confirmation ----------------------------------- */
  document.querySelectorAll("[data-confirm]").forEach(function (element) {
    element.addEventListener("click", function (event) {
      if (!window.confirm(element.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  /* Auto submit filter selects ---------------------------------------- */
  document.querySelectorAll("[data-autosubmit]").forEach(function (select) {
    select.addEventListener("change", function () {
      if (select.form) select.form.submit();
    });
  });

  /* Quantity steppers ------------------------------------------------- */
  document.querySelectorAll("[data-stepper]").forEach(function (stepper) {
    var input = stepper.querySelector(".qty-input");
    if (!input) return;
    stepper.querySelectorAll("[data-step]").forEach(function (button) {
      button.addEventListener("click", function () {
        var step = parseInt(button.getAttribute("data-step"), 10) || 1;
        var min = parseInt(input.min || "1", 10);
        var max = parseInt(input.max || "999", 10);
        var next = (parseInt(input.value, 10) || min) + step;
        if (max > 0) next = Math.min(next, max);
        input.value = Math.max(min, next);
      });
    });
  });

  /* Keep quantity inputs inside their bounds -------------------------- */
  document.querySelectorAll(".qty-input").forEach(function (input) {
    input.addEventListener("change", function () {
      var min = parseInt(input.min || "1", 10);
      var max = parseInt(input.max || "0", 10);
      var value = parseInt(input.value, 10);
      if (isNaN(value) || value < min) value = min;
      if (max > 0 && value > max) value = max;
      input.value = value;
    });
  });
})();
