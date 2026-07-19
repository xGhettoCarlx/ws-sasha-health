#!/usr/bin/env python3
"""make_pwa.py — turn any Station web project into an installable Progressive Web App.

Usage:
    python3 make_pwa.py <project_dir> [--force] [--dry-run] [--name NAME] [--base /path/]

What it does:
  1. Resolves project root (package.json / index.html / public/)
  2. Writes manifest.json (name from package.json or folder)
  3. Writes service-worker.js (cache-first static, network-first API)
  4. Injects <link rel="manifest"> + SW registration into index.html
  5. Ensures 192×192 and 512×512 icons (templates or SVG placeholders)

Vite projects: assets land in public/ so ``npm run build`` copies them to dist/.
Static sites: assets land next to index.html.

Station path (canonical):
    ~/Station/Service/burn-008/scripts/make_pwa.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_VERSION = "1.0.0"
STATION_ICON_TEMPLATES = Path.home() / "Station" / "templates" / "pwa-icons"

# Marker comments so re-runs are idempotent
MANIFEST_LINK_MARKER = "make_pwa:manifest"
SW_REG_MARKER = "make_pwa:sw-register"

DEFAULT_THEME = "#0f172a"
DEFAULT_BG = "#ffffff"


# ── helpers ────────────────────────────────────────────────────────────────


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def log(msg: str) -> None:
    print(f"  · {msg}")


def expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def detect_vite(project: Path) -> bool:
    return any(project.glob("vite.config.*"))


def detect_vite_plugin_pwa(project: Path) -> bool:
    """True when project already uses vite-plugin-pwa (workbox SW at build)."""
    pkg = project / "package.json"
    if pkg.is_file():
        raw = pkg.read_text(encoding="utf-8", errors="ignore")
        if "vite-plugin-pwa" in raw:
            return True
    for cfg in project.glob("vite.config.*"):
        if "VitePWA" in cfg.read_text(encoding="utf-8", errors="ignore"):
            return True
    return False


def find_index_html(project: Path) -> Path | None:
    candidates = [
        project / "index.html",
        project / "public" / "index.html",
        project / "src" / "index.html",
        project / "dist" / "index.html",
    ]
    for c in candidates:
        if c.is_file():
            return c
    # first shallow match
    for p in project.rglob("index.html"):
        if "node_modules" in p.parts:
            continue
        return p
    return None


def detect_base_path(project: Path, cli_base: str | None) -> str:
    if cli_base is not None:
        b = cli_base.strip() or "/"
        if not b.startswith("/"):
            b = "/" + b
        if not b.endswith("/"):
            b = b + "/"
        return b if b != "//" else "/"

    # vite.config.* base: "/sh/"
    for cfg in project.glob("vite.config.*"):
        text = cfg.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"""base\s*:\s*['"]([^'"]+)['"]""", text)
        if m:
            b = m.group(1)
            if not b.startswith("/"):
                b = "/" + b
            if not b.endswith("/"):
                b = b + "/"
            return b

    # existing public/manifest
    for man in (project / "public" / "manifest.json", project / "manifest.json"):
        if man.is_file():
            data = read_json(man)
            scope = data.get("scope") or data.get("start_url") or "/"
            if isinstance(scope, str) and scope.startswith("/"):
                if not scope.endswith("/"):
                    # start_url may be /sh/index.html
                    if scope.count("/") >= 2 and not scope.endswith(".html"):
                        scope = scope.rsplit("/", 1)[0] + "/"
                    elif scope.endswith(".html"):
                        scope = scope.rsplit("/", 1)[0] + "/"
                    else:
                        scope = scope if scope == "/" else scope + "/"
                return scope if scope else "/"
    return "/"


def resolve_app_name(project: Path, cli_name: str | None) -> tuple[str, str]:
    """Return (name, short_name)."""
    if cli_name:
        name = cli_name.strip()
        short = name if len(name) <= 12 else name[:12]
        return name, short

    pkg = project / "package.json"
    if pkg.is_file():
        data = read_json(pkg)
        raw = str(data.get("name") or "").strip()
        if raw:
            # sasha-health-frontend → Sasha Health
            pretty = raw.replace("-frontend", "").replace("_", " ").replace("-", " ")
            pretty = " ".join(w.capitalize() for w in pretty.split())
            short = pretty if len(pretty) <= 12 else pretty.split()[0][:12]
            return pretty, short

    folder = project.name
    if folder in ("frontend", "web", "app", "public", "dist", "src"):
        folder = project.parent.name
    pretty = folder.replace("_", " ").replace("-", " ")
    pretty = " ".join(w.capitalize() for w in pretty.split())
    short = pretty if len(pretty) <= 12 else pretty[:12]
    return pretty, short


def asset_dir(project: Path) -> Path:
    """Where static PWA assets should live (copied/served as-is)."""
    if detect_vite(project) or (project / "public").is_dir():
        d = project / "public"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return project


def theme_from_html(index: Path | None) -> tuple[str, str]:
    theme, bg = DEFAULT_THEME, DEFAULT_BG
    if not index or not index.is_file():
        return theme, bg
    text = index.read_text(encoding="utf-8", errors="ignore")
    m = re.search(
        r'''<meta\s+name=["']theme-color["']\s+content=["']([^"']+)["']''',
        text,
        re.I,
    )
    if m:
        theme = m.group(1)
        bg = theme
    return theme, bg


# ── generators ─────────────────────────────────────────────────────────────


def build_manifest(
    *,
    name: str,
    short_name: str,
    theme: str,
    background: str,
    base: str,
    icons: list[dict[str, str]],
) -> dict[str, Any]:
    start = base if base.endswith("/") else base + "/"
    return {
        "name": name,
        "short_name": short_name,
        "description": f"{name} — Progressive Web App (Station make_pwa)",
        "start_url": start,
        "scope": start,
        "display": "standalone",
        "orientation": "any",
        "theme_color": theme,
        "background_color": background,
        "lang": "ru",
        "icons": icons,
        "make_pwa_version": SCRIPT_VERSION,
    }


def build_service_worker(*, cache_name: str, base: str, precache: list[str]) -> str:
    """Vanilla SW: cache-first for static, network-first for /api/."""
    precache_json = json.dumps(precache, ensure_ascii=False)
    # scope-aware: base may be /sh/
    return f"""/* service-worker.js — generated by make_pwa.py v{SCRIPT_VERSION}
 * Strategy:
 *   - cache-first  → static assets (js/css/img/font/ico/svg/woff2)
 *   - network-first → /api/* and navigations
 */
/* eslint-disable no-restricted-globals */
const CACHE_NAME = {json.dumps(cache_name)};
const BASE = {json.dumps(base)};
const PRECACHE = {precache_json};

self.addEventListener("install", (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  );
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  );
}});

function isApi(url) {{
  try {{
    const u = new URL(url);
    return u.pathname.includes("/api/") || u.pathname.endsWith("/api");
  }} catch (_) {{
    return false;
  }}
}}

function isStatic(request) {{
  const dest = request.destination;
  if (["style", "script", "image", "font", "worker"].includes(dest)) return true;
  const path = new URL(request.url).pathname;
  return /\\.(?:js|css|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|map)(?:\\?.*)?$/i.test(path);
}}

async function cacheFirst(request) {{
  const cached = await caches.match(request);
  if (cached) return cached;
  try {{
    const res = await fetch(request);
    if (res && res.ok && request.method === "GET") {{
      const copy = res.clone();
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, copy);
    }}
    return res;
  }} catch (err) {{
    const fallback = await caches.match(request);
    if (fallback) return fallback;
    throw err;
  }}
}}

async function networkFirst(request) {{
  try {{
    const res = await fetch(request);
    if (res && res.ok && request.method === "GET" && !isApi(request.url)) {{
      const copy = res.clone();
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, copy);
    }}
    return res;
  }} catch (err) {{
    const cached = await caches.match(request);
    if (cached) return cached;
    // offline shell
    const shell = await caches.match(new URL(BASE, self.location.origin).href);
    if (shell) return shell;
    throw err;
  }}
}}

self.addEventListener("fetch", (event) => {{
  const {{ request }} = event;
  if (request.method !== "GET") return;

  if (isApi(request.url)) {{
    event.respondWith(networkFirst(request));
    return;
  }}
  if (isStatic(request)) {{
    event.respondWith(cacheFirst(request));
    return;
  }}
  // documents / navigations
  if (request.mode === "navigate" || request.destination === "document") {{
    event.respondWith(networkFirst(request));
    return;
  }}
  event.respondWith(networkFirst(request));
}});
"""


def sw_register_snippet(base: str) -> str:
    # register with correct scope under base path
    sw_url = f"{base}service-worker.js" if base.endswith("/") else f"{base}/service-worker.js"
    scope = base if base.endswith("/") else base + "/"
    return f"""<!-- {SW_REG_MARKER} -->
<script>
  if ("serviceWorker" in navigator) {{
    window.addEventListener("load", function () {{
      navigator.serviceWorker.register({json.dumps(sw_url)}, {{ scope: {json.dumps(scope)} }})
        .then(function (reg) {{ console.info("[make_pwa] SW registered", reg.scope); }})
        .catch(function (err) {{ console.warn("[make_pwa] SW failed", err); }});
    }});
  }}
</script>
<!-- /{SW_REG_MARKER} -->
"""


def inject_html(
    index: Path,
    *,
    base: str,
    dry_run: bool,
    register_sw: bool = True,
) -> bool:
    text = index.read_text(encoding="utf-8")
    original = text
    manifest_href = f"{base}manifest.json" if base.endswith("/") else f"{base}/manifest.json"
    # relative href is safer for Vite base rewriting — use absolute path from root
    link_tag = (
        f'    <link rel="manifest" href="{manifest_href}" '
        f'data-{MANIFEST_LINK_MARKER.replace(":", "-")} />'
    )

    # remove previous make_pwa injections
    text = re.sub(
        r"\s*<!-- " + re.escape(MANIFEST_LINK_MARKER) + r" -->.*?<!-- /"
        + re.escape(MANIFEST_LINK_MARKER) + r" -->\s*",
        "\n",
        text,
        flags=re.S,
    )
    text = re.sub(
        r"\s*<!-- " + re.escape(SW_REG_MARKER) + r" -->.*?<!-- /"
        + re.escape(SW_REG_MARKER) + r" -->\s*",
        "\n",
        text,
        flags=re.S,
    )
    # also strip older single-line link we may have injected
    text = re.sub(
        r'\s*<link\s+rel=["\']manifest["\'][^>]*data-make_pwa-manifest[^>]*/?>\s*',
        "\n",
        text,
        flags=re.I,
    )

    # inject manifest link in <head>
    if re.search(r'rel=["\']manifest["\']', text, re.I):
        log("index.html already has a manifest link — leaving existing, adding make_pwa marker if missing")
        # ensure ours is present too only if none from make_pwa
        if "data-make_pwa-manifest" not in text and MANIFEST_LINK_MARKER not in text:
            # update href of first manifest link if empty project
            pass
        else:
            pass
    else:
        if re.search(r"</head>", text, re.I):
            text = re.sub(
                r"</head>",
                f"    <!-- {MANIFEST_LINK_MARKER} -->\n{link_tag}\n"
                f"    <!-- /{MANIFEST_LINK_MARKER} -->\n  </head>",
                text,
                count=1,
                flags=re.I,
            )
        else:
            text = f"<!-- {MANIFEST_LINK_MARKER} -->\n{link_tag}\n<!-- /{MANIFEST_LINK_MARKER} -->\n" + text

    # Always ensure make_pwa manifest link if we didn't leave a generic one
    if "data-make_pwa-manifest" not in text and MANIFEST_LINK_MARKER not in text:
        if re.search(r"</head>", text, re.I):
            text = re.sub(
                r"</head>",
                f"    <!-- {MANIFEST_LINK_MARKER} -->\n{link_tag}\n"
                f"    <!-- /{MANIFEST_LINK_MARKER} -->\n  </head>",
                text,
                count=1,
                flags=re.I,
            )

    # inject SW registration before </body> (skip if vite-plugin-pwa owns SW)
    if register_sw:
        snippet = sw_register_snippet(base)
        if re.search(r"</body>", text, re.I):
            text = re.sub(r"</body>", snippet + "\n  </body>", text, count=1, flags=re.I)
        else:
            text = text + "\n" + snippet
    else:
        log("skip SW register inject (vite-plugin-pwa / workbox present)")

    # apple meta hints (nice-to-have, idempotent)
    if "apple-mobile-web-app-capable" not in text.lower():
        meta = (
            '    <meta name="apple-mobile-web-app-capable" content="yes" />\n'
            '    <meta name="mobile-web-app-capable" content="yes" />\n'
        )
        if re.search(r"</head>", text, re.I):
            text = re.sub(r"</head>", meta + "  </head>", text, count=1, flags=re.I)

    if text == original:
        log(f"index.html unchanged: {index}")
        return False
    if dry_run:
        log(f"[dry-run] would update {index}")
        return True
    index.write_text(text, encoding="utf-8")
    log(f"updated {index}")
    return True


# ── icons ──────────────────────────────────────────────────────────────────


def ensure_icons(assets: Path, *, dry_run: bool) -> list[dict[str, str]]:
    """Ensure icon-192 and icon-512 exist; return manifest icon entries."""
    needed = {
        192: ["favicon-192x192.png", "icon-192.png", "icon-192.svg", "pwa-192.png"],
        512: ["favicon-512x512.png", "icon-512.png", "icon-512.svg", "pwa-512.png"],
    }
    found: dict[int, str] = {}

    for size, names in needed.items():
        for n in names:
            p = assets / n
            if p.is_file():
                found[size] = n
                break
        # search project parent public
        if size not in found:
            for n in names:
                # already only assets dir
                pass

    # copy from station templates
    for size in (192, 512):
        if size in found:
            continue
        for cand in (
            STATION_ICON_TEMPLATES / f"icon-{size}.svg",
            STATION_ICON_TEMPLATES / f"icon-{size}.png",
            STATION_ICON_TEMPLATES / f"favicon-{size}x{size}.png",
        ):
            if cand.is_file():
                dest_name = f"icon-{size}{cand.suffix}"
                dest = assets / dest_name
                if not dry_run:
                    shutil.copy2(cand, dest)
                found[size] = dest_name
                log(f"copied template icon → {dest}")
                break

    # generate SVG placeholders
    for size in (192, 512):
        if size in found:
            continue
        dest_name = f"icon-{size}.svg"
        dest = assets / dest_name
        svg = _placeholder_svg(size)
        if not dry_run:
            dest.write_text(svg, encoding="utf-8")
        found[size] = dest_name
        log(f"generated SVG placeholder → {dest}")

    icons: list[dict[str, str]] = []
    for size in (192, 512):
        src = found[size]
        mime = "image/svg+xml" if src.endswith(".svg") else "image/png"
        entry: dict[str, str] = {
            "src": src,
            "sizes": f"{size}x{size}",
            "type": mime,
        }
        if size == 512:
            entry["purpose"] = "any maskable"
        icons.append(entry)
    return icons


def _placeholder_svg(size: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#007AFF"/>
      <stop offset="100%" stop-color="#5AC8FA"/>
    </linearGradient>
  </defs>
  <rect width="{size}" height="{size}" rx="{max(8, size // 5)}" fill="url(#g)"/>
  <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle"
        font-family="-apple-system, system-ui, sans-serif" font-weight="700"
        font-size="{max(24, size // 4)}" fill="#ffffff">PWA</text>
</svg>
"""


# ── main pipeline ──────────────────────────────────────────────────────────


def make_pwa(
    project: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    name: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    if not project.is_dir():
        die(f"not a directory: {project}")

    index = find_index_html(project)
    if not index:
        die(f"index.html not found under {project}")

    assets = asset_dir(project)
    base_path = detect_base_path(project, base)
    app_name, short_name = resolve_app_name(project, name)
    theme, bg = theme_from_html(index)
    vite = detect_vite(project)

    print(f"make_pwa v{SCRIPT_VERSION}")
    print(f"  project : {project}")
    print(f"  index   : {index}")
    print(f"  assets  : {assets}")
    print(f"  base    : {base_path}")
    print(f"  name    : {app_name} ({short_name})")
    print(f"  vite    : {vite}")

    icons = ensure_icons(assets, dry_run=dry_run)
    manifest = build_manifest(
        name=app_name,
        short_name=short_name,
        theme=theme,
        background=bg,
        base=base_path,
        icons=icons,
    )

    man_path = assets / "manifest.json"
    if man_path.is_file() and not force:
        existing = read_json(man_path)
        # merge: keep custom name if richer, but ensure display/icons/start_url
        if existing.get("name") and not name:
            manifest["name"] = existing["name"]
            manifest["short_name"] = existing.get("short_name") or short_name
        if existing.get("description"):
            manifest["description"] = existing["description"]
        if existing.get("theme_color"):
            manifest["theme_color"] = existing["theme_color"]
        if existing.get("background_color"):
            manifest["background_color"] = existing["background_color"]
        # prefer existing icons if valid
        if isinstance(existing.get("icons"), list) and existing["icons"]:
            # keep if files exist
            ok_icons = []
            for ic in existing["icons"]:
                src = ic.get("src") if isinstance(ic, dict) else None
                if src and (assets / Path(src).name).is_file():
                    # normalize to basename for public root
                    ic = dict(ic)
                    ic["src"] = Path(src).name
                    ok_icons.append(ic)
            if ok_icons:
                manifest["icons"] = ok_icons

    # ensure display standalone always
    manifest["display"] = "standalone"
    manifest["start_url"] = base_path
    manifest["scope"] = base_path

    if dry_run:
        log(f"[dry-run] would write {man_path}")
    else:
        man_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        log(f"wrote {man_path}")

    # service worker
    cache_slug = re.sub(r"[^\w]+", "-", short_name.lower()).strip("-") or "app"
    precache = [base_path, f"{base_path}manifest.json"]
    for ic in manifest["icons"]:
        src = ic.get("src") if isinstance(ic, dict) else None
        if src:
            precache.append(f"{base_path}{Path(src).name}")
    # de-dupe
    seen: set[str] = set()
    precache_u = []
    for u in precache:
        if u not in seen:
            seen.add(u)
            precache_u.append(u)

    sw_body = build_service_worker(
        cache_name=f"make-pwa-{cache_slug}-v1",
        base=base_path,
        precache=precache_u,
    )
    sw_path = assets / "service-worker.js"
    if dry_run:
        log(f"[dry-run] would write {sw_path}")
    else:
        sw_path.write_text(sw_body, encoding="utf-8")
        log(f"wrote {sw_path}")

    has_vite_pwa = detect_vite_plugin_pwa(project)
    # Always write service-worker.js as portable baseline; avoid double-register
    # when vite-plugin-pwa injects workbox SW at build time.
    inject_html(
        index,
        base=base_path,
        dry_run=dry_run,
        register_sw=not has_vite_pwa,
    )
    if has_vite_pwa:
        log("vite-plugin-pwa detected — production SW remains workbox (sw.js)")

    # validate
    report = validate(
        assets,
        index,
        base_path,
        require_sw_register=not has_vite_pwa,
    )
    print("\nValidation:")
    for k, v in report.items():
        print(f"  {'✓' if v else '✗'} {k}")

    if not all(report.values()):
        die("validation failed", code=2)

    print("\nDone. Install tips:")
    print("  · HTTPS or localhost required for SW")
    print("  · Chrome/Edge: install icon in address bar / menu")
    print("  · iOS Safari: Share → Add to Home Screen")
    if vite:
        print("  · Vite: re-run `npm run build` so public/ assets land in dist/")
    return {"manifest": str(man_path), "sw": str(sw_path), "index": str(index), "base": base_path}


def validate(
    assets: Path,
    index: Path,
    base: str,
    *,
    require_sw_register: bool = True,
) -> dict[str, bool]:
    man = assets / "manifest.json"
    sw = assets / "service-worker.js"
    ok_man = False
    ok_sw = False
    ok_html = False
    ok_icons = False

    if man.is_file():
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
            ok_man = (
                data.get("display") == "standalone"
                and bool(data.get("name"))
                and bool(data.get("icons"))
            )
        except json.JSONDecodeError:
            ok_man = False

    if sw.is_file():
        body = sw.read_text(encoding="utf-8")
        ok_sw = (
            "cacheFirst" in body
            and "networkFirst" in body
            and "addEventListener" in body
            and len(body) > 200
        )

    if index.is_file():
        html = index.read_text(encoding="utf-8")
        has_manifest = 'rel="manifest"' in html or "rel='manifest'" in html
        has_sw = "serviceWorker" in html or "registerSW" in html or not require_sw_register
        ok_html = has_manifest and has_sw

    # icons listed in manifest exist
    if ok_man:
        data = json.loads(man.read_text(encoding="utf-8"))
        ok_icons = all(
            (assets / Path(ic["src"]).name).is_file()
            for ic in data.get("icons", [])
            if isinstance(ic, dict) and ic.get("src")
        )

    return {
        "manifest.json valid": ok_man,
        "service-worker.js valid": ok_sw,
        "index.html injected": ok_html,
        "icons present": ok_icons,
        f"base={base}": bool(base.startswith("/")),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Make a Station web project installable as a PWA",
    )
    ap.add_argument(
        "project",
        type=str,
        help="Path to project (e.g. ~/Station/mini_apps_studio/apps/sasha-health/frontend)",
    )
    ap.add_argument("--force", action="store_true", help="Overwrite existing manifest fields")
    ap.add_argument("--dry-run", action="store_true", help="Print actions only")
    ap.add_argument("--name", type=str, default=None, help="App display name")
    ap.add_argument(
        "--base",
        type=str,
        default=None,
        help="URL base path (default: detect from vite.config or /)",
    )
    args = ap.parse_args(argv)

    project = expand(args.project)
    try:
        make_pwa(
            project,
            force=args.force,
            dry_run=args.dry_run,
            name=args.name,
            base=args.base,
        )
    except SystemExit as e:
        return int(e.code) if e.code is not None else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
