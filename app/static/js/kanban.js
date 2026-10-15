/* Kanban board: AJAX (fetch) against /api, drag & drop via SortableJS. */
(() => {
  "use strict";

  const STATUSES = [
    { key: "todo", label: "To Do" },
    { key: "in_progress", label: "In Progress" },
    { key: "review", label: "Review" },
    { key: "done", label: "Done" },
  ];
  const PRIORITY_RANK = { high: 0, medium: 1, low: 2 };
  const AVATAR_COLORS = ["av-owner", "av-sky", "av-indigo", "av-teal"];

  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const BOARD_ID = document.body.dataset.boardId;
  const CSRF = $('meta[name="csrf-token"]').content;

  const state = { board: null, role: document.body.dataset.role, perms: { edit: false, delete_any: false }, me: null, members: [], tasks: [] };
  const filters = { q: "", member: "all", priority: "all" };
  let sortables = [];
  let lastDragEnd = 0;

  /* ------------------------------------------------------------------ API */
  class ApiError extends Error {
    constructor(status, body) { super((body && body.error) || "Request failed."); this.status = status; this.errors = (body && body.errors) || {}; }
  }
  async function api(method, url, body) {
    let res;
    try {
      res = await fetch(url, {
        method, credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json", "X-CSRFToken": CSRF },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (e) { throw new ApiError(0, { error: "Network error. Check your connection and try again." }); }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON error */ }
    if (res.status === 401) { location.href = "/login?next=" + encodeURIComponent(location.pathname); throw new ApiError(401, data); }
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
  }

  /* ------------------------------------------------------------------ helpers */
  const memberById = (id) => state.members.find((m) => m.id === id);
  const initials = (n) => String(n || "?").slice(0, 2).toUpperCase();
  const colorFor = (id) => AVATAR_COLORS[(id || 0) % AVATAR_COLORS.length];
  const statusLabel = (k) => (STATUSES.find((s) => s.key === k) || {}).label || k;
  const taskById = (id) => state.tasks.find((t) => t.id === Number(id));

  function todayISO() { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }
  function fmtDate(iso, year) { return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", ...(year ? { year: "numeric" } : {}) }); }
  function fmtDateTime(iso) { return iso ? new Date(iso + "Z").toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : ""; }
  function dueInfo(t) {
    if (!t.deadline) return { cls: "", icon: "bi-calendar3", text: "No deadline", full: "No deadline" };
    if (t.status === "done") return { cls: "done", icon: "bi-check2-all", text: fmtDate(t.deadline), full: "Completed" };
    const diff = Math.round((new Date(t.deadline) - new Date(todayISO())) / 86400000);
    const text = "Due: " + fmtDate(t.deadline);
    if (diff < 0) return { cls: "overdue", icon: "bi-alarm", text, full: `${-diff} day(s) overdue` };
    if (diff <= 3) return { cls: "soon", icon: "bi-clock", text, full: diff === 0 ? "Due today" : `${diff} day(s) remaining` };
    return { cls: "", icon: "bi-calendar3", text, full: `${diff} days remaining` };
  }
  const priorityBadge = (p) => `<span class="badge-priority badge-priority-${esc(p)}">${esc(p).toUpperCase()}</span>`;
  function assigneeHTML(id, big) {
    const m = memberById(id);
    if (!m) return `<span class="ttb-assignee none"><i class="bi bi-person-dash"></i> Unassigned</span>`;
    return `<span class="ttb-assignee"><span class="ttb-avatar ${big ? "lg " : ""}${colorFor(m.id)}">${esc(initials(m.username))}</span><span>${esc(m.username)}</span></span>`;
  }
  const compare = (a, b) =>
    (PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]) ||
    ((a.deadline || "9999") < (b.deadline || "9999") ? -1 : (a.deadline || "9999") > (b.deadline || "9999") ? 1 : 0) ||
    a.id - b.id;
  const visible = (t) =>
    t.title.toLowerCase().includes(filters.q) &&
    (filters.member === "all" || String(t.assigned_to) === filters.member) &&
    (filters.priority === "all" || t.priority === filters.priority);

  function toast(message, type = "success") {
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${type === "error" ? "danger" : "dark"} border-0`;
    el.setAttribute("role", type === "error" ? "alert" : "status");
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${esc(message)}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
    $("#toasts").appendChild(el);
    const t = new bootstrap.Toast(el, { delay: type === "error" ? 5000 : 2500 });
    el.addEventListener("hidden.bs.toast", () => el.remove());
    t.show();
  }
  function setBusy(btn, busy, label) {
    if (busy) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>${label || ""}`; }
    else { btn.disabled = false; if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
  }
  const canDelete = (t) => state.perms.delete_any || (state.role === "member" && state.me && t.created_by === state.me.id);

  /* ------------------------------------------------------------------ rendering */
  function cardHTML(t) {
    const due = dueInfo(t);
    return `
    <div class="ttb-card ${t.status === "done" ? "is-done" : ""}" data-id="${t.id}" role="button" tabindex="0" aria-label="Open task ${esc(t.title)}">
      <div class="d-flex align-items-center justify-content-between"><span class="ttb-code">${esc(t.code)}</span>${priorityBadge(t.priority)}</div>
      <h3 class="ttb-card-title">${esc(t.title)}</h3>
      ${t.description ? `<p class="ttb-card-desc">${esc(t.description)}</p>` : ""}
      <div class="ttb-card-foot">
        <span class="ttb-due ${due.cls}"><i class="bi ${due.icon}"></i>${esc(due.text)}</span>
        ${assigneeHTML(t.assigned_to)}
      </div>
    </div>`;
  }

  function renderCards(status) {
    const box = $(`.ttb-cards[data-status="${status}"]`);
    if (!box) return;
    const tasks = state.tasks.filter((t) => t.status === status && visible(t)).sort(compare);
    box.innerHTML = tasks.map(cardHTML).join("") || `<div class="ttb-empty">${state.tasks.some((t) => t.status === status) ? "No matching tasks" : "No tasks"}</div>`;
    const badge = $(`.ttb-column[data-status="${status}"] .ttb-count`);
    if (badge) badge.textContent = tasks.length;
  }
  function renderStats() {
    const n = (k) => state.tasks.filter((t) => t.status === k).length;
    $("#boardStats").textContent = `${state.tasks.length} Tasks • ${n("in_progress")} In Progress • ${n("review")} In Review • ${n("done")} Done`;
  }
  function renderBoard() {
    const editable = state.perms.edit;
    $("#board").innerHTML = STATUSES.map((s) => `
      <section class="ttb-column" data-status="${s.key}" aria-label="${s.label}">
        <div class="ttb-col-header"><div class="d-flex align-items-center gap-2">
          <span class="ttb-dot dot-${s.key}"></span><h2 class="ttb-col-title">${s.label}</h2><span class="ttb-count">0</span></div></div>
        <div class="ttb-cards" data-status="${s.key}"></div>
        ${editable ? `<button class="ttb-add" data-add="${s.key}"><i class="bi bi-plus-lg me-1"></i>Add task</button>` : ""}
      </section>`).join("");
    STATUSES.forEach((s) => renderCards(s.key));
    renderStats();
    initSortable();
  }

  /* ------------------------------------------------------------------ drag & drop */
  function initSortable() {
    sortables.forEach((s) => s.destroy());
    sortables = [];
    if (!state.perms.edit) return;
    document.querySelectorAll(".ttb-cards").forEach((el) => {
      sortables.push(Sortable.create(el, {
        group: "tasks", draggable: ".ttb-card", sort: false, animation: 150,
        ghostClass: "ttb-ghost", chosenClass: "ttb-chosen",
        forceFallback: true, fallbackOnBody: true, fallbackTolerance: 4,
        delay: 150, delayOnTouchOnly: true, touchStartThreshold: 5,
        onMove: (evt) => {
          document.querySelectorAll(".ttb-column.is-over").forEach((c) => c.classList.remove("is-over"));
          evt.to.closest(".ttb-column").classList.add("is-over");
        },
        onEnd: onDrop,
      }));
    });
  }

  async function onDrop(evt) {
    document.querySelectorAll(".ttb-column.is-over").forEach((c) => c.classList.remove("is-over"));
    lastDragEnd = Date.now();
    const task = taskById(evt.item.dataset.id);
    const from = evt.from.dataset.status, to = evt.to.dataset.status;
    if (!task || from === to) { setTimeout(() => renderCards(from)); return; }

    // optimistic update: card is already in the new column, keep state in sync and re-sort
    task.status = to;
    setTimeout(() => { renderCards(from); renderCards(to); renderStats(); flash(task.id); });
    try {
      const { task: saved } = await api("PATCH", `/api/tasks/${task.id}/status`, { status: to });
      Object.assign(task, saved);
      toast(`Moved to ${statusLabel(to)}`);
    } catch (err) {
      task.status = from;                                // roll back
      renderCards(from); renderCards(to); renderStats(); flash(task.id);
      toast(err.message || "Could not move the task.", "error");
    }
  }
  function flash(id) {
    const el = $(`.ttb-card[data-id="${id}"]`);
    if (el) { el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }
  }

  /* ------------------------------------------------------------------ task detail */
  let detailId = null;
  const detailModal = () => bootstrap.Modal.getOrCreateInstance($("#detailModal"));

  function fillDetail(t) {
    const due = dueInfo(t);
    $("#dCode").textContent = t.code;
    $("#dPriority").innerHTML = priorityBadge(t.priority);
    $("#dTitle").textContent = t.title;
    $("#dDesc").innerHTML = t.description ? esc(t.description) : `<span class="ttb-meta">No description.</span>`;
    $("#dAssignee").innerHTML = assigneeHTML(t.assigned_to, true);
    $("#dDue").innerHTML = t.deadline
      ? `<div class="fw-medium">${esc(fmtDate(t.deadline, true))}</div><span class="ttb-due ${due.cls}">${esc(due.full)}</span>` : `<span class="ttb-meta">No deadline</span>`;
    $("#dCreated").textContent = fmtDateTime(t.created_at);
    const sel = $("#dStatus");
    sel.innerHTML = STATUSES.map((s) => `<option value="${s.key}" ${s.key === t.status ? "selected" : ""}>${s.label}</option>`).join("");
    sel.disabled = !state.perms.edit;
  }
  function commentHTML(c) {
    const a = c.author || { id: 0, username: "?" };
    return `<div class="ttb-comment"><span class="ttb-avatar lg ${colorFor(a.id)}">${esc(initials(a.username))}</span>
      <div class="ttb-comment-body"><div class="fw-semibold">${esc(a.username)}<span class="ttb-comment-meta">${esc(fmtDateTime(c.created_at))}</span></div>
      <div style="white-space:pre-wrap">${esc(c.content)}</div></div></div>`;
  }
  function setCommentCount(n) { $("#dCommentCount").textContent = n; }

  async function openDetail(id) {
    const t = taskById(id);
    if (!t) return;
    detailId = t.id;
    fillDetail(t);
    $("#dComments").innerHTML = `<div class="ttb-skel" style="height:48px"></div>`;
    setCommentCount(t.comment_count);
    $("#commentForm").classList.toggle("d-none", !state.perms.edit);
    $("#dEdit").classList.toggle("d-none", !state.perms.edit);
    $("#dDeleteArea").innerHTML = canDelete(t) ? deleteButtonHTML() : "";
    clearCommentError();
    detailModal().show();
    try {
      const data = await api("GET", `/api/tasks/${t.id}`);
      if (detailId !== t.id) return;
      Object.assign(t, data.task);
      $("#dComments").innerHTML = data.comments.length ? data.comments.map(commentHTML).join("") : `<p class="ttb-meta">No comments yet.</p>`;
      setCommentCount(data.comments.length);
      $("#dDeleteArea").innerHTML = data.permissions.delete ? deleteButtonHTML() : "";
    } catch (err) {
      $("#dComments").innerHTML = `<p class="text-danger small">${esc(err.message)}</p>`;
    }
  }
  const deleteButtonHTML = () => `<button class="btn btn-ghost text-danger" data-action="ask-delete"><i class="bi bi-trash me-1"></i>Delete</button>`;

  async function changeStatusFromDetail(e) {
    const t = taskById(detailId), to = e.target.value, from = t.status;
    if (!t || to === from) return;
    e.target.disabled = true;
    try {
      const { task: saved } = await api("PATCH", `/api/tasks/${t.id}/status`, { status: to });
      Object.assign(t, saved);
      renderCards(from); renderCards(to); renderStats(); flash(t.id);
      fillDetail(t);
      toast(`Moved to ${statusLabel(to)}`);
    } catch (err) {
      e.target.value = from;
      toast(err.message, "error");
    } finally { e.target.disabled = !state.perms.edit; }
  }

  function clearCommentError() { $("#commentInput").classList.remove("is-invalid"); $("#commentError").textContent = ""; }
  async function submitComment(e) {
    e.preventDefault();
    const input = $("#commentInput"), text = input.value.trim(), btn = $("#commentBtn");
    clearCommentError();
    if (!text) { input.classList.add("is-invalid"); $("#commentError").textContent = "Comment cannot be empty."; input.focus(); return; }
    setBusy(btn, true, "Posting");
    try {
      const { comment } = await api("POST", `/api/tasks/${detailId}/comments`, { content: text });
      const t = taskById(detailId);
      const box = $("#dComments");
      if (!box.querySelector(".ttb-comment")) box.innerHTML = "";
      box.insertAdjacentHTML("beforeend", commentHTML(comment));
      t.comment_count += 1; setCommentCount(t.comment_count);
      input.value = "";
    } catch (err) {
      input.classList.add("is-invalid");
      $("#commentError").textContent = (err.errors.content || [err.message])[0];
    } finally { setBusy(btn, false); }
  }

  function askDelete() {
    $("#dDeleteArea").innerHTML = `<span class="small me-2">Delete this task?</span>
      <button class="btn btn-secondary btn-sm me-1" data-action="cancel-delete">Cancel</button>
      <button class="btn btn-danger btn-sm" data-action="confirm-delete">Yes, delete</button>`;
  }
  async function confirmDelete(btn) {
    const t = taskById(detailId);
    setBusy(btn, true, "Deleting");
    try {
      await api("DELETE", `/api/tasks/${t.id}`);
      state.tasks = state.tasks.filter((x) => x.id !== t.id);
      detailModal().hide();
      renderCards(t.status); renderStats();
      toast("Task deleted");
    } catch (err) {
      toast(err.message, "error");
      $("#dDeleteArea").innerHTML = canDelete(t) ? deleteButtonHTML() : "";
    }
  }

  /* ------------------------------------------------------------------ create / edit form */
  let editingId = null;
  const formModal = () => bootstrap.Modal.getOrCreateInstance($("#formModal"));
  const F = { title: $("#fTitle"), description: $("#fDescription"), status: $("#fStatus"), priority: $("#fPriority"), assigned_to: $("#fAssignee"), deadline: $("#fDeadline") };

  function clearFormErrors() {
    $("#formAlert").classList.add("d-none");
    Object.values(F).forEach((el) => { el.classList.remove("is-invalid"); const fb = el.parentElement.querySelector(".invalid-feedback"); if (fb) fb.textContent = ""; });
  }
  function showFieldErrors(errors) {
    let first = null;
    for (const [name, msgs] of Object.entries(errors || {})) {
      const el = F[name]; if (!el) continue;
      el.classList.add("is-invalid");
      el.parentElement.querySelector(".invalid-feedback").textContent = msgs[0];
      first = first || el;
    }
    if (first) first.focus();
    return !!first;
  }
  function validateClient() {
    const errors = {}, title = F.title.value.trim();
    if (!title) errors.title = ["Title is required."];
    else if (title.length > 200) errors.title = ["Title must be 200 characters or fewer."];
    if (F.description.value.length > 2000) errors.description = ["Description must be 2000 characters or fewer."];
    if (F.deadline.value && !/^\d{4}-\d{2}-\d{2}$/.test(F.deadline.value)) errors.deadline = ["Enter a valid date."];
    return errors;
  }
  function openForm(task, defaultStatus) {
    editingId = task ? task.id : null;
    clearFormErrors();
    $("#formTitle").textContent = task ? "Edit Task" : "Create Task";
    $("#formSubmit").textContent = task ? "Save changes" : "Create Task";
    F.assigned_to.innerHTML = `<option value="">Unassigned</option>` +
      state.members.filter((m) => m.role !== "viewer").map((m) => `<option value="${m.id}">${esc(m.username)}</option>`).join("");
    F.title.value = task ? task.title : "";
    F.description.value = task ? task.description : "";
    F.status.value = task ? task.status : defaultStatus || "todo";
    F.priority.value = task ? task.priority : "medium";
    F.assigned_to.value = task && task.assigned_to ? String(task.assigned_to) : "";
    F.deadline.value = task && task.deadline ? task.deadline : "";
    $("#fTitleCount").textContent = `${F.title.value.length}/200`;
    formModal().show();
  }
  async function submitForm(e) {
    e.preventDefault();
    clearFormErrors();
    const local = validateClient();
    if (showFieldErrors(local)) return;
    const payload = {
      title: F.title.value.trim(), description: F.description.value.trim(), status: F.status.value, priority: F.priority.value,
      deadline: F.deadline.value || null, assigned_to: F.assigned_to.value ? Number(F.assigned_to.value) : null,
    };
    const btn = $("#formSubmit");
    setBusy(btn, true, "Saving");
    try {
      if (editingId) {
        const t = taskById(editingId), old = t.status;
        const { task } = await api("PUT", `/api/tasks/${editingId}`, payload);
        Object.assign(t, task);
        renderCards(old); if (old !== t.status) renderCards(t.status);
        renderStats(); flash(t.id);
        toast("Task updated");
        if (detailId === t.id) fillDetail(t);
      } else {
        const { task } = await api("POST", `/api/boards/${BOARD_ID}/tasks`, payload);
        state.tasks.push(task);
        renderCards(task.status); renderStats(); flash(task.id);
        toast("Task created");
      }
      formModal().hide();
    } catch (err) {
      if (err.status === 422 && showFieldErrors(err.errors)) { /* field errors shown */ }
      else { const a = $("#formAlert"); a.textContent = err.message; a.classList.remove("d-none"); }
    } finally { setBusy(btn, false); }
  }

  /* ------------------------------------------------------------------ init */
  async function load() {
    try {
      const data = await api("GET", `/api/boards/${BOARD_ID}`);
      Object.assign(state, { board: data.board, role: data.role, perms: data.permissions, me: data.me, members: data.members, tasks: data.tasks });
      $("#memberStack").innerHTML = state.members.map((m) => `<span class="ttb-avatar ${colorFor(m.id)}" title="${esc(m.username)} (${esc(m.role)})">${esc(initials(m.username))}</span>`).join("");
      $("#filterMember").insertAdjacentHTML("beforeend", state.members.map((m) => `<option value="${m.id}">${esc(m.username)}</option>`).join(""));
      renderBoard();
    } catch (err) {
      $("#board").innerHTML = `<div class="ttb-error-state"><i class="bi bi-exclamation-triangle display-6"></i>
        <p class="mt-2">${esc(err.message)}</p><button class="btn btn-secondary btn-sm" id="retry">Try again</button></div>`;
      $("#retry").addEventListener("click", () => location.reload());
    }
  }

  function bind() {
    $("#board").addEventListener("click", (e) => {
      const add = e.target.closest("[data-add]");
      if (add) return openForm(null, add.dataset.add);
      const card = e.target.closest(".ttb-card");
      if (card && Date.now() - lastDragEnd > 250) openDetail(card.dataset.id);
    });
    $("#board").addEventListener("keydown", (e) => {
      const card = e.target.closest(".ttb-card");
      if (card && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openDetail(card.dataset.id); }
    });
    const add = $("#btnAdd"); if (add) add.addEventListener("click", () => openForm(null, "todo"));
    $("#dStatus").addEventListener("change", changeStatusFromDetail);
    $("#commentForm").addEventListener("submit", submitComment);
    $("#commentInput").addEventListener("input", clearCommentError);
    $("#dEdit").addEventListener("click", () => {
      const t = taskById(detailId);
      detailModal().hide();
      $("#detailModal").addEventListener("hidden.bs.modal", () => openForm(t), { once: true });
    });
    $("#dFooter").addEventListener("click", (e) => {
      const b = e.target.closest("[data-action]"); if (!b) return;
      if (b.dataset.action === "ask-delete") askDelete();
      if (b.dataset.action === "cancel-delete") $("#dDeleteArea").innerHTML = deleteButtonHTML();
      if (b.dataset.action === "confirm-delete") confirmDelete(b);
    });
    $("#detailModal").addEventListener("hidden.bs.modal", () => { detailId = null; });
    $("#taskForm").addEventListener("submit", submitForm);
    F.title.addEventListener("input", () => { $("#fTitleCount").textContent = `${F.title.value.length}/200`; F.title.classList.remove("is-invalid"); });
    $("#formModal").addEventListener("shown.bs.modal", () => F.title.focus());

    const refilter = () => { STATUSES.forEach((s) => renderCards(s.key)); };
    $("#filterSearch").addEventListener("input", (e) => { filters.q = e.target.value.toLowerCase().trim(); refilter(); });
    $("#filterMember").addEventListener("change", (e) => { filters.member = e.target.value; refilter(); });
    $("#filterPriority").addEventListener("change", (e) => { filters.priority = e.target.value; refilter(); });
    $("#filterReset").addEventListener("click", () => {
      Object.assign(filters, { q: "", member: "all", priority: "all" });
      $("#filterSearch").value = ""; $("#filterMember").value = "all"; $("#filterPriority").value = "all"; refilter();
    });
  }

  document.addEventListener("DOMContentLoaded", () => { bind(); load(); });
})();
