"""Safe hosts-file helper for focus mode."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

DEFAULT_HOSTS_PATH = Path("/etc/hosts")
BEGIN_MARKER = "# >>> OMARCHY_FOCUS START"
END_MARKER = "# <<< OMARCHY_FOCUS END"
META_PREFIX = "# OMARCHY_FOCUS_META "
BLOCK_ADDRESSES = ("0.0.0.0", "::1")
BLOCK_ADDRESS_ALIASES = {"127.0.0.1", "0.0.0.0", "::1", "::"}


@dataclass(slots=True)
class HostsStatus:
    active: bool = False
    session_id: str | None = None
    strict: bool = False
    started_at: str | None = None
    owner: str | None = None
    sites: tuple[str, ...] = ()
    readable: bool = True


def _site_variants(site: str) -> list[str]:
    item = site.strip().lower()
    if not item:
        return []
    variants = [item]
    if item.startswith("www.") and "." in item[4:]:
        variants.append(item[4:])
    elif item.count(".") == 1:
        variants.append(f"www.{item}")
    return variants


def _dedupe_sites(sites: Iterable[str]) -> list[str]:
    clean = []
    seen: set[str] = set()
    for site in sites:
        for item in _site_variants(site):
            if item in seen:
                continue
            seen.add(item)
            clean.append(item)
    return clean


def inspect_hosts_file(hosts_path: Path = DEFAULT_HOSTS_PATH) -> HostsStatus:
    if not hosts_path.exists():
        return HostsStatus()
    try:
        lines = hosts_path.read_text(encoding="utf-8").splitlines()
    except PermissionError:
        return HostsStatus(readable=False)
    try:
        start = lines.index(BEGIN_MARKER)
        end = lines.index(END_MARKER, start + 1)
    except ValueError:
        return HostsStatus()

    payload = HostsStatus(active=True)
    block_lines = lines[start + 1 : end]
    if block_lines and block_lines[0].startswith(META_PREFIX):
        metadata = json.loads(block_lines[0][len(META_PREFIX) :])
        payload.session_id = metadata.get("session_id")
        payload.strict = bool(metadata.get("strict"))
        payload.started_at = metadata.get("started_at")
        payload.owner = metadata.get("owner")
        block_lines = block_lines[1:]

    sites: list[str] = []
    for line in block_lines:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] in BLOCK_ADDRESS_ALIASES:
            sites.extend(parts[1:])
    payload.sites = tuple(_dedupe_sites(sites))
    return payload


def strip_managed_block(content: str) -> str:
    lines = content.splitlines()
    cleaned: list[str] = []
    skip = False
    for line in lines:
        if line == BEGIN_MARKER:
            skip = True
            continue
        if skip and line == END_MARKER:
            skip = False
            continue
        if not skip:
            cleaned.append(line)
    return "\n".join(cleaned).rstrip() + "\n"


def render_managed_block(
    *,
    session_id: str,
    sites: Iterable[str],
    strict: bool,
    started_at: str,
    owner: str,
) -> str:
    metadata = {
        "session_id": session_id,
        "strict": strict,
        "started_at": started_at,
        "owner": owner,
    }
    expanded_sites = _dedupe_sites(sites)
    lines = [BEGIN_MARKER, META_PREFIX + json.dumps(metadata, sort_keys=True)]
    for address in BLOCK_ADDRESSES:
        lines.append(f"{address} {' '.join(expanded_sites)}")
    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def apply_blocks(
    *,
    hosts_path: Path = DEFAULT_HOSTS_PATH,
    session_id: str,
    sites: Iterable[str],
    strict: bool,
    started_at: str,
    owner: str,
) -> HostsStatus:
    content = hosts_path.read_text(encoding="utf-8") if hosts_path.exists() else ""
    cleaned = strip_managed_block(content)
    managed = render_managed_block(
        session_id=session_id,
        sites=sites,
        strict=strict,
        started_at=started_at,
        owner=owner,
    )
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    _atomic_write(hosts_path, cleaned + ("\n" if cleaned.strip() else "") + managed)
    return inspect_hosts_file(hosts_path)


def clear_blocks(hosts_path: Path = DEFAULT_HOSTS_PATH) -> HostsStatus:
    content = hosts_path.read_text(encoding="utf-8") if hosts_path.exists() else ""
    _atomic_write(hosts_path, strip_managed_block(content))
    return inspect_hosts_file(hosts_path)


def _require_root(action: str, hosts_path: Path) -> None:
    if action in {"apply", "clear"} and hosts_path == DEFAULT_HOSTS_PATH and os.geteuid() != 0:
        raise SystemExit("Root privileges required to modify /etc/hosts")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clar Focus hosts helper")
    parser.add_argument("--hosts-file", default=str(DEFAULT_HOSTS_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--session-id", required=True)
    apply_parser.add_argument("--strict", action="store_true")
    apply_parser.add_argument("--started-at", required=True)
    apply_parser.add_argument("--owner", default=os.environ.get("SUDO_USER") or os.environ.get("USER") or "unknown")
    apply_parser.add_argument("sites", nargs="+")

    clear_parser = subparsers.add_parser("clear")
    clear_parser.add_argument("--json", action="store_true")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    hosts_path = Path(args.hosts_file).expanduser()
    _require_root(args.command, hosts_path)

    if args.command == "apply":
        status = apply_blocks(
            hosts_path=hosts_path,
            session_id=args.session_id,
            sites=args.sites,
            strict=args.strict,
            started_at=args.started_at,
            owner=args.owner,
        )
    elif args.command == "clear":
        status = clear_blocks(hosts_path)
    else:
        status = inspect_hosts_file(hosts_path)

    if getattr(args, "json", False) or args.command in {"apply", "clear", "status"}:
        print(json.dumps(asdict(status), ensure_ascii=False))
    else:
        print("active" if status.active else "inactive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
