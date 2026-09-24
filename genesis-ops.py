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
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&family=Fraunces:ital,opsz,wght@0,9..144,500;1,9..144,500&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0e1412;--surface:#171f1b;--raised:#1e2923;--fg:#edf3ee;--muted:#8f9d94;--primary:#d4b483;--ink:#1a140c;--crit:#e08a7a;--ok:#8fbf9a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 Figtree,sans-serif}
header{padding:28px 32px 8px}h1{font-family:Fraunces,serif;font-weight:500;font-size:2.4rem;margin:4px 0;font-style:italic}
h1 span{color:var(--primary);font-style:normal}.kicker{letter-spacing:.14em;text-transform:uppercase;color:var(--primary);font-size:.75rem;font-weight:600}
.muted{color:var(--muted)}.wrap{max-width:72rem;margin:0 auto;padding:0 32px 40px}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:16px 0}
@media(max-width:800px){.kpis{grid-template-columns:1fr 1fr}}
.kpi,.card,li.item{background:var(--surface);border-radius:16px;box-shadow:0 0 0 1px rgba(255,255,255,.07)}
.kpi{padding:12px 16px}.kpi b{display:block;font-family:Fraunces,serif;font-size:1.7rem;font-weight:500}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0}
button,input{min-height:44px;border:0;border-radius:999px;background:var(--raised);color:var(--muted);padding:0 14px}
button.on,button.tab.on{background:var(--raised);color:var(--primary);box-shadow:0 0 0 1px rgba(255,255,255,.07)}
ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
li.item{padding:16px 18px}h2{font-family:Fraunces,serif;font-size:1.25rem;margin:8px 0}
.pill{display:inline-flex;min-height:28px;align-items:center;border-radius:999px;padding:0 10px;background:var(--raised);color:var(--muted);font-size:.75rem;margin-right:6px}
.pill.bad{color:var(--crit)}
.bar{height:6px;background:var(--raised);border-radius:999px;overflow:hidden;margin-top:10px}
.bar i{display:block;height:100%;background:var(--primary)}
svg{width:100%;height:auto}
</style>
</head>
<body>
<header class="wrap">
  <p class="kicker">Librarian SSOT · this computer · port 8787</p>
  <h1>Genesis <span>Ops</span></h1>
  <p class="muted" id="meta">Scanning this disk. Not the crypto dashboard. Not Mission Control.</p>
</header>
<div class="wrap">
  <div class="kpis" id="kpis"></div>
  <div class="row" id="filters"></div>
  <div class="row" id="tabs"></div>
  <div id="view"></div>
</div>
<script>
let DATA={projects:[]}, tab="attention", kind="", folder="";
const tabs=["attention","map","projects"];
async function load(){
  const r=await fetch("/api/scan");
  DATA=await r.json();
  document.getElementById("meta").textContent=
    "This computer · "+DATA.home+" · "+DATA.count+" projects · "+(DATA.scannedAt||"").replace("T"," ").slice(0,19)+" · not :8765 · not :8766";
  draw();
}
function shown(){
  return (DATA.projects||[]).filter(p=>{
    if(kind && p.kind!==kind) return false;
    if(folder && p.folder!==folder) return false;
    return true;
  });
}
function hot(list){return list.filter(p=>p.alerts && p.alerts.length)}
function draw(){
  const rows=shown();
  const need=hot(rows);
  const bits=[["On this disk",rows.length],["Needs you",need.length],["No git",rows.filter(p=>!p.git).length],["Quiet 30d+",rows.filter(p=>p.age>30).length],["Folders",new Set(rows.map(p=>p.folder)).size]];
  document.getElementById("kpis").innerHTML=bits.map(b=>'<div class="kpi"><b>'+b[1]+'</b><span class="muted">'+b[0]+'</span></div>').join("");
  const bar=document.getElementById("filters");
  bar.innerHTML="";
  const add=(label,on,fn)=>{const b=document.createElement("button");b.textContent=label;if(on)b.className="on";b.onclick=fn;bar.appendChild(b);};
  add("All",!kind&&!folder,()=>{kind="";folder="";draw()});
  [...new Set((DATA.projects||[]).map(p=>p.kind))].forEach(k=>add(k,kind===k,()=>{kind=kind===k?"":k;draw()}));
  const tabsEl=document.getElementById("tabs");
  tabsEl.innerHTML="";
  tabs.forEach(t=>{const b=document.createElement("button");b.className="tab"+(tab===t?" on":"");b.textContent=t[0].toUpperCase()+t.slice(1)+(t==="attention"?" "+need.length:"");b.onclick=()=>{tab=t;draw()};tabsEl.appendChild(b);});
  const view=document.getElementById("view");
  if(tab==="attention") view.innerHTML=need.length?("<ul>"+need.slice(0,40).map(card).join("")+"</ul>"):'<p class="muted">Nothing needs attention in this filter.</p>';
  else if(tab==="projects") view.innerHTML="<ul>"+rows.slice(0,80).map(card).join("")+"</ul>";
  else view.innerHTML='<div class="card" style="padding:16px"><p class="kicker">Folders</p><svg id="map" viewBox="0 0 640 420"></svg></div>';
  if(tab==="map") drawMap(rows);
}
function card(p){
  const alerts=(p.alerts||[]).map(a=>'<span class="pill bad">'+a+"</span>").join("");
  const pct=Math.max(8,Math.min(100,100-Math.min(p.age,90)));
  return '<li class="item"><div class="pill">'+p.kind+'</div><div class="pill">'+(p.git?"git":"no git")+'</div><h2>'+p.name+'</h2><p class="muted">'+p.path+" · "+p.age+"d · "+p.updated+'</p><div class="bar"><i style="width:'+pct+'%"></i></div><p>'+alerts+"</p></li>";
}
function drawMap(rows){
  const groups={};
  rows.forEach(p=>{groups[p.folder]=(groups[p.folder]||0)+1});
  const entries=Object.entries(groups).sort((a,b)=>b[1]-a[1]).slice(0,24);
  const max=Math.max(1,...entries.map(e=>e[1]));
  const svg=document.getElementById("map");
  svg.innerHTML="";
  entries.forEach(([name,n],i)=>{
    const a=i*2.399, rad=Math.sqrt(i/Math.max(1,entries.length))*180;
    const c=document.createElementNS("http://www.w3.org/2000/svg","circle");
    c.setAttribute("cx",320+Math.cos(a)*rad); c.setAttribute("cy",210+Math.sin(a)*rad);
    c.setAttribute("r",12+Math.sqrt(n/max)*36);
    c.setAttribute("fill","#d4b483"); c.setAttribute("fill-opacity", folder===name?"1":".55");
    c.style.cursor="pointer";
    c.onclick=()=>{folder=folder===name?"":name; tab="projects"; draw()};
    svg.appendChild(c);
    const t=document.createElementNS("http://www.w3.org/2000/svg","text");
    t.setAttribute("x",320+Math.cos(a)*rad); t.setAttribute("y",210+Math.sin(a)*rad+4);
    t.setAttribute("fill","#1a140c"); t.setAttribute("font-size","11"); t.setAttribute("text-anchor","middle");
    t.textContent=name.slice(0,14);
    svg.appendChild(t);
  });
}
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
