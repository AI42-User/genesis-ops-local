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
<html lang="fi">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Genesis Ops — tämä kone</title>
<style>
:root{--bg:#0e1412;--surface:#171f1b;--fg:#edf3ee;--muted:#8f9d94;--gold:#d4b483;--ink:#1a140c;--line:#2a3530;--crit:#e08a7a;--ok:#8fbf9a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 Figtree,system-ui,sans-serif}
header{padding:20px 24px 8px;border-bottom:1px solid var(--line)}
h1{font-family:Fraunces,Georgia,serif;font-weight:500;font-size:2rem;margin:0}
h1 span{color:var(--gold);font-style:italic}
.sub{color:var(--muted);font-size:.9rem}
.bar{display:flex;flex-wrap:wrap;gap:8px;padding:12px 24px}
button,select{min-height:44px;border:0;border-radius:999px;background:#1e2923;color:var(--muted);padding:0 14px;cursor:pointer}
button.on{background:var(--gold);color:var(--ink);font-weight:650}
main{display:grid;grid-template-columns:280px 1fr;gap:16px;padding:8px 24px 32px}
@media(max-width:800px){main{grid-template-columns:1fr}}
.card{background:var(--surface);border-radius:16px;padding:14px}
ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
li{background:var(--surface);border-radius:14px;padding:12px 14px}
.path{color:var(--muted);font-size:.78rem;word-break:break-all}
.tag{display:inline-block;border-radius:999px;padding:2px 8px;background:#1e2923;color:var(--gold);font-size:.75rem;margin-right:6px}
.warn{color:var(--crit)}
svg{width:100%;height:auto}
</style>
</head>
<body>
<header>
  <p class="sub">Projektiskanneri · ei crypto dashboard :8765 · ei mission control :8766</p>
  <h1>Genesis <span>Ops</span></h1>
  <p class="sub" id="meta">skannataan…</p>
</header>
<div class="bar" id="filters"></div>
<main>
  <section class="card"><p class="sub">Kansiot</p><svg id="map" viewBox="0 0 280 280"></svg></section>
  <section><ul id="list"></ul></section>
</main>
<script>
let DATA={projects:[]};
const state={kind:"",folder:"",q:""};
async function load(){
  const r=await fetch("/api/scan");
  DATA=await r.json();
  document.getElementById("meta").textContent=
    DATA.home+" · "+DATA.count+" projektia · "+(DATA.scannedAt||"").slice(0,19).replace("T"," ");
  drawFilters(); draw();
}
function shown(){
  return DATA.projects.filter(p=>{
    if(state.kind && p.kind!==state.kind) return false;
    if(state.folder && p.folder!==state.folder) return false;
    if(state.q && !(p.name+" "+p.path).toLowerCase().includes(state.q)) return false;
    return true;
  });
}
function drawFilters(){
  const kinds=[...new Set(DATA.projects.map(p=>p.kind))];
  const folders=[...new Set(DATA.projects.map(p=>p.folder))].slice(0,12);
  const bar=document.getElementById("filters");
  bar.innerHTML="";
  const add=(label,on,fn)=>{
    const b=document.createElement("button");
    b.textContent=label; b.className=on?"on":""; b.onclick=fn; bar.appendChild(b);
  };
  add("Kaikki",!state.kind&&!state.folder,()=>{state.kind="";state.folder="";draw()});
  kinds.forEach(k=>add(k,state.kind===k,()=>{state.kind=state.kind===k?"":k;draw()}));
  folders.forEach(f=>add(f,state.folder===f,()=>{state.folder=state.folder===f?"":f;draw()}));
  const inp=document.createElement("input");
  inp.placeholder="hae"; inp.value=state.q;
  inp.style.cssText="min-height:44px;border-radius:999px;border:0;background:#1e2923;color:#edf3ee;padding:0 14px";
  inp.oninput=()=>{state.q=inp.value.toLowerCase();drawList()};
  bar.appendChild(inp);
}
function draw(){drawFilters();drawMap();drawList()}
function drawMap(){
  const rows=shown();
  const groups={};
  rows.forEach(p=>{groups[p.folder]=(groups[p.folder]||0)+1});
  const entries=Object.entries(groups).sort((a,b)=>b[1]-a[1]).slice(0,16);
  const max=Math.max(1,...entries.map(e=>e[1]));
  const svg=document.getElementById("map");
  svg.innerHTML="";
  entries.forEach(([name,n],i)=>{
    const a=i*2.399; const rad=20+Math.sqrt(i/Math.max(1,entries.length))*100;
    const c=document.createElementNS("http://www.w3.org/2000/svg","circle");
    c.setAttribute("cx",140+Math.cos(a)*rad); c.setAttribute("cy",140+Math.sin(a)*rad);
    c.setAttribute("r",8+Math.sqrt(n/max)*28);
    c.setAttribute("fill","#d4b483"); c.setAttribute("fill-opacity",state.folder===name?"1":".55");
    c.style.cursor="pointer";
    c.onclick=()=>{state.folder=state.folder===name?"":name;draw()};
    svg.appendChild(c);
  });
}
function drawList(){
  const ul=document.getElementById("list");
  const rows=shown();
  ul.innerHTML="";
  rows.slice(0,80).forEach(p=>{
    const li=document.createElement("li");
    li.innerHTML='<span class="tag">'+p.kind+'</span><b>'+p.name+'</b> <span class="sub">'+p.age+' pv</span>'
      +(p.alerts.length?'<div class="warn">'+p.alerts.join(" · ")+'</div>':'')
      +'<div class="path">'+p.path+'</div>';
    ul.appendChild(li);
  });
  if(!rows.length) ul.innerHTML="<li>Ei osumia.</li>";
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
    print("Sulje: Ctrl+C")
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
    text = src.read_text(encoding="utf-8")
    target.write_text(text, encoding="utf-8")
    target.chmod(0o755)
    desktop = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Genesis Ops
Comment=Paikallinen skanneri tälle koneelle
Exec=/usr/bin/python3 {target}
Icon=utilities-system-monitor
Terminal=true
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
        written.append(path)
    print("Asennettu:", target)
    for path in written:
        print(" kuvake:", path)
    print("Avaa kuvake tai aja: python3", target)


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
