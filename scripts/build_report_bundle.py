"""Build a retrospection bundle for a requested period.

Reads requests/*.md files containing a line `period: YYYY-MM-DD..YYYY-MM-DD`,
concatenates the period's entries, and writes UTF-8 parts of at most
MAX_PART_BYTES each under analysis/bundles/<period>/ so ChatGPT can read a
few files instead of dozens (single-file reads truncate around 3K tokens).
The request file is rewritten with the result status. No dependencies.
"""

import re
import sys
from pathlib import Path

MAX_PART_BYTES = 7000
PERIOD_RE = re.compile(r"^period:\s*(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})\s*$", re.M)

def split_utf8(data: bytes, budget: int) -> list[bytes]:
    parts, i = [], 0
    while i < len(data):
        j = min(i + budget, len(data))
        while j > i and j < len(data) and (data[j] & 0xC0) == 0x80:
            j -= 1
        parts.append(data[i:j])
        i = j
    return parts

processed = False
for req in sorted(Path("requests").glob("*.md")):
    text = req.read_text(encoding="utf-8")
    if "status: done" in text or "status: error" in text:
        continue
    m = PERIOD_RE.search(text)
    if not m:
        req.write_text(text.rstrip() + "\n\nstatus: error\nreason: period line not found "
                       "(expected `period: YYYY-MM-DD..YYYY-MM-DD`)\n", encoding="utf-8")
        processed = True
        continue
    start, end = m.group(1), m.group(2)
    days = []
    for p in sorted(Path("entries").glob("[0-9]*/[0-9]*/*.md")):
        day = p.stem
        if start <= day <= end:
            days.append((day, p.read_text(encoding="utf-8")))
    out_dir = Path("analysis/bundles") / f"{start}--{end}"
    out_dir.mkdir(parents=True, exist_ok=True)
    header = (f"# Bundle {start}..{end}\n\n"
              f"- entries: {len(days)}\n"
              f"- 生成: 機械的な連結(分析はChatGPT側で行う)\n\n---\n\n")
    body = header + "\n\n---\n\n".join(t for _, t in days)
    parts = split_utf8(body.encode("utf-8"), MAX_PART_BYTES)
    for old in out_dir.glob("part-*.md"):
        old.unlink()
    for n, part in enumerate(parts, 1):
        (out_dir / f"part-{n}.md").write_bytes(part)
    req.write_text(
        text.rstrip() + f"\n\nstatus: done\nentries: {len(days)}\n"
        f"bundle: analysis/bundles/{start}--{end}/ (part-1.md .. part-{len(parts)}.md)\n",
        encoding="utf-8")
    print(f"{req.name}: {len(days)} entries -> {len(parts)} parts")
    processed = True

if not processed:
    print("no pending requests")
sys.exit(0)
