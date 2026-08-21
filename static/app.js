(function () {
  "use strict";

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function getCookie(name) {
    var parts = ("; " + document.cookie).split("; " + name + "=");
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop().split(";").shift() || "");
    }
    return "";
  }

  function csrfToken() {
    var meta = $('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    return getCookie("worklog_csrf") || "";
  }

  function apiHeaders(extra) {
    var h = {
      Accept: "application/json",
      "X-CSRF-Token": csrfToken(),
    };
    if (extra) {
      Object.keys(extra).forEach(function (k) {
        h[k] = extra[k];
      });
    }
    return h;
  }

  function toast(msg, kind) {
    var el = $("#toast");
    if (!el) return;
    el.hidden = false;
    el.textContent = msg;
    el.className = "toast" + (kind ? " " + kind : "");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () {
      el.hidden = true;
    }, 2600);
  }

  if (window.WorklogPrefs) {
    window.WorklogPrefs.bind(function (_name, _value, message) {
      toast(message, "ok");
    });
  }

  // ── Create entry → reload list (single HTML source: server) ──
  var form = $("#entry-form");
  if (form) {
    form.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var statusEl = $("#form-status");
      var submitBtn = $("#submit-btn");
      var payload = {
        date: $("#date").value,
        category: $("#category").value,
        status: $("#status").value,
        title: $("#title").value.trim(),
        details: $("#details").value.trim(),
        tags: $("#tags") ? $("#tags").value.trim() : "",
        follow_up: $("#follow_up") ? $("#follow_up").value : "",
      };
      if (!payload.title) {
        if (statusEl) {
          statusEl.textContent = "Title is required";
          statusEl.className = "form-status err";
        }
        return;
      }
      if (submitBtn) submitBtn.disabled = true;
      if (statusEl) {
        statusEl.textContent = "Saving…";
        statusEl.className = "form-status";
      }
      try {
        var res = await fetch("/api/entries", {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify(payload),
          credentials: "same-origin",
        });
        var data = await res.json();
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!res.ok || !data.ok) {
          throw new Error(data.error || "Save failed");
        }
        toast("Entry saved", "ok");
        window.location.reload();
      } catch (err) {
        if (statusEl) {
          statusEl.textContent = err.message || "Error saving";
          statusEl.className = "form-status err";
        }
        toast(err.message || "Error saving", "err");
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // ── Edit modal ──
  var modal = $("#edit-modal");
  var editForm = $("#edit-form");
  var lastFocus = null;

  function focusable(root) {
    return $$(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
      root
    ).filter(function (el) {
      return !el.hasAttribute("disabled") && el.offsetParent !== null;
    });
  }

  function openModal(btn) {
    if (!modal) return;
    lastFocus = btn;
    $("#edit-id").value = btn.dataset.id || "";
    $("#edit-date").value = btn.dataset.date || "";
    $("#edit-title-input").value = btn.dataset.title || "";
    $("#edit-details").value = btn.dataset.details || "";
    $("#edit-category").value = btn.dataset.category || "General";
    var statusSelect = $("#edit-entry-status");
    if (statusSelect) statusSelect.value = btn.dataset.status || "done";
    var tagsEl = $("#edit-tags");
    if (tagsEl) tagsEl.value = btn.dataset.tags || "";
    var fuEl = $("#edit-follow-up");
    if (fuEl) fuEl.value = btn.dataset.followUp || "";
    var st = $("#edit-form-status");
    if (st) {
      st.textContent = "";
      st.className = "form-status";
    }
    modal.hidden = false;
    document.body.classList.add("modal-open");
    setTimeout(function () {
      var t = $("#edit-title-input");
      if (t) t.focus();
    }, 30);
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener("click", function (ev) {
    var editBtn = ev.target.closest(".edit-btn");
    if (editBtn) {
      openModal(editBtn);
      return;
    }
    if (ev.target.closest("[data-close-modal]")) closeModal();
  });

  document.addEventListener("keydown", function (ev) {
    if (!modal || modal.hidden) return;
    if (ev.key === "Escape") {
      closeModal();
      return;
    }
    if (ev.key === "Tab") {
      var nodes = focusable(modal);
      if (!nodes.length) return;
      var first = nodes[0];
      var last = nodes[nodes.length - 1];
      if (ev.shiftKey && document.activeElement === first) {
        ev.preventDefault();
        last.focus();
      } else if (!ev.shiftKey && document.activeElement === last) {
        ev.preventDefault();
        first.focus();
      }
    }
  });

  if (editForm) {
    editForm.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var id = $("#edit-id").value;
      var statusSelect = $("#edit-entry-status");
      var payload = {
        date: $("#edit-date").value,
        title: $("#edit-title-input").value.trim(),
        details: $("#edit-details").value.trim(),
        category: $("#edit-category").value,
        status: statusSelect ? statusSelect.value : "done",
        tags: $("#edit-tags") ? $("#edit-tags").value.trim() : "",
        follow_up: $("#edit-follow-up") ? $("#edit-follow-up").value : "",
      };
      var st = $("#edit-form-status");
      var saveBtn = $("#edit-save-btn");
      if (!payload.title) {
        if (st) {
          st.textContent = "Title is required";
          st.className = "form-status err";
        }
        return;
      }
      if (saveBtn) saveBtn.disabled = true;
      try {
        var res = await fetch("/api/entries/" + encodeURIComponent(id), {
          method: "PUT",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify(payload),
          credentials: "same-origin",
        });
        var data = await res.json();
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!res.ok || !data.ok) throw new Error(data.error || "Update failed");
        toast("Entry updated", "ok");
        window.location.reload();
      } catch (err) {
        if (st) {
          st.textContent = err.message || "Update failed";
          st.className = "form-status err";
        }
        toast(err.message || "Update failed", "err");
        if (saveBtn) saveBtn.disabled = false;
      }
    });
  }

  // ── Delete ──
  document.addEventListener("click", async function (ev) {
    var btn = ev.target.closest(".delete-btn");
    if (!btn) return;
    var id = btn.dataset.id;
    if (!id || !confirm("Delete this entry? This cannot be undone.")) return;
    try {
      var res = await fetch("/api/entries/" + encodeURIComponent(id), {
        method: "DELETE",
        headers: apiHeaders(),
        credentials: "same-origin",
      });
      var data = await res.json();
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok || !data.ok) throw new Error(data.error || "Delete failed");
      toast("Entry deleted", "ok");
      window.location.reload();
    } catch (err) {
      toast(err.message || "Delete failed", "err");
    }
  });

  // ── Account: password ──
  var pwForm = $("#password-form");
  if (pwForm) {
    pwForm.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var st = $("#pw-status");
      var btn = $("#pw-submit");
      if ($("#new_password").value !== $("#confirm_password").value) {
        if (st) {
          st.textContent = "New passwords do not match";
          st.className = "form-status err";
        }
        return;
      }
      if (btn) btn.disabled = true;
      try {
        var res = await fetch("/api/change-password", {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          credentials: "same-origin",
          body: JSON.stringify({
            current_password: $("#current_password").value,
            new_password: $("#new_password").value,
            confirm_password: $("#confirm_password").value,
            csrf_token: csrfToken(),
          }),
        });
        var data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "Update failed");
        toast("Password updated. Sign in again.", "ok");
        window.location.href = "/login?next=/settings";
      } catch (err) {
        if (st) {
          st.textContent = err.message || "Update failed";
          st.className = "form-status err";
        }
        toast(err.message || "Update failed", "err");
        if (btn) btn.disabled = false;
      }
    });
  }

  // ── Account: ticket system ──
  var ticketForm = $("#ticket-form");
  if (ticketForm) {
    ticketForm.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var st = $("#ticket-status");
      var btn = $("#ticket-submit");
      if (btn) btn.disabled = true;
      try {
        var res = await fetch("/api/ticket-settings", {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          credentials: "same-origin",
          body: JSON.stringify({
            url: $("#ticket-url") ? $("#ticket-url").value.trim() : "",
            prefixes: $("#ticket-prefixes")
              ? $("#ticket-prefixes").value.trim()
              : "",
            csrf_token: csrfToken(),
          }),
        });
        var data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "Save failed");
        toast("Ticket system saved", "ok");
        if (st) {
          st.textContent = "Saved";
          st.className = "form-status ok";
        }
        if (btn) btn.disabled = false;
      } catch (err) {
        if (st) {
          st.textContent = err.message || "Save failed";
          st.className = "form-status err";
        }
        toast(err.message || "Save failed", "err");
        if (btn) btn.disabled = false;
      }
    });
  }

  // ── Admin: rename ──
  var renameForm = $("#rename-form");
  if (renameForm) {
    renameForm.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var st = $("#rename-status");
      var btn = $("#rename-submit");
      if (btn) btn.disabled = true;
      try {
        var res = await fetch("/api/rename-user", {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          credentials: "same-origin",
          body: JSON.stringify({
            new_username: $("#new-username").value.trim(),
            display_name: $("#new-display-name")
              ? $("#new-display-name").value.trim()
              : "",
            csrf_token: csrfToken(),
          }),
        });
        var data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "Rename failed");
        toast("Username updated. Sign in again.", "ok");
        window.location.href = "/login";
      } catch (err) {
        if (st) {
          st.textContent = err.message || "Rename failed";
          st.className = "form-status err";
        }
        toast(err.message || "Rename failed", "err");
        if (btn) btn.disabled = false;
      }
    });
  }

  // ── Admin: create / update user ──
  function postUser(payload, statusSel, btnSel) {
    return (async function () {
      var st = $(statusSel);
      var btn = $(btnSel);
      if (btn) btn.disabled = true;
      try {
        payload.csrf_token = csrfToken();
        var res = await fetch("/api/users", {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          credentials: "same-origin",
          body: JSON.stringify(payload),
        });
        var data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "Failed");
        toast("User saved", "ok");
        window.location.reload();
      } catch (err) {
        if (st) {
          st.textContent = err.message || "Failed";
          st.className = "form-status err";
        }
        toast(err.message || "Failed", "err");
        if (btn) btn.disabled = false;
      }
    })();
  }

  var cuForm = $("#create-user-form");
  if (cuForm) {
    cuForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      postUser(
        {
          action: "create",
          username: $("#cu-username").value.trim(),
          password: $("#cu-password").value,
          role: $("#cu-role").value,
        },
        "#cu-status",
        "#cu-submit"
      );
    });
  }

  var auForm = $("#admin-user-form");
  if (auForm) {
    auForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var payload = {
        action: "update",
        username: $("#au-username").value.trim(),
      };
      var role = $("#au-role").value;
      if (role) payload.role = role;
      var pw = $("#au-password").value;
      if (pw) payload.password = pw;
      postUser(payload, "#au-status", "#au-submit");
    });
  }

  // ── Backup / restore ──
  var backupBtn = $("#backup-now-btn");
  if (backupBtn) {
    backupBtn.addEventListener("click", async function () {
      var st = $("#backup-status");
      backupBtn.disabled = true;
      try {
        var res = await fetch("/api/backup", {
          method: "POST",
          headers: apiHeaders({ "Content-Type": "application/json" }),
          credentials: "same-origin",
          body: JSON.stringify({ csrf_token: csrfToken() }),
        });
        var data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "Backup failed");
        toast("Backup created", "ok");
        window.location.reload();
      } catch (err) {
        if (st) {
          st.textContent = err.message || "Backup failed";
          st.className = "form-status err";
        }
        toast(err.message || "Backup failed", "err");
        backupBtn.disabled = false;
      }
    });
  }

  document.addEventListener("click", async function (ev) {
    var btn = ev.target.closest(".restore-btn");
    if (!btn) return;
    var name = btn.dataset.name;
    if (
      !name ||
      !confirm(
        "Restore database from " +
          name +
          "?\n\nCurrent data is backed up first as pre-restore."
      )
    ) {
      return;
    }
    try {
      var res = await fetch("/api/restore", {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        credentials: "same-origin",
        body: JSON.stringify({ name: name, csrf_token: csrfToken() }),
      });
      var data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Restore failed");
      toast("Restored. Reloading.", "ok");
      window.location.href = "/";
    } catch (err) {
      toast(err.message || "Restore failed", "err");
    }
  });

  // ── Copy weekly highlights ──
  var copyBtn = $("#copy-talking-points");
  if (copyBtn) {
    copyBtn.addEventListener("click", async function () {
      var raw = $("#talking-points-raw");
      var text = raw ? raw.value : copyBtn.getAttribute("data-text") || "";
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          var ta = document.createElement("textarea");
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        }
        toast("Weekly highlights copied", "ok");
      } catch (err) {
        toast("Could not copy. Select text manually.", "err");
      }
    });
  }
})();
