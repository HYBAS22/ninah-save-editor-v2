"use strict";
let S = { ctl: null, ctlShort: "", data: null, kind: "" };

const $ = id => document.getElementById(id);
function toast(msg, cls) {
  const d = document.createElement("div");
  d.className = "toast " + (cls || "");
  d.textContent = msg;
  $("toast").appendChild(d);
  setTimeout(() => d.remove(), 6000);
}
async function api(path, body) {
  const o = { headers: { "Content-Type": "application/json" } };
  let r;
  if (body === undefined) r = await fetch(path);
  else { o.method = "POST"; o.body = JSON.stringify(body); r = await fetch(path, o); }
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || ("http " + r.status));
  return j;
}

function renderVerify(v) {
  const el = $("verify");
  if (!v) { el.textContent = "no file open"; return; }
  const sync = v.synced ? v.synced.length : 0, div = v.diverged ? v.diverged.length : 0;
  el.innerHTML = "decrypt/json <b class='ok'>OK</b> · synced <b class='ok'>" + sync +
    "</b> · stale <b class='warn'>" + div + "</b>" +
    (v.notes ? " · " + v.notes.map(n => n.replace(/</g, "&lt;")).join(" · ") : "");
}

async function refresh() {
  const st = await api("/api/state");
  $("ver").textContent = "v" + (st.version || "");
  const fp = $("filepick");
  fp.innerHTML = "";
  (st.files || []).forEach(f => {
    const o = document.createElement("option");
    o.value = f.path;
    const d = new Date(f.mtime * 1000);
    o.textContent = "[" + f.kind + "] " + f.path + " (" + f.size + "b, " + d.toLocaleString() + ")";
    fp.appendChild(o);
  });
  if (st.open) {
    if ([...fp.options].some(o => o.value === st.path)) fp.value = st.path;
    S.kind = st.kind;
    renderVerify(st.verify);
    const q = $("ctlsearch").value.toLowerCase();
    const ul = $("ctllist"); ul.innerHTML = "";
    st.controllers.forEach(c => {
      if (q && c.name.toLowerCase().indexOf(q) < 0) return;
      const li = document.createElement("li");
      li.textContent = c.name + " (" + c.fields.length + ")";
      if (c.dirty) { const s = document.createElement("span"); s.className = "dot"; s.textContent = "●"; li.appendChild(s); }
      if (c.short === S.ctlShort) li.classList.add("sel");
      li.onclick = () => openController(c.short, c.name);
      ul.appendChild(li);
    });
  } else {
    $("ctllist").innerHTML = "<li>open a save file ↑</li>";
    renderVerify(null);
  }
  loadSnaps();
  return st;
}

async function openController(short, name) {
  S.ctlShort = short; S.ctl = name;
  $("ctltitle").textContent = name;
  $("rawwrap").classList.add("hidden");
  const r = await api("/api/node?controller=" + encodeURIComponent(short) +
    (S.kind === "meta" ? "&path=" : ""));
  S.data = r.value;
  renderTree();
  refreshSidebarSel();
}
function refreshSidebarSel() {
  [...$("ctllist").children].forEach(li => {
    li.classList.toggle("sel", li.textContent.indexOf(S.ctl) === 0);
  });
}

function pathJoin(base, key) { return base ? base + "." + key : key; }
window.addEventListener("unhandledrejection", e => toast(String(e.reason || e), "err"));

function renderTree() {
  const root = $("tree"); root.innerHTML = "";
  const q = $("leafsearch").value.toLowerCase();
  root.appendChild(renderNode(S.data, "", 0, q));
}
function matchQ(key, full, q) {
  return !q || key.toLowerCase().indexOf(q) >= 0 || full.toLowerCase().indexOf(q) >= 0;
}

function renderNode(val, path, depth, q) {
  if (val !== null && typeof val === "object") {
    const isArr = Array.isArray(val);
    const keys = isArr ? val.map((_, i) => i) : Object.keys(val).filter(k => k !== "$type");
    const wrap = document.createElement("div"); wrap.className = "node";
    const head = document.createElement("div"); head.className = "head";
    const label = path === "" ? "(root)" : path.split(".").pop();
    head.textContent = (isArr ? "▸ " : "▸ ") + label + (isArr ? " [" + val.length + "]" : " {" + keys.length + "}");
    const body = document.createElement("div"); body.className = "body"; body.style.display = "none";
    head.onclick = () => { body.style.display = body.style.display === "none" ? "" : "none"; };
    if (depth < 1) body.style.display = "";
    if (isArr) {
      const bar = document.createElement("div"); bar.className = "arrbar";
      const add = document.createElement("button"); add.textContent = "+ add item";
      add.onclick = async () => {
        const cur = await getVal(path);
        const sample = cur.find(x => x !== null && x !== undefined);
        const nv = sample === undefined ? null : JSON.parse(JSON.stringify(sample));
        cur.push(nv === undefined ? null : nv);
        await setVal(path, cur); await reloadNode();
      };
      bar.appendChild(add); body.appendChild(bar);
    }
    keys.forEach(k => {
      const kp = isArr ? path + "[" + k + "]" : pathJoin(path, k);
      const child = renderNode(val[k], kp, depth + 1, q);
      if (!q || child.dataset.hit === "1") { body.appendChild(child); wrap.dataset.hit = "1"; }
    });
    // raw edit for this container
    const bar = document.createElement("div"); bar.className = "arrbar";
    const raw = document.createElement("button"); raw.textContent = "{} raw edit";
    raw.onclick = () => rawEditNode(path);
    bar.appendChild(raw); body.appendChild(bar);
    wrap.appendChild(head); wrap.appendChild(body);
    if (path === "" || !q) wrap.dataset.hit = "1";
    return wrap;
  }
  // leaf
  const row = document.createElement("div"); row.className = "leaf";
  const key = path.split(".").pop();
  if (!matchQ(key, path, q)) { row.dataset.hit = "0"; row.style.display = "none"; }
  else row.dataset.hit = "1";
  const k = document.createElement("span"); k.className = "k"; k.textContent = key; k.title = path;
  const t = document.createElement("span"); t.className = "t";
  let input;
  if (typeof val === "boolean") {
    t.textContent = "bool";
    input = document.createElement("input"); input.type = "checkbox"; input.checked = val;
    input.onchange = () => setVal(path, input.checked).then(afterSet);
  } else if (typeof val === "number") {
    t.textContent = Number.isInteger(val) ? "int" : "float";
    input = document.createElement("input");
    input.type = "number"; input.value = val;
    if (!Number.isInteger(val)) input.step = "any";
    input.onchange = () => {
      const n = Number(input.value);
      if (Number.isNaN(n)) { toast("not a number", "err"); return; }
      setVal(path, n).then(afterSet);
    };
  } else {
    t.textContent = val === null ? "null" : "str";
    input = document.createElement("input"); input.type = "text";
    input.value = val === null ? "" : val;
    input.placeholder = val === null ? "null" : "";
    input.onchange = () => setVal(path, input.value).then(afterSet);
  }
  row.appendChild(k); row.appendChild(input); row.appendChild(t);
  const wrap = document.createElement("div"); wrap.appendChild(row);
  wrap.dataset.hit = row.dataset.hit;
  return wrap;
}

async function getVal(path) {
  const r = await api("/api/node?controller=" + encodeURIComponent(S.ctlShort) +
    "&path=" + encodeURIComponent(path));
  return r.value;
}
async function setVal(path, value) {
  return api("/api/set", { controller: S.ctlShort, path: path, value: value });
}
async function afterSet(r) {
  if (r && r.verify) renderVerify(r.verify);
  const st = await api("/api/state"); renderVerify(st.verify);
}
async function reloadNode() {
  const r = await api("/api/node?controller=" + encodeURIComponent(S.ctlShort));
  S.data = r.value; renderTree();
}
function rawEditNode(path) {
  getVal(path).then(v => {
    const nv = prompt("Raw JSON for " + (path || "(root)") + ":", JSON.stringify(v));
    if (nv === null) return;
    let parsed;
    try { parsed = JSON.parse(nv); }
    catch (e) { toast("bad JSON: " + e.message, "err"); return; }
    setVal(path, parsed).then(r => { toast("raw applied · " + r.sync, "ok"); reloadNode(); })
      .catch(e => toast(String(e), "err"));
  });
}

$("openbtn").onclick = async () => {
  try { await api("/api/open", { path: $("filepick").value }); S.ctlShort = ""; $("tree").innerHTML = ""; await refresh(); }
  catch (e) { toast(String(e), "err"); }
};
$("reloadbtn").onclick = async () => {
  try { await api("/api/reload", {}); S.ctlShort = ""; $("tree").innerHTML = ""; await refresh(); toast("reloaded, changes discarded", "ok"); }
  catch (e) { toast(String(e), "err"); }
};
async function loadSnaps() {
  try {
    const r = await api("/api/restores");
    const s = $("snaplist"); s.innerHTML = "";
    (r.snaps || []).forEach(x => {
      const o = document.createElement("option");
      o.value = x.name; o.textContent = x.name + (x.label ? " — " + x.label : "");
      s.appendChild(o);
    });
  } catch (e) { /* ignore */ }
}
$("snapbtn").onclick = async () => {
  try {
    const r = await api("/api/backup", {});
    toast("snapshot saved", "ok"); loadSnaps();
  } catch (e) { toast(String(e), "err"); }
};
$("restorebtn").onclick = async () => {
  const name = $("snaplist").value;
  if (!name) { toast("no snapshot selected", "err"); return; }
  if (!confirm("Restore snapshot " + name + "? Current state will be overwritten (a backup is taken first by publish flow).")) return;
  try {
    const r = await api("/api/restore", { name: name });
    toast("restored " + name, "ok");
    if (r.verify) renderVerify(r.verify);
    S.ctlShort = ""; $("tree").innerHTML = "";
    await refresh();
  } catch (e) { toast(String(e), "err"); }
};
$("savebtn").onclick = async () => {
  try {
    const r = await api("/api/save", {});
    if (r.targets) {
      Object.keys(r.targets).forEach(t => {
        const tr = r.targets[t];
        toast("[" + t + "] " + (tr.ok ? "OK — " + tr.detail : "FAIL: " + tr.detail),
          tr.ok ? "ok" : "err");
      });
      if (!r.ok) toast("some targets failed — local file/registry may still be fine", "err");
    } else {
      toast("saved" + (r.backup ? " · backup: " + r.backup : ""), "ok");
    }
    if (r.cloud && r.cloud.uploaded === false) toast("Steam Cloud STALE — " + r.cloud.note, "err");
    renderVerify(r.verify); await refresh();
  } catch (e) { toast(String(e), "err"); }
};
$("ctlsearch").oninput = refresh;
$("leafsearch").oninput = renderTree;
$("rawbtn").onclick = async () => {
  if (!S.ctlShort) { toast("pick a controller first", "err"); return; }
  const w = $("rawwrap"); w.classList.toggle("hidden");
  if (!w.classList.contains("hidden")) {
    const r = await api("/api/node?controller=" + encodeURIComponent(S.ctlShort));
    $("rawtext").value = JSON.stringify(r.value, null, 2);
  }
};
$("rawapply").onclick = async () => {
  try {
    const parsed = JSON.parse($("rawtext").value);
    const r = await setVal("", parsed);
    toast("controller replaced · " + r.sync, "ok");
    reloadNode();
  } catch (e) { toast("bad JSON: " + e.message, "err"); }
};

refresh().catch(e => { $("verify").textContent = "server error: " + e; });
