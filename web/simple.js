"use strict";
/* Simple mode: player-friendly cards. Uses api()/toast() from app.js. */
let MODE = "simple";

function setMode(m) {
  MODE = m;
  $("mode-simple").classList.toggle("sel", m === "simple");
  $("mode-expert").classList.toggle("sel", m === "expert");
  $("tree").classList.toggle("hidden", m === "simple");
  $("rawwrap").classList.add("hidden");
  document.querySelector(".toolbar strong").style.display = m === "simple" ? "none" : "";
  $("leafsearch").style.display = m === "simple" ? "none" : "";
  $("rawbtn").style.display = m === "simple" ? "none" : "";
  if (m === "simple") loadSimple();
  else if (!S.ctlShort) $("tree").innerHTML = "<p class='dim'>← pick a controller</p>";
}
$("mode-simple").onclick = () => setMode("simple");
$("mode-expert").onclick = () => setMode("expert");

function fldCtl(f) { return S.kind === "meta" ? "_meta" : f.ctl; }
async function pushSet(f, path, value) {
  const r = await api("/api/set", { controller: fldCtl(f), path: path, value: value });
  const st = await api("/api/state");
  renderVerify(st.verify);
  return r;
}
function fullPath(f, sub) { return sub ? f.path + "." + sub : f.path; }

function card(title, hint) {
  const d = document.createElement("div"); d.className = "card";
  const h = document.createElement("h3"); h.textContent = title; d.appendChild(h);
  if (hint) { const p = document.createElement("p"); p.className = "chint"; p.textContent = hint; d.appendChild(p); }
  return d;
}
function fieldRow(label, hint, ctrl) {
  const r = document.createElement("div"); r.className = "frow";
  const l = document.createElement("div"); l.className = "flabel";
  l.textContent = label;
  if (hint) { const s = document.createElement("small"); s.textContent = hint; l.appendChild(document.createElement("br")); l.appendChild(s); }
  r.appendChild(l);
  const w = document.createElement("div"); w.className = "fwidget";
  w.appendChild(ctrl); r.appendChild(w);
  return r;
}

function wNumber(f, val, onVal) {
  const wrap = document.createElement("div"); wrap.className = "stepper";
  const minus = document.createElement("button"); minus.textContent = "−";
  const inp = document.createElement("input");
  inp.type = "number"; inp.value = val;
  if (f.min !== undefined) inp.min = f.min;
  if (f.max !== undefined) inp.max = f.max;
  if (f.step !== undefined) inp.step = f.step;
  const plus = document.createElement("button"); plus.textContent = "+";
  const commit = v => { let n = Number(v); if (Number.isNaN(n)) return; onVal(n); };
  minus.onclick = () => { inp.value = Number(inp.value) - 1; commit(inp.value); };
  plus.onclick = () => { inp.value = Number(inp.value) + 1; commit(inp.value); };
  inp.onchange = () => commit(inp.value);
  wrap.appendChild(minus); wrap.appendChild(inp); wrap.appendChild(plus);
  return wrap;
}
function wToggle(f, val, isFlag) {
  const c = document.createElement("input");
  c.type = "checkbox"; c.checked = isFlag ? val === 1 : !!val;
  c.onchange = () => pushSet(f, f.path, isFlag ? (c.checked ? 1 : 0) : c.checked)
    .then(() => toast("saved", "ok")).catch(e => toast(String(e), "err"));
  return c;
}
function wSelect(f, val) {
  const s = document.createElement("select");
  (f.options || []).forEach(o => {
    const op = document.createElement("option");
    op.value = o.value; op.textContent = o.label;
    if (o.value === val) op.selected = true;
    s.appendChild(op);
  });
  s.onchange = () => pushSet(f, f.path, Number(s.value))
    .then(() => toast("saved", "ok")).catch(e => toast(String(e), "err"));
  return s;
}
function nameOf(f, id) {
  const o = (f.options || []).find(o => o.value === id);
  return o ? o.label : "#" + id;
}
function wIdList(f, val, numOnly) {
  const wrap = document.createElement("div");
  const chips = document.createElement("div"); chips.className = "chips";
  const redraw = cur => {
    chips.innerHTML = "";
    cur.forEach(id => {
      const c = document.createElement("span"); c.className = "chip";
      c.textContent = (numOnly ? id : nameOf(f, id)) + " ×";
      c.title = "click to remove";
      c.onclick = () => {
        const nv = cur.filter(x => x !== id);
        pushSet(f, f.path, nv).then(() => { f.value = nv; redraw(nv); });
      };
      chips.appendChild(c);
    });
    if (!cur.length) { const e = document.createElement("span"); e.className = "dim"; e.textContent = "— empty —"; chips.appendChild(e); }
  };
  redraw(val.slice());
  wrap.appendChild(chips);
  const row = document.createElement("div"); row.className = "addrow";
  let inp;
  if (numOnly) {
    inp = document.createElement("input"); inp.type = "number"; inp.placeholder = "id";
  } else {
    inp = document.createElement("select");
    (f.options || []).forEach(o => {
      const op = document.createElement("option"); op.value = o.value; op.textContent = o.label;
      inp.appendChild(op);
    });
  }
  const add = document.createElement("button"); add.textContent = "Add";
  add.onclick = () => {
    const id = numOnly ? Number(inp.value) : Number(inp.value);
    if (Number.isNaN(id)) return;
    const cur = f.value.slice();
    if (cur.indexOf(id) < 0) cur.push(id);
    pushSet(f, f.path, cur).then(() => { f.value = cur; redraw(cur); });
  };
  row.appendChild(inp); row.appendChild(add); wrap.appendChild(row);
  return wrap;
}
function wChecklist(f, val) {
  const wrap = document.createElement("div"); wrap.className = "checks";
  const spoiler = !!f.spoiler;
  if (spoiler) wrap.classList.add("blur");
  Object.keys(val).forEach(k => {
    const lbl = document.createElement("label");
    const c = document.createElement("input"); c.type = "checkbox";
    const on = val[k] === 1 || val[k] === true;
    c.checked = on;
    const nm = (f.labels && f.labels[k]) ? f.labels[k][0] : k;
    const hint = (f.labels && f.labels[k]) ? f.labels[k][1] : "";
    c.onchange = () => {
      const nv = (val[k] === true || val[k] === false) ? c.checked : (c.checked ? 1 : 0);
      pushSet(f, fullPath(f, k), nv).then(() => { val[k] = nv; });
    };
    lbl.appendChild(c);
    const sp = document.createElement("span"); sp.textContent = nm;
    if (hint) sp.title = hint;
    lbl.appendChild(sp);
    wrap.appendChild(lbl);
  });
  if (spoiler) {
    const rev = document.createElement("button"); rev.textContent = "reveal spoiler";
    rev.onclick = () => { wrap.classList.remove("blur"); rev.remove(); };
    wrap.appendChild(rev);
  }
  return wrap;
}
function wMap(f, val, kind) {
  const wrap = document.createElement("div"); wrap.className = "maprows";
  Object.keys(val).forEach(k => {
    const row = document.createElement("div"); row.className = "mrow";
    const l = document.createElement("span"); l.className = "mlabel"; l.textContent = k;
    row.appendChild(l);
    const inp = document.createElement("input");
    if (kind === "num") {
      inp.type = "number"; inp.value = val[k];
      if (f.step !== undefined) inp.step = f.step;
      inp.onchange = () => {
        const n = Number(inp.value);
        if (Number.isNaN(n)) return;
        pushSet(f, fullPath(f, k), n).then(() => { val[k] = n; });
      };
    } else {
      inp.type = "text"; inp.value = val[k];
      inp.onchange = () => pushSet(f, fullPath(f, k), inp.value).then(() => { val[k] = inp.value; });
    }
    row.appendChild(inp); wrap.appendChild(row);
  });
  return wrap;
}

async function loadSimple() {
  const box = $("simple"); box.innerHTML = "<p class='dim'>loading…</p>";
  let r;
  try { r = await api("/api/simple"); }
  catch (e) { box.innerHTML = ""; toast(String(e), "err"); return; }
  box.innerHTML = "";
  r.sections.forEach(sec => {
    const c = card(sec.title, sec.hint);
    sec.fields.forEach(f => {
      const v = f.value;
      let w = null;
      const setLeaf = nv => pushSet(f, f.path, nv).then(() => { f.value = nv; toast("saved", "ok"); })
        .catch(e => toast(String(e), "err"));
      switch (f.widget) {
        case "number": w = wNumber(f, v, setLeaf); break;
        case "toggle": w = wToggle(f, v, false); break;
        case "flag": w = wToggle(f, v, true); break;
        case "select": w = wSelect(f, v); break;
        case "text": {
          const i = document.createElement("input"); i.type = "text"; i.value = v || "";
          i.onchange = () => setLeaf(i.value); w = i; break;
        }
        case "readonly": {
          const s = document.createElement("span"); s.textContent = String(v); w = s; break;
        }
        case "idlist": w = wIdList(f, v || [], false); break;
        case "intlist": w = wIdList(f, v || [], true); break;
        case "strlist": {
          const wrap = document.createElement("div");
          const chips = document.createElement("div"); chips.className = "chips";
          const redraw = cur => {
            chips.innerHTML = "";
            cur.forEach(sv => {
              const c = document.createElement("span"); c.className = "chip";
              c.textContent = sv + " ×"; c.onclick = () => {
                const nv = cur.filter(x => x !== sv);
                pushSet(f, f.path, nv).then(() => { f.value = nv; redraw(nv); });
              };
              chips.appendChild(c);
            });
          };
          redraw((v || []).slice()); wrap.appendChild(chips);
          const row = document.createElement("div"); row.className = "addrow";
          const inp = document.createElement("input"); inp.type = "text";
          const add = document.createElement("button"); add.textContent = "Add";
          add.onclick = () => {
            if (!inp.value) return;
            const cur = f.value.slice(); cur.push(inp.value);
            pushSet(f, f.path, cur).then(() => { f.value = cur; redraw(cur); inp.value = ""; });
          };
          row.appendChild(inp); row.appendChild(add); wrap.appendChild(row);
          w = wrap; break;
        }
        case "checklist": w = wChecklist(f, v || {}); break;
        case "nummap": w = wMap(f, v || {}, "num"); break;
        case "textmap": w = wMap(f, v || {}, "text"); break;
        default: {
          const s = document.createElement("span"); s.className = "dim";
          s.textContent = "unsupported: " + f.widget; w = s;
        }
      }
      c.appendChild(fieldRow(f.label, f.hint, w));
    });
    box.appendChild(c);
  });
}

// opening a file lands on Simple; expert tree stays available
const _refreshOrig = refresh;
refresh = async function () {
  const st = await _refreshOrig();
  if (st.open && MODE === "simple") loadSimple();
  if (!st.open) { $("simple").innerHTML = "<p class='dim'>open a save file above ↑</p>"; }
  return st;
};

// initial boot: app.js already fired the original refresh() before this
// script installed the wrapper above, so align the panes explicitly here.
(async () => {
  try {
    const st = await api("/api/state");
    if (st.open) setMode("simple");
    else {
      $("tree").classList.add("hidden");
      $("simple").classList.remove("hidden");
      $("simple").innerHTML = "<p class='dim'>open a save file above ↑</p>";
    }
  } catch (e) { /* server down: app.js shows it */ }
})();
