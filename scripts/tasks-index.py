#!/usr/bin/env python3
"""生成并校验 tasks/INDEX.md —— 执行任务索引。

索引是派生视图，不是事实源：每个字段都取自计划目录里的已有文件。
状态取自 STATUS.md，目标取自 plan.md，本脚本不产生任何新信息。

用法：
    python scripts/tasks-index.py            重写 tasks/INDEX.md
    python scripts/tasks-index.py --check    只校验，不一致退出码 1
    python scripts/tasks-index.py --stdout   打印到标准输出，不写文件

零第三方依赖。解析 plan.md / STATUS.md / analysis.md 用正则，不解析 YAML。
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANS = ROOT / "tasks" / "plans"
INDEX = ROOT / "tasks" / "INDEX.md"

ACTIVE = ("Planned", "In Progress", "Blocked")
CLOSED = ("Verified", "Completed", "Archived")
ALL_STATUS = ACTIVE + CLOSED

HEADER = """<!-- 本文件由 scripts/tasks-index.py 生成，不要手改。 -->
<!-- 要改状态请改对应计划的 STATUS.md，改目标请改 plan.md，然后运行 python scripts/tasks-index.py -->
"""


class Problem(Exception):
    """单个计划目录的数据问题，收集后统一报出。"""


def text_of(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def metadata(plan_text: str) -> dict[str, str]:
    """解析 plan.md 的 ## Metadata 段（`- Key: value` 形式）。"""
    block = re.search(r"^##\s*Metadata\s*$(.*?)(?=^##\s|\Z)", plan_text, re.M | re.S)
    if not block:
        raise Problem("plan.md 缺少 ## Metadata 段")
    out: dict[str, str] = {}
    for line in block.group(1).splitlines():
        m = re.match(r"^\s*-\s*([A-Za-z][A-Za-z ]*?)\s*[:：]\s*(.*)$", line)
        if m:
            out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def goal_of(plan_text: str) -> str:
    """取 ## 目标 段的第一段文字，压成一行。"""
    block = re.search(r"^##\s*目标\s*$(.*?)(?=^##\s|\Z)", plan_text, re.M | re.S)
    if not block:
        raise Problem("plan.md 缺少 ## 目标 段")
    body = block.group(1).strip()
    if not body:
        raise Problem("plan.md 的 ## 目标 段是空的")
    first = re.split(r"\n\s*\n", body)[0]
    return " ".join(first.split())


def status_of(status_text: str) -> tuple[str, str]:
    """返回 (状态, 最后更新日期)。格式错误直接报错，不猜。"""
    s = re.search(r"^Current Status:\s*(.+?)\s*$", status_text, re.M)
    if not s:
        raise Problem("STATUS.md 第一行不是 `Current Status: <状态>`")
    value = s.group(1)
    if value not in ALL_STATUS:
        raise Problem(f"STATUS.md 的状态 `{value}` 不在允许集合 {list(ALL_STATUS)}")
    u = re.search(r"^Updated:\s*(\d{4}-\d{2}-\d{2})", status_text, re.M)
    updated = u.group(1) if u else "-"
    return value, updated


def pretty_date(name: str) -> str:
    """目录名开头的 YYYYMMDD -> YYYY-MM-DD；不符合则返回 -。"""
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else "-"


def conclusion_of(analysis_text: str) -> str:
    """没有 plan.md 的目录（not-a-bug / design-gap）取 analysis.md 的结论。"""
    m = re.search(r"^-\s*结论\s*[:：]\s*(.+)$", analysis_text, re.M)
    if m:
        raw = m.group(1)
        for key in ("not-a-bug", "design-gap", "needs-info", "confirmed"):
            if key in raw:
                return key
    return "未判定"


def cell(value: str) -> str:
    return value.replace("|", "\\|").strip() or "-"


def table(rows: list[list[str]], columns: list[str]) -> str:
    head = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def collect(problems: list[str]) -> tuple[list, list, list]:
    active, closed, unresolved = [], [], []
    if not PLANS.is_dir():
        return active, closed, unresolved

    for topic_dir in sorted(p for p in PLANS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        for plan_dir in sorted(p for p in topic_dir.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
            plan = plan_dir / "plan.md"
            status_file = plan_dir / "STATUS.md"
            label = f"{topic_dir.name}/{plan_dir.name}"

            if not plan.exists():
                analysis = plan_dir / "analysis.md"
                if analysis.exists():
                    unresolved.append([
                        pretty_date(plan_dir.name), plan_dir.name, topic_dir.name,
                        conclusion_of(text_of(analysis)),
                    ])
                else:
                    problems.append(f"{label}: 既没有 plan.md 也没有 analysis.md")
                continue

            try:
                meta = metadata(text_of(plan))
                goal = goal_of(text_of(plan))
            except Problem as e:
                problems.append(f"{label}: {e}")
                continue

            if not status_file.exists():
                problems.append(f"{label}: 缺少 STATUS.md")
                continue
            try:
                status, updated = status_of(text_of(status_file))
            except Problem as e:
                problems.append(f"{label}: {e}")
                continue

            pid = meta.get("plan id", "")
            if pid and pid != plan_dir.name:
                problems.append(f"{label}: Metadata.Plan ID `{pid}` 与目录名不一致")
                continue

            created = meta.get("created", "")
            prefix = re.match(r"^(\d{4})(\d{2})(\d{2})-", plan_dir.name)
            if not created:
                problems.append(f"{label}: Metadata 缺少 Created")
                continue
            if prefix:
                from_name = f"{prefix.group(1)}-{prefix.group(2)}-{prefix.group(3)}"
                if from_name != created:
                    problems.append(f"{label}: 目录日期 {from_name} 与 Metadata.Created {created} 不一致")
                    continue
            else:
                problems.append(f"{label}: 目录名不是 YYYYMMDD- 开头")
                continue

            kind = meta.get("type", "")
            if not kind:
                problems.append(f"{label}: Metadata 缺少 Type")
                continue

            row = [created, plan_dir.name, kind, topic_dir.name, goal, status, updated]
            (active if status in ACTIVE else closed).append(row)

    active.sort(key=lambda r: (r[0], r[1]), reverse=True)
    closed.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return active, closed, unresolved


def render(active, closed, unresolved, with_age: bool) -> str:
    out = [HEADER]
    out.append(f"<!-- 进行中 {len(active)} · 已收口 {len(closed)} · 未成立 {len(unresolved)} -->\n")

    cols = ["日期", "plan-id", "Type", "模块", "目标", "状态", "最后更新"]
    cols_age = cols + ["停留"]

    rows = active
    if with_age:
        now = dt.date.today()
        rows = [r + [(f"{(now - dt.date.fromisoformat(r[6])).days}d" if r[6] != "-" else "-")] for r in active]

    out.append("## 进行中\n")
    out.append(table(rows, cols_age if with_age else cols) if active else "（当前没有进行中的计划）")
    out.append("")
    out.append("## 已收口\n")
    out.append(table(closed, cols) if closed else "（还没有已收口的计划）")
    out.append("")
    if unresolved:
        out.append("## 未成立的问题\n")
        out.append(table(unresolved, ["日期", "plan-id", "模块", "结论"]))
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="生成或校验 tasks/INDEX.md")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="只校验，不一致退出码 1")
    mode.add_argument("--stdout", action="store_true", help="打印，不写文件")
    args = ap.parse_args()

    problems: list[str] = []
    active, closed, unresolved = collect(problems)

    if problems:
        print("计划目录数据有问题，未生成索引：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    body = render(active, closed, unresolved, with_age=args.stdout)

    if args.stdout:
        print(body, end="")
        return 0

    if args.check:
        if not INDEX.exists():
            print(f"缺少 {INDEX.relative_to(ROOT)}，请运行 python scripts/tasks-index.py", file=sys.stderr)
            return 1
        current = text_of(INDEX)
        if current != body:
            print("索引与计划目录不一致：", file=sys.stderr)
            old = current.rstrip("\n").splitlines()
            new = body.rstrip("\n").splitlines()
            import difflib
            diff = list(difflib.unified_diff(old, new, fromfile="tasks/INDEX.md", tofile="重新生成", lineterm=""))
            for line in diff[:60]:
                print(line, file=sys.stderr)
            print("\n请运行 python scripts/tasks-index.py 后重新提交。", file=sys.stderr)
            return 1
        print(f"索引一致：进行中 {len(active)} · 已收口 {len(closed)}")
        return 0

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(body, encoding="utf-8")
    print(f"已生成 {INDEX.relative_to(ROOT)}：进行中 {len(active)} · 已收口 {len(closed)} · 未成立 {len(unresolved)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
