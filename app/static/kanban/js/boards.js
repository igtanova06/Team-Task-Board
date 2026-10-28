/* Board management UI: board list, create / edit / delete board, board switcher, member management.
   Everything talks to the JSON API with fetch (AJAX):
     GET/POST /api/boards          GET/PATCH/DELETE /api/boards/<id>
     POST /api/boards/<id>/members            PATCH/DELETE /api/boards/<id>/members/<user_id>
   Loaded on every signed-in page (from base.html). */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cap = (s) => String(s || "").charAt(0).toUpperCase() + String(s || "").slice(1);
  const csrfMeta = $('meta[name="csrf-token"]');
  const CSRF = csrfMeta ? csrfMeta.content : "";
  const ME = Number(document.body.dataset.userId);
  const PAGE_BOARD_ID = document.body.dataset.boardId ? Number(document.body.dataset.boardId) : null;
  const AVATAR_COLORS = ["av-owner", "av-sky", "av-indigo", "av-teal"];
  const colorFor = (id) => AVATAR_COLORS[(id || 0) % AVATAR_COLORS.length];
  const initials = (n) => esc(String(n || "?").slice(0, 2).toUpperCase());
  const emit = (name, detail) => window.dispatchEvent(new CustomEvent(name, { detail }));

  /* ------------------------------------------------------------------ fetch wrapper */
  class ApiError extends Error {
    constructor(status, body) { super((body && body.detail) || "Request failed."); this.status = status; this.errors = (body && body.errors) || {}; }
  }
  async function api(method, url, body) {
    let res;
    try {
      res = await fetch(url, {
        method, credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json", "X-CSRFToken": CSRF },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (e) { throw new ApiError(0, { detail: "Network error. Check your connection and try again." }); }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON */ }
    if (res.status === 401) { location.href = "/login?next=" + encodeURIComponent(location.pathname); throw new ApiError(401, data); }
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
  }
  const firstError = (err) => { const f = Object.values(err.errors || {}).flat(); return f.length ? f[0] : err.message; };

  function toast(message, type = "success") {
    const box = $("#toasts"); if (!box) return;
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${type === "error" ? "danger" : "dark"} border-0`;
    el.setAttribute("role", type === "error" ? "alert" : "status");
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${esc(message)}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
    box.appendChild(el);
    el.addEventListener("hidden.bs.toast", () => el.remove());
    new bootstrap.Toast(el, { delay: type === "error" ? 5000 : 2500 }).show();
  }
  function setBusy(btn, busy, label) {
    if (busy) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>${label || ""}`; }
    else { btn.disabled = false; if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
  }
  // a toast that must survive a redirect
  function flashNext(msg) { try { sessionStorage.setItem("ttb_flash", msg); } catch (e) { /* ignore */ } }
  function showFlash() { try { const m = sessionStorage.getItem("ttb_flash"); if (m) { sessionStorage.removeItem("ttb_flash"); toast(m); } } catch (e) { /* ignore */ } }

  /* ------------------------------------------------------------------ create / edit / delete board modal */
  const bm = {
    el: $("#boardModal"), form: $("#boardForm"), name: $("#bName"), desc: $("#bDescription"),
    alert: $("#boardFormAlert"), submit: $("#boardSubmit"), title: $("#boardModalTitle"),
    danger: $("#boardDangerZone"), delArea: $("#boardDeleteArea"), count: $("#bNameCount"),
  };
  let editing = null;                                   // null = creating, else the board being edited
  const bmModal = () => bootstrap.Modal.getOrCreateInstance(bm.el);

  function clearBoardErrors() {
    bm.alert.classList.add("d-none");
    [bm.name, bm.desc].forEach((f) => { f.classList.remove("is-invalid"); f.nextElementSibling.textContent = ""; });
  }
  function fieldError(input, msg) { input.classList.add("is-invalid"); input.nextElementSibling.textContent = msg; }
  function showBoardErrors(err) {
    const e = err.errors || {}; let shown = false;
    if (e.name) { fieldError(bm.name, e.name[0]); shown = true; }
    if (e.description) { fieldError(bm.desc, e.description[0]); shown = true; }
    if (!shown) { bm.alert.textContent = err.message; bm.alert.classList.remove("d-none"); }
  }
  const deleteButton = () => `<button type="button" class="btn btn-secondary text-danger btn-sm" data-act="ask"><i class="bi bi-trash me-1"></i>Delete this board…</button>`;

  function openBoardModal(board) {
    editing = board || null;
    clearBoardErrors();
    bm.title.textContent = editing ? "Board settings" : "New board";
    bm.submit.textContent = editing ? "Save changes" : "Create board";
    bm.name.value = editing ? editing.name : ""; bm.desc.value = editing ? (editing.description || "") : "";
    bm.count.textContent = `${bm.name.value.length}/100`;
    bm.danger.classList.toggle("d-none", !editing);
    bm.delArea.innerHTML = editing ? deleteButton() : "";
    bmModal().show();
  }
  function validateBoardClient() {
    const name = bm.name.value.trim();
    if (!name) { fieldError(bm.name, "Board name is required."); return false; }
    if (name.length > 100) { fieldError(bm.name, "Board name must be 100 characters or fewer."); return false; }
    return true;
  }
  async function submitBoard(e) {
    e.preventDefault(); clearBoardErrors();
    if (!validateBoardClient()) return bm.name.focus();
    const payload = { name: bm.name.value.trim(), description: bm.desc.value.trim() };
    setBusy(bm.submit, true, editing ? "Saving…" : "Creating…");
    try {
      if (editing) {
        const b = await api("PATCH", `/api/boards/${editing.id}`, payload);
        bmModal().hide(); toast("Board updated."); emit("ttb:board-saved", b);
      } else {
        const b = await api("POST", "/api/boards", payload);
        flashNext(`Board “${b.name}” created.`);
        location.href = `/boards/${b.id}`;
        return;
      }
    } catch (err) { showBoardErrors(err); }
    finally { setBusy(bm.submit, false); }
  }
  async function deleteBoard(btn) {
    setBusy(btn, true, "Deleting…");
    try {
      await api("DELETE", `/api/boards/${editing.id}`);
      const id = editing.id; bmModal().hide();
      emit("ttb:board-deleted", { id });
      if (PAGE_BOARD_ID === id) { flashNext("Board deleted."); location.href = "/boards"; }
      else toast("Board deleted.");
    } catch (err) {
      setBusy(btn, false); bm.alert.textContent = err.message; bm.alert.classList.remove("d-none");
    }
  }
  function bindBoardModal() {
    if (!bm.el) return;
    bm.form.addEventListener("submit", submitBoard);
    bm.name.addEventListener("input", () => { bm.count.textContent = `${bm.name.value.length}/100`; bm.name.classList.remove("is-invalid"); });
    bm.el.addEventListener("shown.bs.modal", () => bm.name.focus());
    bm.delArea.addEventListener("click", (e) => {
      const b = e.target.closest("[data-act]"); if (!b) return;
      if (b.dataset.act === "ask") {
        bm.delArea.innerHTML = `<p class="small mb-2">Delete <strong>${esc(editing.name)}</strong> with all its tasks, comments and memberships? This cannot be undone.</p>
          <div class="d-flex gap-2"><button type="button" class="btn btn-ghost btn-sm" data-act="cancel">Keep board</button>
          <button type="button" class="btn btn-danger btn-sm" data-act="confirm">Yes, delete board</button></div>`;
      }
      if (b.dataset.act === "cancel") bm.delArea.innerHTML = deleteButton();
      if (b.dataset.act === "confirm") deleteBoard(b);
    });
  }

  /* ------------------------------------------------------------------ navbar board switcher */
  async function loadSwitcher() {
    const menu = $("#boardSwitcherMenu"); if (!menu) return;
    try {
      const boards = await api("GET", "/api/boards");
      menu.innerHTML = boards.map((b) => `<li><a class="dropdown-item ${b.id === PAGE_BOARD_ID ? "active" : ""}" href="/boards/${b.id}">
          <span class="text-truncate">${esc(b.name)}</span><span class="badge-role badge-role-${esc(b.role)}">${esc(cap(b.role))}</span></a></li>`).join("")
        + (boards.length ? '<li><hr class="dropdown-divider"></li>' : "")
        + `<li><a class="dropdown-item" href="/boards"><span><i class="bi bi-grid me-2"></i>All boards</span></a></li>
           <li><button class="dropdown-item" type="button" id="switcherNew"><span><i class="bi bi-plus-lg me-2"></i>New board</span></button></li>`;
      $("#switcherNew").addEventListener("click", () => openBoardModal(null));
    } catch (err) { menu.innerHTML = `<li class="px-3 py-2 text-danger small">${esc(err.message)}</li>`; }
  }

  /* ------------------------------------------------------------------ board list page */
  const list = { boards: [], q: "" };
  function relTime(iso) {
    if (!iso) return "";
    const d = new Date(iso), days = Math.floor((Date.now() - d.getTime()) / 86400000);
    if (days <= 0) return "today"; if (days === 1) return "yesterday";
    return days < 30 ? `${days} days ago` : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  function cardHTML(b) {
    const owner = b.role === "owner";
    const menu = `<div class="dropdown ttb-card-menu">
        <button class="btn btn-ghost btn-sm px-2" data-bs-toggle="dropdown" aria-expanded="false" aria-label="Actions for ${esc(b.name)}"><i class="bi bi-three-dots"></i></button>
        <ul class="dropdown-menu dropdown-menu-end shadow-sm">
          ${owner ? `<li><button class="dropdown-item" data-act="edit" data-id="${b.id}"><i class="bi bi-pencil me-2"></i>Rename / edit</button></li>` : ""}
          <li><button class="dropdown-item" data-act="leave" data-id="${b.id}"><i class="bi bi-box-arrow-left me-2"></i>Leave board</button></li>
          ${owner ? `<li><hr class="dropdown-divider"></li><li><button class="dropdown-item text-danger" data-act="delete" data-id="${b.id}"><i class="bi bi-trash me-2"></i>Delete board</button></li>` : ""}
        </ul></div>`;
    return `<article class="ttb-board-card" data-id="${b.id}">
      <div class="d-flex align-items-start justify-content-between gap-2">
        <a class="stretched-link text-break" href="/boards/${b.id}">${esc(b.name)}</a>${menu}
      </div>
      <div><span class="badge-role badge-role-${esc(b.role)}">${esc(cap(b.role))}</span></div>
      <div class="ttb-desc">${b.description ? esc(b.description) : '<span class="fst-italic">No description</span>'}</div>
      <div class="ttb-board-foot"><span><i class="bi bi-list-task me-1"></i>${b.task_count} task${b.task_count === 1 ? "" : "s"}</span>
        <span><i class="bi bi-people me-1"></i>${b.member_count} member${b.member_count === 1 ? "" : "s"}</span>
        <span class="ms-auto">Updated ${esc(relTime(b.updated_at))}</span></div>
    </article>`;
  }
  function renderList() {
    const grid = $("#boardGrid"), q = list.q;
    const shown = list.boards.filter((b) => !q || b.name.toLowerCase().includes(q));
    $("#boardsSummary").textContent = `${list.boards.length} board${list.boards.length === 1 ? "" : "s"} · ${list.boards.filter((b) => b.role === "owner").length} owned by you`;
    if (!list.boards.length) {
      grid.innerHTML = `<div class="ttb-empty"><i class="bi bi-kanban display-5 text-primary"></i>
        <h2 class="h6 fw-bold mt-2 text-body">You are not on any board yet</h2>
        <p class="mb-3">Create your first board, or ask a board owner to add you. Empty database? Run <code>python seed.py</code> and sign in as <code>alex</code>.</p>
        <button class="btn btn-primary" data-act="new"><i class="bi bi-plus-lg me-1"></i>Create board</button></div>`;
    } else if (!shown.length) {
      grid.innerHTML = `<div class="ttb-empty">No board matches “${esc(q)}”.</div>`;
    } else grid.innerHTML = shown.map(cardHTML).join("");
  }
  async function loadList() {
    try { list.boards = await api("GET", "/api/boards"); renderList(); }
    catch (err) {
      $("#boardGrid").innerHTML = `<div class="ttb-empty"><i class="bi bi-exclamation-triangle display-6"></i><p class="mt-2">${esc(err.message)}</p>
        <button class="btn btn-secondary btn-sm" id="listRetry">Try again</button></div>`;
      $("#listRetry").addEventListener("click", loadList);
    }
  }
  async function leaveBoard(b) {
    if (!window.confirm(`Leave “${b.name}”? Tasks assigned to you will become unassigned.`)) return;
    try {
      await api("DELETE", `/api/boards/${b.id}/members/${ME}`);
      list.boards = list.boards.filter((x) => x.id !== b.id); renderList(); loadSwitcher(); toast("You left the board.");
    } catch (err) { toast(err.message, "error"); }
  }
  function initListPage() {
    $("#btnNewBoard").addEventListener("click", () => openBoardModal(null));
    $("#boardSearch").addEventListener("input", (e) => { list.q = e.target.value.toLowerCase().trim(); renderList(); });
    $("#boardGrid").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-act]"); if (!btn) return;
      if (btn.dataset.act === "new") return openBoardModal(null);
      const b = list.boards.find((x) => x.id === Number(btn.dataset.id)); if (!b) return;
      if (btn.dataset.act === "edit") openBoardModal(b);
      if (btn.dataset.act === "leave") leaveBoard(b);
      if (btn.dataset.act === "delete") { openBoardModal(b); bm.delArea.querySelector("[data-act=ask]").click(); }
    });
    window.addEventListener("ttb:board-saved", loadList);
    window.addEventListener("ttb:board-deleted", (e) => { list.boards = list.boards.filter((b) => b.id !== e.detail.id); renderList(); });
    loadList();
  }

  /* ------------------------------------------------------------------ board page: settings + members */
  const mm = { el: $("#membersModal"), list: $("#memberList"), count: $("#membersCount"), invite: $("#inviteForm"), err: $("#inviteError") };
  const mstate = { role: null, members: [] };
  const mModal = () => bootstrap.Modal.getOrCreateInstance(mm.el);
  const isOwner = () => mstate.role === "owner";
  let pendingRemove = null, pendingTimer = null;

  function memberRow(m) {
    const self = m.id === ME;
    const roleCell = isOwner()
      ? `<select class="form-select form-select-sm" data-act="role" data-id="${m.id}" aria-label="Role of ${esc(m.username)}">
          ${["owner", "member", "viewer"].map((r) => `<option value="${r}" ${m.role === r ? "selected" : ""}>${cap(r)}</option>`).join("")}</select>`
      : `<span class="badge-role badge-role-${esc(m.role)}">${esc(cap(m.role))}</span>`;
    let action = "";
    if (self) action = `<button class="btn btn-ghost btn-sm text-danger" data-act="remove" data-id="${m.id}"><i class="bi bi-box-arrow-left me-1"></i>Leave</button>`;
    else if (isOwner()) action = `<button class="btn btn-ghost btn-sm text-danger" data-act="remove" data-id="${m.id}" aria-label="Remove ${esc(m.username)}"><i class="bi bi-trash"></i></button>`;
    return `<li data-id="${m.id}"><span class="ttb-avatar lg ${colorFor(m.id)}">${initials(m.username)}</span>
      <div class="who"><div class="fw-semibold">${esc(m.username)}${self ? ' <span class="ttb-meta fw-normal">(you)</span>' : ""}</div><div class="ttb-meta">${esc(m.email || "")}</div></div>
      ${roleCell}${action}</li>`;
  }
  function renderMembers() {
    mm.count.textContent = mstate.members.length;
    mm.list.innerHTML = mstate.members.map(memberRow).join("");
    mm.invite.classList.toggle("d-none", !isOwner());
  }
  async function loadMembers() {
    mm.list.innerHTML = '<li class="ttb-meta">Loading…</li>';
    try {
      const info = await api("GET", `/api/boards/${PAGE_BOARD_ID}`);
      mstate.role = info.role; mstate.members = info.members; renderMembers();
    } catch (err) { mm.list.innerHTML = `<li class="text-danger">${esc(err.message)}</li>`; }
  }
  const membersChanged = () => emit("ttb:members-changed", { members: mstate.members });

  async function changeRole(sel) {
    const uid = Number(sel.dataset.id), m = mstate.members.find((x) => x.id === uid), prev = m.role;
    sel.disabled = true;
    try {
      const r = await api("PATCH", `/api/boards/${PAGE_BOARD_ID}/members/${uid}`, { role: sel.value });
      m.role = r.role; toast(`${m.username} is now ${cap(m.role)}.`);
      if (uid === ME) { location.reload(); return; }          // my own permissions changed
      renderMembers(); membersChanged();
    } catch (err) { sel.value = prev; sel.disabled = false; toast(firstError(err), "error"); }
  }
  async function removeMember(btn) {
    const uid = Number(btn.dataset.id), m = mstate.members.find((x) => x.id === uid);
    if (pendingRemove !== uid) {                                // two-step confirm on the button itself
      pendingRemove = uid; clearTimeout(pendingTimer);
      btn.classList.replace("btn-ghost", "btn-danger"); btn.classList.remove("text-danger");
      btn.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>Confirm`;
      pendingTimer = setTimeout(() => { pendingRemove = null; renderMembers(); }, 4000);
      return;
    }
    pendingRemove = null; clearTimeout(pendingTimer); btn.disabled = true;
    try {
      await api("DELETE", `/api/boards/${PAGE_BOARD_ID}/members/${uid}`);
      if (uid === ME) { flashNext("You left the board."); location.href = "/boards"; return; }
      mstate.members = mstate.members.filter((x) => x.id !== uid);
      renderMembers(); toast(`${m.username} removed. Their tasks are now unassigned.`); membersChanged();
    } catch (err) { btn.disabled = false; renderMembers(); toast(firstError(err), "error"); }
  }
  async function inviteMember(e) {
    e.preventDefault();
    const input = $("#inviteIdentity"), btn = $("#inviteBtn"), identity = input.value.trim();
    mm.err.classList.add("d-none"); input.classList.remove("is-invalid");
    if (!identity) { input.classList.add("is-invalid"); mm.err.textContent = "Enter a username or email."; mm.err.classList.remove("d-none"); return input.focus(); }
    setBusy(btn, true, "Inviting…");
    try {
      const r = await api("POST", `/api/boards/${PAGE_BOARD_ID}/members`, { identity, role: $("#inviteRole").value });
      mstate.members.push({ id: r.user_id, username: r.username, email: r.email, role: r.role });
      renderMembers(); input.value = ""; toast(`${r.username} added as ${cap(r.role)}.`); membersChanged();
    } catch (err) {
      input.classList.add("is-invalid");
      mm.err.textContent = err.status === 404 ? "No user with that username or email." : firstError(err);
      mm.err.classList.remove("d-none");
    } finally { setBusy(btn, false); }
  }
  async function openSettings() {
    try { const info = await api("GET", `/api/boards/${PAGE_BOARD_ID}`); openBoardModal(info.board); }
    catch (err) { toast(err.message, "error"); }
  }
  function initBoardPage() {
    const set = $("#btnBoardSettings"); if (set) set.addEventListener("click", openSettings);
    const open = () => { pendingRemove = null; mm.err.classList.add("d-none"); mModal().show(); loadMembers(); };
    $("#btnMembers").addEventListener("click", open);
    $("#memberStack").addEventListener("click", open);
    mm.invite.addEventListener("submit", inviteMember);
    $("#inviteIdentity").addEventListener("input", (e) => { e.target.classList.remove("is-invalid"); mm.err.classList.add("d-none"); });
    mm.list.addEventListener("change", (e) => { if (e.target.dataset.act === "role") changeRole(e.target); });
    mm.list.addEventListener("click", (e) => { const b = e.target.closest("[data-act=remove]"); if (b) removeMember(b); });
    window.addEventListener("ttb:board-saved", (e) => {
      const n = $("#boardName"); if (n) n.textContent = e.detail.name;
      document.title = `${e.detail.name} · Team Task Board`; loadSwitcher();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindBoardModal(); loadSwitcher(); showFlash();
    window.addEventListener("ttb:board-saved", loadSwitcher);
    window.addEventListener("ttb:board-deleted", loadSwitcher);
    if (document.body.dataset.page === "boards") initListPage();
    if (PAGE_BOARD_ID && mm.el) initBoardPage();
  });
})();
