"""Lite validation of journal entries: format checks + privacy pattern scan.

Post-commit second line of defense. Format problems are repairable after the
fact; privacy findings mean the primary guard (pre-save check in the ChatGPT
instructions) was missed. Prints findings; exits 1 when any exist.
No third-party dependencies.
"""

import re
import sys
from pathlib import Path

ENTRY_RE = re.compile(r"entries/(\d{4})/(\d{2})/(\d{4}-\d{2}-\d{2})\.md$")
META_KEYS = (
    "capture_id",
    "captured_at",
    "temporal_origin",
    "elicitation",
    "authorship",
    "confirmation",
)
CAPTURE_ID_RE = re.compile(r"capture_id: c-\d{8}-[0-9a-f]{12}$", re.M)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
PRIVACY_PATTERNS = (
    ("メールアドレスらしき文字列", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("電話番号らしき文字列", re.compile(r"(?<!\d)0\d{1,4}-\d{2,4}-\d{4}(?!\d)")),
    ("APIキーらしき文字列", re.compile(r"\b(?:ghp_|gho_|sk-|AKIA)[A-Za-z0-9_-]{10,}")),
    ("パスワードの記載", re.compile(r"(?:password|パスワード|暗証番号)\s*[:は=]", re.I)),
)

findings: list[str] = []
root = Path(".")
for path in sorted(root.glob("entries/[0-9]*/[0-9]*/*.md")):
    m = ENTRY_RE.search(path.as_posix())
    if not m:
        continue
    day = m.group(3)
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith(f"---\ndate: {day}\ntimezone: Asia/Tokyo\n---\n"):
        findings.append(f"{path}: frontmatterがcanonical形式ではない")
    if f"\n# {day}\n" not in f"\n{text}":
        findings.append(f"{path}: 日付見出し `# {day}` がない")
    comments = COMMENT_RE.findall(text)
    if not comments:
        findings.append(f"{path}: capture metadataがない")
    for c in comments:
        for key in META_KEYS:
            if f"{key}: " not in c:
                findings.append(f"{path}: metadata欠落 ({key})")
        if "capture_id: " in c and not CAPTURE_ID_RE.search(c):
            findings.append(f"{path}: capture_idの形式が不正")
    body = COMMENT_RE.sub("", text)
    for label, pat in PRIVACY_PATTERNS:
        if pat.search(body):
            findings.append(f"{path}: [privacy] {label}を検出。内容を確認し、"
                            "不要なら現ファイルから削除を(履歴には残る点に注意)")

if findings:
    print("\n".join(findings))
    sys.exit(1)
print("OK: all entries passed lite validation")
