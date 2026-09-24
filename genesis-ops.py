#!/usr/bin/env python3
"""Genesis Ops on this Linux machine.

  python3 genesis-ops.py --install
  python3 genesis-ops.py

Install writes a desktop icon and copies this file to
/home/prime1/genesis-ops/genesis-ops.py
The icon opens http://127.0.0.1:8787 on this computer only.
This is the project scanner. It is not Crypto Dashboard (:8765)
and not Mission Control (:8766).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PORT = 8787
RESERVED = {8000, 6379, 5432, 5678, 8765, 8766}
SKIP_DIR = {
    "node_modules", ".git", "dist", "build", "target", ".venv", "venv",
    "__pycache__", ".next", ".cache", ".turbo", ".output", "vendor",
    ".local", ".config", ".npm", ".cargo", ".rustup", ".mozilla",
    ".steam", ".thumbnails", ".Trash", "snap",
}
SKIP_PATH = ("/go/pkg/", "/pkg/mod/", "/.grok/", "-grok-workspace")
MARKERS = {
    "package.json": "node", "Cargo.toml": "rust", "go.mod": "go",
    "pyproject.toml": "python", "foundry.toml": "solidity",
    "SKILL.md": "skill", "portfolio.json": "genesis",
}
NAMED = ("genesis", "hermes", "hister", "keepline", "dataplicity", "obsidian")


def home() -> Path:
    env = os.environ.get("GENESIS_HOME")
    if env:
        return Path(env)
    prime = Path("/home/prime1")
    return prime if prime.is_dir() else Path.home()


def install_dir() -> Path:
    return home() / "genesis-ops"


def skip_dir(name: str) -> bool:
    return name in SKIP_DIR or (name.startswith(".") and name != ".git")


def scan() -> dict:
    root = home()
    found = []
    now = datetime.now(tz=timezone.utc).timestamp()
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        parent = os.path.basename(os.path.dirname(dirpath))
        has_git = ".git" in dirnames or os.path.isdir(os.path.join(dirpath, ".git"))
        dirnames[:] = [d for d in dirnames if not skip_dir(d)]
        if parent == "go" and "pkg" in dirnames:
            dirnames.remove("pkg")
        if any(s in dirpath for s in SKIP_PATH) or depth > 5:
            dirnames[:] = []
            continue
        kind = None
        for marker, k in MARKERS.items():
            if marker in filenames:
                kind = k
                break
        base = os.path.basename(dirpath)
        named = any(t in base.lower() for t in NAMED) and base.lower() not in {"skills", "skill"}
        if not kind and not named and not has_git:
            continue
        if kind is None:
            kind = "named" if named else "git"
        newest = 0.0
        for fn in filenames:
            try:
                newest = max(newest, os.path.getmtime(os.path.join(dirpath, fn)))
            except OSError:
                pass
        day = datetime.fromtimestamp(newest or now, tz=timezone.utc).date().isoformat()
        age = max(0, int((now - (newest or now)) / 86400))
        alerts = []
        if not has_git:
            alerts.append("ei git")
        if age > 30:
            alerts.append(f"hiljainen {age} pv")
        found.append({
            "name": base,
            "path": dirpath,
            "folder": rel.split(os.sep)[0] if rel != "." else base,
            "kind": kind,
            "git": has_git,
            "age": age,
            "updated": day,
            "alerts": alerts,
        })
        if len(found) >= 200:
            dirnames[:] = []
    found.sort(key=lambda p: (p["age"], p["path"]))
    return {
        "scannedAt": datetime.now(tz=timezone.utc).isoformat(),
        "home": str(root),
        "count": len(found),
        "projects": found,
    }


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Genesis Ops</title>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&family=Fraunces:ital,opsz,wght@0,9..144,500;1,9..144,500&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0e1412;--surface:#171f1b;--raised:#1e2923;--fg:#edf3ee;--muted:#8f9d94;--primary:#d4b483;--ink:#1a140c;--crit:#e08a7a;--ok:#8fbf9a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 Figtree,sans-serif}
.wrap{max-width:72rem;margin:0 auto;padding:28px 28px 48px}
.kicker{letter-spacing:.16em;text-transform:uppercase;color:var(--primary);font-size:.72rem;font-weight:600}
h1{font-family:Fraunces,serif;font-style:italic;font-weight:500;font-size:2.6rem;margin:6px 0}
h1 span{color:var(--primary);font-style:normal}
.muted{color:var(--muted)}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:18px 0}
@media(max-width:900px){.kpis{grid-template-columns:1fr 1fr}}
.card{background:var(--surface);border-radius:18px;box-shadow:0 0 0 1px rgba(255,255,255,.07)}
.kpi{padding:14px 16px}.kpi b{display:block;font-family:Fraunces,serif;font-size:1.8rem;font-weight:500}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
button,input{min-height:44px;border:0;border-radius:999px;background:transparent;color:var(--muted);padding:0 14px;font:inherit}
button.tab.on{background:var(--raised);color:var(--primary);box-shadow:0 0 0 1px rgba(255,255,255,.07)}
button.chip{background:var(--raised);color:var(--muted)}
button.chip.on{background:var(--primary);color:var(--ink);font-weight:650}
button.gold{background:var(--primary);color:var(--ink);font-weight:650}
label.chk{display:inline-flex;gap:8px;align-items:center;min-height:44px;color:var(--muted)}
ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
li.item{padding:18px 20px}
.lvl{color:var(--crit);font-size:.72rem;letter-spacing:.08em;font-weight:700}
h2{font-family:Fraunces,serif;font-size:1.35rem;margin:6px 0;font-weight:500}
.dot{width:8px;height:8px;border-radius:99px;display:inline-block;background:var(--primary);margin-right:6px}
.search{margin-left:auto;background:var(--surface);box-shadow:0 0 0 1px rgba(255,255,255,.07);min-width:220px}
.lab{font-size:.68rem;letter-spacing:.12em;color:var(--muted);width:64px}
</style>
</head>
<body>
<div class="wrap">
  <p class="kicker">Librarian SSOT</p>
  <h1>Genesis <span>Ops</span></h1>
  <p class="muted" id="meta">This computer · port 8787 · not crypto dashboard · not Mission Control</p>
  <div class="kpis" id="kpis"></div>
  <label class="chk"><input id="catalog" type="checkbox" checked/> Include Grok catalog</label>
  <div class="row" id="tabs"></div>
  <div class="row" id="filters"></div>
  <div id="view"></div>
</div>
<script>
const CATALOG=[
 {id:"genesis-bootstrap",name:"Genesis Bootstrap / Runtime",kind:"infra",folder:"Genesis Bootstrap",origin:"genesis",git:true,age:83,updated:"2026-07-03",alerts:["viability stale (83 d)"],detail:"last_reviewed=2026-07-03. Librarian forces re-review after 30 days."},
 {id:"genesis-tech-scout",name:"Genesis Tech Scout",kind:"infra",folder:"Genesis Tech Scout",origin:"genesis",git:true,age:83,updated:"2026-07-03",alerts:["viability stale (83 d)"],detail:"last_reviewed=2026-07-03. Librarian forces re-review after 30 days."},
 {id:"own-account-yield",name:"Own-account yield lanes",kind:"yield",folder:"Own-account yield lanes",origin:"genesis",git:true,age:4,updated:"2026-09-20",alerts:["No wallet or live positions in this workspace"],detail:"Skills on disk. No live wallet audit."},
 {id:"fi-legal",name:"FI legal / insurance / debt",kind:"domain",folder:"FI legal",origin:"genesis",git:true,age:40,updated:"2026-08-15",alerts:["needs a fresh review"],detail:"Domain pack. Re-check before acting."},
 {id:"ops-board",name:"Ops board + attention agent",kind:"content",folder:"Ops board + attention agent",origin:"genesis",git:true,age:4,updated:"2026-09-20",alerts:[],detail:"This board."},
 {id:"kids-yt",name:"Kids YouTube strategist",kind:"content",folder:"Kids YouTube strategist",origin:"genesis",git:true,age:50,updated:"2026-08-05",alerts:["idea gone quiet"],detail:"No publish loop in this workspace."},
 {id:"cex-vip",name:"CEX VIP / Base App audits",kind:"audit",folder:"CEX VIP",origin:"genesis",git:true,age:20,updated:"2026-09-04",alerts:[],detail:"Audit notes only. No live keys."}
];
let DISK=[], tab="attention", kind="", folder="", flag="", q="";
const reviewed=new Set(JSON.parse(localStorage.getItem("gops-reviewed")||"[]"));
async function load(){
  const r=await fetch("/api/scan");
  const data=await r.json();
  DISK=(data.projects||[]).map(p=>({...p,id:p.path,origin:"local",detail:(p.alerts||[]).join(" · ")||"On this disk."}));
  document.getElementById("meta").textContent="This computer · "+data.home+" · "+data.count+" on disk · "+(data.scannedAt||"").replace("T"," ").slice(0,19)+" · port 8787 · not :8765 · not :8766";
  draw();
}
function pool(){
  const cat=document.getElementById("catalog").checked?CATALOG:[];
  return DISK.concat(cat).filter(p=>{
    if(reviewed.has(p.id)) return flag!=="attention";
    if(flag==="git"&&!p.git) return false;
    if(flag==="nogit"&&p.git) return false;
    if(flag==="rust"&&p.kind!=="rust") return false;
    if(flag==="go"&&p.kind!=="go") return false;
    if(flag==="attention"&&!(p.alerts||[]).length) return false;
    if(flag==="local"&&p.origin!=="local") return false;
    if(flag==="genesis"&&p.origin!=="genesis") return false;
    if(kind&&p.kind!==kind) return false;
    if(folder&&p.folder!==folder) return false;
    if(q&&!(p.name+" "+(p.path||"")).toLowerCase().includes(q)) return false;
    return true;
  });
}
function draw(){
  const rows=pool();
  const all=DISK.concat(document.getElementById("catalog").checked?CATALOG:[]);
  const need=all.filter(p=>(p.alerts||[]).length&&!reviewed.has(p.id));
  const bits=[["On this disk",DISK.length],["Grok catalog",document.getElementById("catalog").checked?CATALOG.length:0],["Rust crates",DISK.filter(p=>p.kind==="rust").length],["Genesis active","5/5"],["Needs you",need.length]];
  document.getElementById("kpis").innerHTML=bits.map(b=>'<div class="card kpi"><b>'+b[1]+'</b><span class="muted">'+b[0]+'</span></div>').join("");
  const tabs=document.getElementById("tabs");
  tabs.innerHTML="";
  ["attention","map","projects","skills","ledger"].forEach(t=>{
    const b=document.createElement("button");
    b.className="tab"+(tab===t?" on":"");
    b.textContent=(t[0].toUpperCase()+t.slice(1))+(t==="attention"?" "+need.length:"");
    b.onclick=()=>{tab=t;draw()};
    tabs.appendChild(b);
  });
  const inp=document.createElement("input");
  inp.className="search"; inp.placeholder="Filter…"; inp.value=q;
  inp.oninput=()=>{q=inp.value.toLowerCase();drawList()};
  tabs.appendChild(inp);
  const filters=document.getElementById("filters");
  filters.innerHTML="";
  const addRow=(label,items,cur,set)=>{
    const lab=document.createElement("span"); lab.className="lab"; lab.textContent=label; filters.appendChild(lab);
    items.forEach(([id,text])=>{
      const b=document.createElement("button");
      b.className="chip"+(cur===id?" on":"");
      b.textContent=text;
      b.onclick=()=>set(cur===id?"":id);
      filters.appendChild(b);
    });
    filters.appendChild(document.createElement("div"));
    filters.lastChild.style.flexBasis="100%";
  };
  addRow("SHOW",[["","All"],["local","This PC"],["genesis","Grok catalog"],["git","Git"],["nogit","No git"],["rust","Rust"],["go","Go"],["attention","Needs attention"]],flag,v=>{flag=v;draw()});
  const kinds=[...new Set(all.map(p=>p.kind))];
  addRow("KIND",kinds.map(k=>[k,k+" "+all.filter(p=>p.kind===k).length]),kind,v=>{kind=v;draw()});
  const folders=[...new Set(all.map(p=>p.folder))].slice(0,12);
  addRow("FOLDER",folders.map(f=>[f,f+" "+all.filter(p=>p.folder===f).length]),folder,v=>{folder=v;draw()});
  document.getElementById("catalog").onchange=draw;
  const view=document.getElementById("view");
  const list=tab==="attention"?rows.filter(p=>(p.alerts||[]).length):rows;
  if(tab==="map"){view.innerHTML='<div class="card" style="padding:16px"><svg id="map" viewBox="0 0 640 420"></svg></div>';drawMap(rows);return;}
  if(tab==="skills"||tab==="ledger"){view.innerHTML='<p class="muted">Same board. '+(tab==="skills"?"Skills live on disk under the project paths.":"Ledger is the scan itself: "+DISK.length+" paths.")+'</p>';return;}
  view.innerHTML='<ul id="list"></ul>';
  drawList(list);
}
function drawList(list){
  const ul=document.getElementById("list");
  if(!ul) return;
  const rows=list||pool();
  ul.innerHTML=rows.slice(0,60).map(p=>{
    const code=(p.alerts&&p.alerts[0])?"stale_review":"ok";
    return '<li class="item card"><div class="lvl">'+(p.alerts&&p.alerts.length?"CRIT":"OK")+' '+code+'</div><h2>'+p.name+(p.alerts&&p.alerts[0]?": "+p.alerts[0]:"")+'</h2><p class="muted">'+(p.detail||p.path||"")+'</p><div class="row"><button class="gold" data-id="'+p.id+'">Mark reviewed today</button><button data-open="'+encodeURIComponent(p.path||p.name)+'">Open project</button></div></li>';
  }).join("")||'<li class="item card"><p class="muted">Nothing matches.</p></li>';
  ul.querySelectorAll("button.gold").forEach(b=>b.onclick=()=>{reviewed.add(b.dataset.id);localStorage.setItem("gops-reviewed",JSON.stringify([...reviewed]));draw()});
  ul.querySelectorAll("button[data-open]").forEach(b=>b.onclick=()=>{folder="";q=decodeURIComponent(b.dataset.open).split("/").pop();tab="projects";draw()});
}
function drawMap(rows){
  const groups={};
  rows.forEach(p=>{groups[p.folder]=(groups[p.folder]||0)+1});
  const entries=Object.entries(groups).sort((a,b)=>b[1]-a[1]).slice(0,24);
  const max=Math.max(1,...entries.map(e=>e[1]));
  const svg=document.getElementById("map");
  entries.forEach(([name,n],i)=>{
    const a=i*2.399, rad=Math.sqrt((i+1)/entries.length)*170;
    const c=document.createElementNS("http://www.w3.org/2000/svg","circle");
    c.setAttribute("cx",320+Math.cos(a)*rad); c.setAttribute("cy",210+Math.sin(a)*rad);
    c.setAttribute("r",14+Math.sqrt(n/max)*34); c.setAttribute("fill","#d4b483"); c.setAttribute("fill-opacity",".7");
    c.style.cursor="pointer"; c.onclick=()=>{folder=name;tab="projects";draw()};
    svg.appendChild(c);
  });
}
document.getElementById("catalog").checked=true;
load();
setInterval(load,60000);
</script>
</body>
</html>
"""
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/scan":
            payload = json.dumps(scan()).encode()
            self._send(200, payload, "application/json")
            return
        if path in ("/", "/index.html"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            return
        self._send(404, b"no", "text/plain")


def serve() -> None:
    port = PORT
    server = None
    for candidate in range(PORT, PORT + 8):
        if candidate in RESERVED:
            continue
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("Ei vapaata porttia 8787–8794. Crypto :8765 jätettiin rauhaan.")
    url = f"http://127.0.0.1:{port}"
    print("Genesis Ops PROJEKTISKANNERI (ei crypto, ei mission control)")
    print(url)
    print("Koti:", home())
    print("Sulje palvelu: systemctl --user stop genesis-ops")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nseis")


def install() -> None:
    src = Path(__file__).resolve()
    dest_dir = install_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / "genesis-ops.py"
    target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    target.chmod(0o755)
    opener = dest_dir / "open.sh"
    opener.write_text(
        f"""#!/bin/bash
URL=http://127.0.0.1:{PORT}/
if ! curl -fsS -o /dev/null --max-time 2 "$URL"; then
  systemctl --user start genesis-ops.service 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    curl -fsS -o /dev/null --max-time 1 "$URL" && break
    sleep 0.4
  done
fi
xdg-open "$URL" >/dev/null 2>&1 || true
""",
        encoding="utf-8",
    )
    opener.chmod(0o755)
    desktop = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Genesis Ops
Comment=Projektiskanneri portissa {PORT}. Ei crypto, ei mission control.
Exec={opener}
Icon=utilities-system-monitor
Terminal=false
Categories=Utility;
StartupNotify=true
"""
    folders = [
        home() / "Työpöytä",
        home() / "Desktop",
        Path.home() / ".local" / "share" / "applications",
    ]
    written = []
    for folder in folders:
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        path = folder / "Genesis-Ops.desktop"
        path.write_text(desktop, encoding="utf-8")
        path.chmod(0o755)
        try:
            subprocess.run(
                ["gio", "set", str(path), "metadata::trusted", "true"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
        written.append(path)
    autostart = Path.home() / ".config" / "autostart"
    autostart.mkdir(parents=True, exist_ok=True)
    auto = autostart / "Genesis-Ops.desktop"
    auto.write_text(
        desktop + "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )
    auto.chmod(0o755)
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit = unit_dir / "genesis-ops.service"
    unit.write_text(
        f"""[Unit]
Description=Genesis Ops project scanner on {PORT}
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {target} --no-browser
WorkingDirectory={dest_dir}
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
""",
        encoding="utf-8",
    )
    print("Asennettu:", target)
    print("Kuvake avaa:", opener)
    for path in written:
        print(" kuvake:", path)
    print("Autostart:", auto)
    print("Palvelu:", unit)
    if os.environ.get("GENESIS_SKIP_SYSTEMD") == "1":
        print("systemd ohitettu")
        return
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        started = subprocess.run(
            ["systemctl", "--user", "enable", "--now", "genesis-ops.service"],
            check=False,
        )
        linger = subprocess.run(["loginctl", "enable-linger", os.environ.get("USER", "")], check=False)
    except FileNotFoundError:
        print("systemd ei ole tässä ympäristössä")
        return
    subprocess.run(["systemctl", "--user", "restart", "genesis-ops.service"], check=False)
    if started.returncode == 0:
        print("Aina päällä: genesis-ops.service")
    else:
        print("Palvelua ei saatu päälle. Kirjautumisen jälkeen kuvake avaa sen.")
    if linger.returncode != 0:
        print("Linger ei mennyt (salasana voi puuttua). Käynnistyy kun kirjaudut sisään.")



def check_ports() -> None:
    import urllib.request
    targets = [
        (8765, "crypto dashboard"),
        (8766, "mission control"),
        (8000, "vLLM"),
        (8787, "genesis ops scanner"),
    ]
    print("Vain luku. Ei tapeta prosesseja.")
    for port, name in targets:
        url = f"http://127.0.0.1:{port}/"
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                print(f"UP   :{port}  {name}  HTTP {resp.status}")
        except Exception as exc:
            print(f"DOWN :{port}  {name}  {type(exc).__name__}")


def self_test() -> None:
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    (tmp / "hister").mkdir()
    (tmp / "hister" / "package.json").write_text('{"name":"h"}')
    (tmp / "GENESIS_AUDITS").mkdir()
    (tmp / "GENESIS_AUDITS" / "notes.md").write_text("x")
    os.environ["GENESIS_HOME"] = str(tmp)
    data = scan()
    names = {p["name"] for p in data["projects"]}
    assert "hister" in names and "GENESIS_AUDITS" in names, names
    assert PORT == 8787 and 8765 in RESERVED and 8766 in RESERVED
    print("SELF-TEST OK", sorted(names))


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    elif "--check" in sys.argv:
        check_ports()
    elif "--install" in sys.argv:
        install()
    else:
        serve()
