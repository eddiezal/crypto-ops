#!/usr/bin/env python3
"""
zip_clean.py - Create a clean .zip of crypto-ops for sharing.
- Whitelists key folders (apps, service, configs, win, requirements.txt, Procfile).
- Optionally includes scripts/.
- Excludes venvs, caches, plans, scratch, logs, .env files, backup files.
- Replaces configs/policy.rebalancer.json with a safe sample.
- Writes MANIFEST.json into the zip.
- Stdlib only. Cross-platform.
"""

import argparse, os, json, time, tempfile, shutil, zipfile, subprocess, sys
from pathlib import Path
from typing import List

# ---------- helpers

def _git_commit(root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(root), stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return "n/a"

def _now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _copy_file(src: Path, dst: Path) -> None:
    _ensure_dir(dst.parent)
    shutil.copy2(str(src), str(dst))

def _copy_tree(src: Path, dst: Path) -> None:
    """
    Copy directory using an ignore filter to drop caches and noise.
    """
    def _ignore(dirpath, names):
        DIR_SKIP = {
            "__pycache__", ".pytest_cache", ".mypy_cache",
            ".venv", ".git", ".vscode", ".idea", "plans", "scratch", "node_modules"
        }
        FILE_SUFFIX_SKIP = (".pyc", ".pyo", ".pyd", ".log", ".tmp", ".swp", ".bak", ".orig", "~")
        FILE_NAME_SKIP   = {".DS_Store", ".env", ".env.local", ".env.prod", ".env.dev"}

        ignored: List[str] = []
        dp = Path(dirpath)

        for n in names:
            p = dp / n
            if p.is_dir() and n in DIR_SKIP:
                ignored.append(n)
                continue
            if p.is_file():
                if n in FILE_NAME_SKIP or n.startswith(".env."):
                    ignored.append(n)
                    continue
                for suf in FILE_SUFFIX_SKIP:
                    if n.endswith(suf):
                        ignored.append(n)
                        break
        return set(ignored)

    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=_ignore)

def _zip_dir(src_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(str(zip_path), "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in src_dir.rglob("*"):
            if p.is_file():
                z.write(str(p), arcname=str(p.relative_to(src_dir)))

# ---------- main assemble

def make_clean_zip(root: Path, outdir: Path, include_scripts: bool) -> Path:
    if not root.exists():
        raise SystemExit(f"Root not found: {root}")

    stage = Path(tempfile.gettempdir()) / f"cryptoops_stage_{_now_stamp()}"
    if stage.exists():
        shutil.rmtree(stage, ignore_errors=True)
    _ensure_dir(stage)

    include = ["apps", "service", "configs", "win", "requirements.txt", "Procfile"]
    if include_scripts:
        include.append("scripts")

    # Copy whitelisted items
    for item in include:
        src = root / item
        dst = stage / item
        if not src.exists():
            print(f"[skip] missing: {src}")
            continue
        if src.is_dir():
            print(f"[copy dir]  {src} -> {dst}")
            _copy_tree(src, dst)
        else:
            print(f"[copy file] {src} -> {dst}")
            _copy_file(src, dst)

    # Replace policy with a safe sample
    real_policy   = stage / "configs" / "policy.rebalancer.json"
    sample_policy = stage / "configs" / "policy.rebalancer.sample.json"
    if real_policy.exists():
        print(f"[remove] {real_policy}")
        real_policy.unlink(missing_ok=True)
    if not sample_policy.exists():
        _ensure_dir(sample_policy.parent)
        sample_policy.write_text(
            json.dumps({
                "targets_trading": {"BTC": 0.44, "ETH": 0.24, "SOL": 0.17, "LINK": 0.15},
                "band_dynamic": {"enabled": True, "base": 0.035, "min": 0.02, "max": 0.08,
                                 "lookback_days": 30, "target_ann_vol": 0.35},
                "cash": {"auto_deploy_usd_per_day": 8000, "floor_usd": 40000,
                         "pro_rata_underweights": True},
                "momentum": {"enabled": True, "lookback_days": 60,
                             "tilt_strength": 1.0, "tilt_max_pct": 0.08},
                "satellite_gate": {"enabled": True, "symbols": ["SOL","LINK"],
                                   "threshold_ret": 0.02, "lookback_days": 60,
                                   "max_weight_pct": {"SOL": 0.2, "LINK": 0.2}}
            }, separators=(",", ":")),
            encoding="utf-8"
        )
        print(f"[write]  {sample_policy}")

    # Manifest
    files = [p for p in stage.rglob("*") if p.is_file()]
    manifest = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": _git_commit(root),
        "root": str(root),
        "includes": include,
        "excludes": ["__pycache__", ".pytest_cache", ".mypy_cache", ".venv", ".git",
                     ".vscode", ".idea", "plans", "scratch", "*.pyc", "*.pyo", "*.pyd",
                     ".DS_Store", "*.log", "*.tmp", "*.swp", ".env", ".env.*", "*.bak", "*.orig", "*~"],
        "total_files": len(files),
        "total_bytes": sum(p.stat().st_size for p in files),
    }
    (stage / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Zip it
    _ensure_dir(outdir)
    zip_path = outdir / f"crypto-ops-clean_{_now_stamp()}.zip"
    _zip_dir(stage, zip_path)

    # Cleanup
    shutil.rmtree(stage, ignore_errors=True)

    print(f"\n=== DONE ===\nCreated: {zip_path}")
    return zip_path

def parse_args():
    here = Path(__file__).resolve().parent
    default_root = (here / "crypto-ops") if (here / "crypto-ops").exists() else here
    parser = argparse.ArgumentParser(description="Make a clean shareable zip of crypto-ops.")
    parser.add_argument("--root", default=str(default_root),
                        help="Path to the crypto-ops repository root")
    parser.add_argument("--outdir", default=str(here),
                        help="Directory to write the .zip into")
    parser.add_argument("--include-scripts", action="store_true",
                        help="Also include the scripts/ folder")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    root = Path(args.root).resolve()
    outdir = Path(args.outdir).resolve()
    try:
        make_clean_zip(root, outdir, include_scripts=args.include_scripts)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
