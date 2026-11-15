#!/usr/bin/env python3
"""回归登记表与回归用例的双向一致性校验。

用法（仓库根执行）：
    uv run pytest -m regression --collect-only -q | grep '::' > /tmp/collected.txt
    uv run python scripts/check_regression_registry.py --collected /tmp/collected.txt

校验四项：
    1. 结构完整、枚举值合法、id 不重复；
    2. 每条用例的文件存在；
    3. 缺陷 id 出现在对应用例文件里（防止改了用例忘了改表）；
    4. 后端用例的 pytest 节点确实被收集到（防止用例被删或漏打标记）。

退出码 0 = 一致；1 = 有问题（CI 应阻断）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "regression" / "registry.yaml"

REQUIRED = {
    "id", "title", "severity", "source", "found_at",
    "root_cause", "cases", "reverse_verified", "status",
}
SEVERITY = {"critical", "high", "medium", "low"}
SOURCE = {"defect", "incident", "behavior-change", "contract"}
STATUS = {"active", "pending", "retired"}

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def repo_relative(node: str) -> str:
    """把 pytest 节点 ID 归一到仓库相对路径。

    pytest 在 backend/ 下收集，节点里只有 tests/...；registry 写 backend/tests/...。
    """
    path, sep, rest = node.partition("::")
    candidate = ROOT / path
    if not candidate.exists():
        candidate = ROOT / "backend" / path
    try:
        return f"{candidate.relative_to(ROOT)}{sep}{rest}"
    except ValueError:
        return node


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collected", help="pytest --collect-only 的输出文件")
    args = parser.parse_args()

    if not REGISTRY.exists():
        print(f"ERROR  找不到 {REGISTRY.relative_to(ROOT)}")
        return 1

    entries = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or []
    if not isinstance(entries, list):
        print("ERROR  registry.yaml 顶层必须是列表")
        return 1

    collected: set[str] | None = None
    if args.collected:
        raw = Path(args.collected).read_text(encoding="utf-8").splitlines()
        collected = {repo_relative(x.strip()) for x in raw if "::" in x}
        if not collected:
            err("--collected 为空，确认 pytest 是否加了 -m regression")

    seen: set[str] = set()
    for entry in entries:
        ident = entry.get("id", "<无 id>")
        if ident in seen:
            err(f"{ident}: id 重复")
        seen.add(ident)

        missing = REQUIRED - set(entry)
        if missing:
            err(f"{ident}: 缺字段 {sorted(missing)}")
            continue

        if entry["severity"] not in SEVERITY:
            err(f"{ident}: severity 非法 {entry['severity']}")
        if entry["source"] not in SOURCE:
            err(f"{ident}: source 非法 {entry['source']}")
        if entry["status"] not in STATUS:
            err(f"{ident}: status 非法 {entry['status']}")
        if not entry["cases"]:
            err(f"{ident}: cases 为空")
        if entry["reverse_verified"] and not entry.get("reverse_verified_at"):
            err(f"{ident}: reverse_verified 为 true 但缺 reverse_verified_at")
        if not entry["reverse_verified"] and not entry.get("note"):
            err(f"{ident}: 未反向验证但 note 没写原因")
        if entry["status"] == "retired" and not entry.get("note"):
            err(f"{ident}: retired 条目必须写 note（理由与替代条目）")

        key = str(ident)
        candidates = {
            key,                                  # BUG-1234 / INC-2026-03-11
            key.lstrip("#"),                      # #1234
            re.sub(r"^[A-Za-z]+-", "", key),      # 1234
            re.sub(r"\D", "", key),               # 1234 / 20260311
        }
        for case in entry["cases"]:
            node = case.get("path", "")
            path = ROOT / node.split("::")[0]
            if not node or not path.exists():
                err(f"{ident}: 用例文件不存在 {node}")
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            if not any(c and c in content for c in candidates):
                err(f"{ident}: {path.relative_to(ROOT)} 里找不到编号 {key}")
            if collected is not None and "backend/tests" in str(path.relative_to(ROOT)):
                if repo_relative(node) not in collected:
                    err(f"{ident}: 节点未被 pytest 收集到 {node}")

    for msg in errors:
        print(f"ERROR  {msg}")
    active = sum(1 for e in entries if e.get("status") == "active")
    print(f"共 {len(entries)} 条记录，active {active} 条，问题 {len(errors)} 个")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
