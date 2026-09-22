#!/usr/bin/env python3
"""Validate that the site's Korean content has complete, non-stale English companions.

Checked with the Python 3.12 standard library only, runnable from the repo root:

    python3 .github/scripts/validate_translations.py [--base REF] [--root PATH]

Full validation (always runs) checks that every JSON content file and
``index.html`` currently satisfies the bilingual-content contract described in
the module's helper functions below. Diff validation (``--base REF``) is
additive: it also fails the build when a Korean source value changed since
``REF`` while its English companion stayed byte-identical (a "stale
translation"), which the full check alone cannot catch because a stale
translation is, on its own, a syntactically complete pair.

Exit code is 0 when no issues are found, 1 otherwise. Every issue is printed
as a single line: ``<file>: <item/key>: <message>``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid as uuid_module
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants: file locations and small regexes.
# ---------------------------------------------------------------------------

NEWS_PATH = "News_Blog_JPG/beelab_content/news.json"
BLOG_PATH = "News_Blog_JPG/beelab_content/blog.json"

# (relative path, whether citationEn is required for this collection)
PUBLICATION_FILES: Tuple[Tuple[str, bool], ...] = (
    ("publications/international.json", False),
    ("publications/domestic.json", True),
    ("publications/int-conf.json", False),
    ("publications/dom-conf.json", True),
)

RESEARCH_PATH = "research-content/research.json"
MEMBERS_PATH = "members.json"
EN_JSON_PATH = "i18n/en.json"
HTML_PATH = "index.html"

# Hangul syllables + jamo blocks (compatibility jamo, Hangul Jamo, Jamo Extended-A/B).
HANGUL_RE = re.compile(
    r"[가-힣ᄀ-ᇿ㄰-㆏ꥠ-꥿ힰ-퟿]"
)

# documented Korean-field -> English-companion-field pairs inside members.json
# (recursed into wherever they appear, at any depth).
MEMBERS_COMPANION_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("name", "nameEn"),
    ("bio", "bioEn"),
    ("title", "titleEn"),
    ("affiliation", "affiliationEn"),
    ("roleLine", "roleLineEn"),
    ("lines", "linesEn"),
)

ATTR_KEYS: Tuple[str, ...] = ("aria-label", "alt", "placeholder", "title")

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
SKIP_TEXT_TAGS = {"script", "style"}
COVERING_ATTRS = {"data-i18n", "data-i18n-html", "data-ko-parallel"}


# ---------------------------------------------------------------------------
# Small pure helpers.
# ---------------------------------------------------------------------------


def has_hangul(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(HANGUL_RE.search(text))


def is_valid_uuid(value: Any) -> bool:
    """True for a standard hyphenated UUID version 4 string.

    Pages CMS documents UUID v4 generation but does not guarantee letter case,
    so both lowercase and uppercase hex are accepted. Compact, braced, and URN
    spellings are rejected to keep stored identifiers uniform and diffable.
    """
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid_module.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    if parsed.version != 4:
        return False
    return str(parsed) == value.lower()


def normalized_stable_id(value: Any) -> Any:
    """Normalize valid UUIDs for case-insensitive identity comparisons."""
    if is_valid_uuid(value):
        return value.lower()
    return value


@dataclass(frozen=True)
class Issue:
    file: str
    item: str
    message: str

    def format(self) -> str:
        return f"{self.file}: {self.item}: {self.message}"


def _check_pair(
    issues: List[Issue],
    file_label: str,
    item: str,
    ko_value: Any,
    en_value: Any,
    ko_name: str,
    en_name: str,
    *,
    trigger: str,
    required_source: bool = False,
    required_companion: bool = False,
) -> None:
    """Check one Korean/English string-field pair.

    ``trigger`` selects when the English companion becomes *required*:
      - "nonempty": whenever the Korean value is a non-empty string
        (News/Blog ``title`` only -- the CMS schema marks ``titleEn`` as
        always ``required: true`` once a title exists, English or not).
      - "hangul": whenever the Korean value actually contains Hangul
        (News/Blog ``body``/``caption``, research.json, and members.json:
        an already-English source value never demands a companion).

    Regardless of the trigger, a non-empty English companion that itself
    contains Hangul is always flagged.
    """
    if required_source and (not isinstance(ko_value, str) or not ko_value.strip()):
        issues.append(Issue(file_label, item, f"missing or empty {ko_name}"))
    if ko_value is not None and not isinstance(ko_value, str):
        issues.append(Issue(file_label, item, f"{ko_name} must be a string"))
        ko_text = ""
    else:
        ko_text = ko_value or ""
    if en_value is not None and not isinstance(en_value, str):
        issues.append(Issue(file_label, item, f"{en_name} must be a string"))
        en_text = ""
    else:
        en_text = en_value or ""
    if trigger == "nonempty":
        required = bool(ko_text.strip())
        reason = f"{ko_name} is non-empty"
    else:
        required = has_hangul(ko_text)
        reason = f"{ko_name} contains Hangul"
    if (required or required_companion) and not en_text.strip():
        companion_reason = reason if required else f"{en_name} is required"
        issues.append(Issue(file_label, item, f"missing {en_name} ({companion_reason})"))
    if en_text.strip() and has_hangul(en_text):
        issues.append(Issue(file_label, item, f"{en_name} contains Hangul"))


def _check_list_pair(
    issues: List[Issue],
    file_label: str,
    item: str,
    ko_list: Any,
    en_list: Any,
    ko_name: str,
    en_name: str,
) -> None:
    """Check a Korean/English pair of string lists (members.json 'lines')."""
    if not isinstance(ko_list, list):
        return
    ko_has_hangul = any(has_hangul(s) for s in ko_list if isinstance(s, str))
    if ko_has_hangul:
        if not en_list:
            issues.append(
                Issue(file_label, item, f"missing {en_name} ({ko_name} contains Hangul)")
            )
        elif not isinstance(en_list, list):
            issues.append(Issue(file_label, item, f"{en_name} must be a list of strings"))
        elif len(en_list) != len(ko_list):
            issues.append(
                Issue(
                    file_label,
                    item,
                    f"{en_name} has {len(en_list)} entries but {ko_name} has {len(ko_list)}",
                )
            )
    if isinstance(en_list, list):
        for i, s in enumerate(en_list):
            if isinstance(s, str) and has_hangul(s):
                issues.append(Issue(file_label, f"{item}[{i}]", f"{en_name} contains Hangul"))


def load_json_file(path: Path, rel_label: str) -> Tuple[Any, List[Issue]]:
    if not path.exists():
        return None, [Issue(rel_label, "file", "not found")]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [Issue(rel_label, "file", f"could not be read: {exc}")]
    try:
        return json.loads(text), []
    except json.JSONDecodeError as exc:
        return None, [Issue(rel_label, "file", f"invalid JSON: {exc}")]


# ---------------------------------------------------------------------------
# News / Blog validation.
# ---------------------------------------------------------------------------


def validate_news_blog_records(records: Any, file_label: str) -> List[Issue]:
    issues: List[Issue] = []
    if not isinstance(records, list):
        return [Issue(file_label, "root", "expected a JSON array")]

    seen_ids: Dict[str, str] = {}
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            issues.append(Issue(file_label, f"index {idx}", "expected a JSON object"))
            continue
        rid = rec.get("id")
        item = rid if isinstance(rid, str) and rid else f"index {idx}"

        normalized_id = normalized_stable_id(rid)
        if not rid:
            issues.append(Issue(file_label, item, "missing id"))
        elif not is_valid_uuid(rid):
            issues.append(Issue(file_label, item, f"id is not a valid UUID: {rid!r}"))
        elif normalized_id in seen_ids:
            issues.append(Issue(file_label, item, f"duplicate id (also used by {seen_ids[normalized_id]})"))
        else:
            seen_ids[normalized_id] = item

        _check_pair(issues, file_label, item, rec.get("title"), rec.get("titleEn"),
                    "title", "titleEn", trigger="nonempty", required_source=True,
                    required_companion=True)
        _check_pair(issues, file_label, item, rec.get("body"), rec.get("bodyEn"),
                    "body", "bodyEn", trigger="hangul")

        images = rec.get("images")
        if isinstance(images, list):
            for img_idx, img in enumerate(images):
                if not isinstance(img, dict):
                    continue
                img_item = f"{item}.images[{img_idx}]"
                _check_pair(issues, file_label, img_item, img.get("caption"), img.get("captionEn"),
                            "caption", "captionEn", trigger="hangul")
    return issues


# ---------------------------------------------------------------------------
# Publications validation.
# ---------------------------------------------------------------------------


def validate_publications_records(
    records: Any, file_label: str, require_citation_en: bool
) -> Tuple[List[Issue], Dict[str, str]]:
    issues: List[Issue] = []
    ids: Dict[str, str] = {}
    if not isinstance(records, list):
        return [Issue(file_label, "root", "expected a JSON array")], ids

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            issues.append(Issue(file_label, f"index {idx}", "expected a JSON object"))
            continue
        rid = rec.get("id")
        item = rid if isinstance(rid, str) and rid else f"index {idx}"

        normalized_id = normalized_stable_id(rid)
        if not rid:
            issues.append(Issue(file_label, item, "missing id"))
        elif not is_valid_uuid(rid):
            issues.append(Issue(file_label, item, f"id is not a valid UUID: {rid!r}"))
        elif normalized_id in ids:
            issues.append(Issue(file_label, item, f"duplicate id (also used by {ids[normalized_id]})"))
        else:
            ids[normalized_id] = item

        citation = rec.get("citation")
        citation_en = rec.get("citationEn")
        if not isinstance(citation, str) or not citation.strip():
            issues.append(Issue(file_label, item, "missing or empty citation"))
        elif has_hangul(citation) and not require_citation_en:
            issues.append(Issue(file_label, item, "citation contains Hangul in an international collection"))
        if require_citation_en:
            _check_pair(issues, file_label, item, citation, citation_en,
                        "citation", "citationEn", trigger="nonempty",
                        required_companion=True)
        else:
            # citationEn isn't required for this collection, but if present it
            # must still be a string without Hangul (blanket rule).
            if citation_en is not None and not isinstance(citation_en, str):
                issues.append(Issue(file_label, item, "citationEn must be a string"))
            elif citation_en and citation_en.strip() and has_hangul(citation_en):
                issues.append(Issue(file_label, item, "citationEn contains Hangul"))
    return issues, ids


# ---------------------------------------------------------------------------
# research.json validation.
# ---------------------------------------------------------------------------


def validate_research_records(records: Any) -> List[Issue]:
    file_label = RESEARCH_PATH
    issues: List[Issue] = []
    if not isinstance(records, list):
        return [Issue(file_label, "root", "expected a JSON array")]

    seen_ids: Dict[str, str] = {}
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            issues.append(Issue(file_label, f"index {idx}", "expected a JSON object"))
            continue
        rid = rec.get("id")
        item = rid if isinstance(rid, str) and rid else f"index {idx}"

        if rid:
            if rid in seen_ids:
                issues.append(Issue(file_label, item, f"duplicate id (also used by {seen_ids[rid]})"))
            else:
                seen_ids[rid] = item
        else:
            issues.append(Issue(file_label, item, "missing id"))

        for ko_field, en_field in (
            ("title", "titleEn"),
            ("status", "statusEn"),
            ("background", "backgroundEn"),
            ("goal", "goalEn"),
        ):
            _check_pair(issues, file_label, item, rec.get(ko_field), rec.get(en_field),
                        ko_field, en_field, trigger="hangul")

        researchers = rec.get("researchers")
        if isinstance(researchers, list):
            for r_idx, researcher in enumerate(researchers):
                if not isinstance(researcher, dict):
                    continue
                slug = researcher.get("slug", "?")
                r_item = f"{item}.researchers[{r_idx}]({slug})"
                _check_pair(issues, file_label, r_item, researcher.get("name"),
                            researcher.get("nameEn"), "name", "nameEn", trigger="hangul")
    return issues


# ---------------------------------------------------------------------------
# members.json validation (recursive companion-pair walk).
# ---------------------------------------------------------------------------


def validate_members_data(data: Any) -> List[Issue]:
    file_label = MEMBERS_PATH
    issues: List[Issue] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for ko_field, en_field in MEMBERS_COMPANION_PAIRS:
                if ko_field not in node:
                    continue
                item = f"{path}.{ko_field}" if path else ko_field
                if ko_field == "lines":
                    _check_list_pair(issues, file_label, item, node.get(ko_field),
                                      node.get(en_field), ko_field, en_field)
                else:
                    _check_pair(issues, file_label, item, node.get(ko_field), node.get(en_field),
                                ko_field, en_field, trigger="hangul")
            for key, value in node.items():
                child_path = f"{path}.{key}" if path else key
                walk(value, child_path)
        elif isinstance(node, list):
            for i, child in enumerate(node):
                walk(child, f"{path}[{i}]")

    walk(data, "")
    return issues


# ---------------------------------------------------------------------------
# i18n/en.json standalone validation.
# ---------------------------------------------------------------------------


def flatten_en_json(en_data: Any) -> Dict[str, str]:
    """Return nested translation leaves as the dotted keys used by HTML/JS."""
    flattened: Dict[str, str] = {}

    def walk(node: Any, prefix: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                dotted = f"{prefix}.{key}" if prefix else key
                walk(value, dotted)
        elif isinstance(node, str) and prefix:
            flattened[prefix] = node

    walk(en_data, "")
    return flattened


def validate_en_json_values(en_data: Any) -> List[Issue]:
    file_label = EN_JSON_PATH
    issues: List[Issue] = []
    if not isinstance(en_data, dict):
        return [Issue(file_label, "root", "expected a JSON object")]

    def walk(node: Any, prefix: str) -> None:
        if isinstance(node, dict):
            if prefix and not node:
                issues.append(Issue(file_label, prefix, "translation group is empty"))
            for key, value in node.items():
                dotted = f"{prefix}.{key}" if prefix else key
                walk(value, dotted)
            return
        if not isinstance(node, str):
            issues.append(Issue(file_label, prefix or "root", "value must be a string or object"))
            return
        if not node.strip():
            issues.append(Issue(file_label, prefix, "value is empty"))
        elif has_hangul(node):
            issues.append(Issue(file_label, prefix, "value contains Hangul"))

    walk(en_data, "")
    return issues


# ---------------------------------------------------------------------------
# index.html validation via html.parser.HTMLParser.
# ---------------------------------------------------------------------------


class HtmlI18nScanner(HTMLParser):
    """Single-pass scanner for the index.html bilingual-coverage contract.

    Tracks a stack of open-element frames so that a Hangul text node is
    considered "covered" when itself or ANY ancestor carries data-i18n,
    data-i18n-html or data-ko-parallel. Attribute-level checks
    (aria-label/alt/placeholder/title) are self-only, matching how
    js/i18n.js applies data-i18n-ATTRIBUTE per-element rather than by
    inheritance.
    """

    def __init__(self, file_label: str) -> None:
        super().__init__(convert_charrefs=True)
        self.file_label = file_label
        self.issues: List[Issue] = []
        self.stack: List[Dict[str, Any]] = []
        self.key_usage: Dict[str, List[Tuple[int, int]]] = {}
        self.key_sources: Dict[str, List[Tuple[str, int, int]]] = {}
        self.key_source: Dict[str, str] = {}
        self.all_keys_seen: set = set()

    # -- element open/close -------------------------------------------------

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self._open(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        # Default HTMLParser behaviour would call handle_starttag then
        # handle_endtag; we replicate that explicitly since _open() may
        # decide NOT to push a frame for void elements.
        self._open(tag, attrs)
        self.handle_endtag(tag)

    def _open(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_dict: Dict[str, str] = {k: (v if v is not None else "") for k, v in attrs}
        line, col = self.getpos()
        tag_lower = tag.lower()

        # Attribute-level Hangul coverage (self-only, per js/i18n.js semantics).
        for attr in ATTR_KEYS:
            i18n_attr = f"data-i18n-{attr}"
            value = attrs_dict.get(attr, "")
            if value and has_hangul(value):
                if not attrs_dict.get(i18n_attr):
                    self.issues.append(
                        Issue(
                            self.file_label,
                            f"<{tag}> {attr} (line {line})",
                            f'{attr}="{value}" contains Hangul but has no {i18n_attr}',
                        )
                    )
            key = attrs_dict.get(i18n_attr)
            if key:
                self.key_usage.setdefault(key, []).append((line, col))
                self.key_sources.setdefault(key, []).append((value.strip(), line, col))
                self.all_keys_seen.add(key)
                self.key_source.setdefault(key, value.strip())

        is_void = tag_lower in VOID_ELEMENTS
        covers = any(a in attrs_dict for a in COVERING_ATTRS)
        frame: Dict[str, Any] = {
            "tag": tag_lower,
            "covers": covers,
            "text_parts": [],
            "line": line,
        }

        for key_attr in ("data-i18n", "data-i18n-html"):
            value = attrs_dict.get(key_attr)
            if value:
                self.key_usage.setdefault(value, []).append((line, col))
                self.all_keys_seen.add(value)
                frame["pending_key"] = value

        if not is_void:
            self.stack.append(frame)
        elif frame.get("pending_key"):
            # A void element can't meaningfully carry text-based data-i18n;
            # record it with empty source text rather than silently drop it.
            self.key_source.setdefault(frame["pending_key"], "")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in VOID_ELEMENTS:
            return  # never pushed a frame for these; ignore stray close tags
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag_lower:
                closing = self.stack[i:]
                del self.stack[i:]
                for frame in reversed(closing):
                    self._finalize_frame(frame)
                return
        # No matching open tag: tolerate malformed/mismatched HTML silently.

    def _finalize_frame(self, frame: Dict[str, Any]) -> None:
        pending_key = frame.get("pending_key")
        if pending_key:
            text = " ".join("".join(frame["text_parts"]).split())
            line = frame["line"]
            self.key_sources.setdefault(pending_key, []).append((text, line, 0))
            self.key_source.setdefault(pending_key, text)

    def close(self) -> None:
        super().close()
        # Finalize any frames still open at EOF (tolerant of malformed HTML).
        for frame in self.stack:
            self._finalize_frame(frame)
        self.stack = []

    # -- text ----------------------------------------------------------------

    def handle_data(self, data: str) -> None:
        if any(f["tag"] in SKIP_TEXT_TAGS for f in self.stack):
            return
        for frame in self.stack:
            frame["text_parts"].append(data)
        if not data.strip() or not has_hangul(data):
            return
        if any(f["covers"] for f in self.stack):
            return
        line, col = self.getpos()
        snippet = data.strip()
        if len(snippet) > 40:
            snippet = snippet[:40] + "…"
        self.issues.append(
            Issue(
                self.file_label,
                f'text near line {line}: "{snippet}"',
                "Hangul text not covered by data-i18n/data-i18n-html/data-ko-parallel",
            )
        )

    def finalize(self) -> List[Issue]:
        for key, sources in self.key_sources.items():
            distinct = {text for text, _line, _col in sources}
            if len(distinct) > 1:
                details = "; ".join(
                    f"L{line}: {text!r}" for text, line, _col in sources
                )
                self.issues.append(
                    Issue(
                        self.file_label,
                        key,
                        "data-i18n key is attached to different source values " + details,
                    )
                )
        return self.issues


def scan_html(html_text: str, file_label: str = HTML_PATH) -> HtmlI18nScanner:
    parser = HtmlI18nScanner(file_label)
    parser.feed(html_text)
    parser.close()
    parser.finalize()
    return parser


def check_html_keys_exist_in_en(all_keys_seen: Iterable[str], en_data: Any,
                                 file_label: str = HTML_PATH) -> List[Issue]:
    issues: List[Issue] = []
    en_data = en_data if isinstance(en_data, dict) else {}
    for key in sorted(all_keys_seen):
        if key not in en_data:
            issues.append(Issue(file_label, key, "data-i18n key has no entry in i18n/en.json"))
    return issues


def validate_html_and_i18n(root: Path) -> Tuple[List[Issue], Optional[HtmlI18nScanner], Any]:
    """Full validation for index.html + i18n/en.json.

    Returns (issues, scanner_or_None, en_data) so the caller can reuse the
    parsed state for diff mode without re-parsing.
    """
    issues: List[Issue] = []
    en_path = root / EN_JSON_PATH
    html_path = root / HTML_PATH

    en_data: Any = {}
    if not en_path.exists():
        issues.append(Issue(EN_JSON_PATH, "file", "not found"))
    else:
        try:
            en_data = json.loads(en_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(Issue(EN_JSON_PATH, "file", f"invalid JSON: {exc}"))
            en_data = {}
        else:
            issues.extend(validate_en_json_values(en_data))
            en_data = flatten_en_json(en_data)

    if not html_path.exists():
        issues.append(Issue(HTML_PATH, "file", "not found"))
        return issues, None, en_data

    html_text = html_path.read_text(encoding="utf-8")
    scanner = scan_html(html_text, HTML_PATH)
    issues.extend(scanner.issues)
    issues.extend(check_html_keys_exist_in_en(scanner.all_keys_seen, en_data))
    return issues, scanner, en_data


def diff_html_keys(
    current_key_source: Dict[str, str],
    base_key_source: Dict[str, str],
    current_en: Any,
    base_en: Any,
    file_label: str = HTML_PATH,
) -> List[Issue]:
    issues: List[Issue] = []
    current_en = current_en if isinstance(current_en, dict) else {}
    base_en = base_en if isinstance(base_en, dict) else {}
    for key, cur_src in current_key_source.items():
        if key not in base_key_source:
            continue  # new key: full validation already covers it
        base_src = base_key_source[key]
        if cur_src == base_src:
            continue
        if key not in current_en:
            continue  # missing entirely -> already reported by full validation
        cur_val = current_en.get(key)
        base_val = base_en.get(key)
        if cur_val == base_val:
            issues.append(
                Issue(
                    file_label,
                    key,
                    "Korean source text changed but i18n/en.json value is unchanged (stale translation)",
                )
            )
    return issues


# ---------------------------------------------------------------------------
# --base diff mode: git access + generic id-keyed comparison.
# ---------------------------------------------------------------------------


def git_show(root: Path, ref: str, rel_path: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{rel_path}"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def resolve_base_ref(root: Path, ref: str) -> bool:
    """True iff ``ref`` resolves to a real commit in the repo at ``root``.

    Distinguishes a genuinely invalid ``--base`` argument (a typo, a ref
    that was never fetched, a stray all-zeros SHA, etc.) -- which must fail
    the build clearly instead of silently skipping every stale-translation
    check -- from a valid ref that simply predates individual files or
    stable ids, which the diff helpers above already bootstrap past
    gracefully once the ref itself is known-good.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def load_base_json(root: Path, ref: str, rel_path: str) -> Any:
    text = git_show(root, ref, rel_path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def diff_id_collection(
    file_label: str,
    current_records: Any,
    base_records: Any,
    field_pairs: Iterable[Tuple[str, str]],
    id_field: str = "id",
) -> List[Issue]:
    """Compare records present in both `current_records` and `base_records`
    (matched by `id_field`) and flag a Korean field that changed while its
    English companion stayed byte-identical.

    Gracefully returns no issues (bootstrap fallback, full validation still
    applies) when the base doesn't parse as a list, or has no usable ids at
    all -- this covers a pre-UUID-migration base file.
    """
    issues: List[Issue] = []
    if not isinstance(base_records, list) or not isinstance(current_records, list):
        return issues
    base_by_id = {
        normalized_stable_id(r.get(id_field)): r
        for r in base_records
        if isinstance(r, dict) and r.get(id_field)
    }
    if not base_by_id:
        return issues  # base predates ids entirely: bootstrap, rely on full validation

    for rec in current_records:
        if not isinstance(rec, dict):
            continue
        rid = rec.get(id_field)
        normalized_id = normalized_stable_id(rid)
        if not rid or normalized_id not in base_by_id:
            continue  # new record: full validation covers it
        base_rec = base_by_id[normalized_id]
        item = rid
        for ko_field, en_field in field_pairs:
            cur_ko = rec.get(ko_field) or ""
            base_ko = base_rec.get(ko_field) or ""
            if cur_ko == base_ko:
                continue
            cur_en = rec.get(en_field)
            base_en = base_rec.get(en_field)
            if cur_en is not None and cur_en == base_en:
                issues.append(
                    Issue(file_label, item, f"{ko_field} changed but {en_field} unchanged (stale translation)")
                )
    return issues


def diff_images_by_src(
    file_label: str,
    current_records: Any,
    base_records: Any,
) -> List[Issue]:
    """Compare nested ``images[]`` entries (matched by ``src``) between
    same-``id`` News/Blog records, flagging a Korean ``caption`` that changed
    while ``captionEn`` stayed byte-identical.

    Images carry no id of their own, so ``src`` (the image path/filename) is
    the stable identity used to match an image across the diff. This catches
    a caption edited in place on an otherwise-unchanged image, which
    ``diff_id_collection``'s top-level-only field pairs cannot see because it
    never looks inside ``images[]``.

    Gracefully returns no issues for a record whose base predates
    ``images[].src`` entirely (bootstrap fallback for that record), and for
    the whole file when the base has no usable top-level ids at all.
    """
    issues: List[Issue] = []
    if not isinstance(base_records, list) or not isinstance(current_records, list):
        return issues
    base_by_id = {
        normalized_stable_id(r.get("id")): r
        for r in base_records
        if isinstance(r, dict) and r.get("id")
    }
    if not base_by_id:
        return issues  # base predates ids entirely: bootstrap, rely on full validation

    for rec in current_records:
        if not isinstance(rec, dict):
            continue
        rid = rec.get("id")
        normalized_id = normalized_stable_id(rid)
        if not rid or normalized_id not in base_by_id:
            continue  # new record: full validation covers it
        base_rec = base_by_id[normalized_id]
        cur_images = rec.get("images")
        base_images = base_rec.get("images")
        if not isinstance(cur_images, list) or not isinstance(base_images, list):
            continue
        base_by_src = {
            img.get("src"): img
            for img in base_images
            if isinstance(img, dict) and img.get("src")
        }
        if not base_by_src:
            continue  # base predates src-identified images on this record: bootstrap
        for img in cur_images:
            if not isinstance(img, dict):
                continue
            src = img.get("src")
            if not src or src not in base_by_src:
                continue  # new image: full validation covers it
            base_img = base_by_src[src]
            cur_ko = img.get("caption") or ""
            base_ko = base_img.get("caption") or ""
            if cur_ko == base_ko:
                continue
            cur_en = img.get("captionEn")
            base_en = base_img.get("captionEn")
            if cur_en is not None and cur_en == base_en:
                issues.append(
                    Issue(
                        file_label,
                        f"{rid}.images[{src}]",
                        "caption changed but captionEn unchanged (stale translation)",
                    )
                )
    return issues


def diff_research_researchers(
    file_label: str,
    current_records: Any,
    base_records: Any,
) -> List[Issue]:
    """Compare nested ``researchers[]`` entries (matched by ``slug``) between
    same-``id`` research.json records, flagging a Korean ``name`` that
    changed while ``nameEn`` stayed byte-identical.

    Gracefully returns no issues for a record whose base predates
    ``researchers[].slug`` entirely (bootstrap fallback for that record), and
    for the whole file when the base has no usable top-level ids at all --
    mirroring ``diff_id_collection``/``diff_images_by_src``.
    """
    issues: List[Issue] = []
    if not isinstance(base_records, list) or not isinstance(current_records, list):
        return issues
    base_by_id = {
        normalized_stable_id(r.get("id")): r
        for r in base_records
        if isinstance(r, dict) and r.get("id")
    }
    if not base_by_id:
        return issues

    for rec in current_records:
        if not isinstance(rec, dict):
            continue
        rid = rec.get("id")
        normalized_id = normalized_stable_id(rid)
        if not rid or normalized_id not in base_by_id:
            continue
        base_rec = base_by_id[normalized_id]
        cur_researchers = rec.get("researchers")
        base_researchers = base_rec.get("researchers")
        if not isinstance(cur_researchers, list) or not isinstance(base_researchers, list):
            continue
        base_by_slug = {
            r.get("slug"): r
            for r in base_researchers
            if isinstance(r, dict) and r.get("slug")
        }
        if not base_by_slug:
            continue  # base predates slugs on this record: bootstrap

        for researcher in cur_researchers:
            if not isinstance(researcher, dict):
                continue
            slug = researcher.get("slug")
            if not slug or slug not in base_by_slug:
                continue
            base_researcher = base_by_slug[slug]
            cur_ko = researcher.get("name") or ""
            base_ko = base_researcher.get("name") or ""
            if cur_ko == base_ko:
                continue
            cur_en = researcher.get("nameEn")
            base_en = base_researcher.get("nameEn")
            if cur_en is not None and cur_en == base_en:
                issues.append(
                    Issue(
                        file_label,
                        f"{rid}.researchers[{slug}]",
                        "name changed but nameEn unchanged (stale translation)",
                    )
                )
    return issues


def diff_members_data(current: Any, base: Any) -> List[Issue]:
    file_label = MEMBERS_PATH
    issues: List[Issue] = []
    if not isinstance(base, dict) or not isinstance(current, dict):
        return issues

    cur_profiles = current.get("profiles") if isinstance(current.get("profiles"), dict) else {}
    base_profiles = base.get("profiles") if isinstance(base.get("profiles"), dict) else {}
    for slug, cur_prof in cur_profiles.items():
        if not isinstance(cur_prof, dict):
            continue
        base_prof = base_profiles.get(slug)
        if not isinstance(base_prof, dict):
            continue  # new profile: full validation covers it
        for ko_field, en_field in (("name", "nameEn"), ("bio", "bioEn"), ("roleLine", "roleLineEn")):
            cur_ko = cur_prof.get(ko_field) or ""
            base_ko = base_prof.get(ko_field) or ""
            if cur_ko == base_ko:
                continue
            cur_en = cur_prof.get(en_field)
            base_en = base_prof.get(en_field)
            if cur_en is not None and cur_en == base_en:
                issues.append(
                    Issue(file_label, f"profiles.{slug}", f"{ko_field} changed but {en_field} unchanged (stale translation)")
                )

        # profiles[slug].research[] matched by "page" (no id of its own).
        cur_research = cur_prof.get("research") if isinstance(cur_prof.get("research"), list) else []
        base_research = base_prof.get("research") if isinstance(base_prof.get("research"), list) else []
        base_research_by_page = {
            r.get("page"): r
            for r in base_research
            if isinstance(r, dict) and r.get("page")
        }
        if base_research_by_page:
            for r_item in cur_research:
                if not isinstance(r_item, dict):
                    continue
                page = r_item.get("page")
                if not page or page not in base_research_by_page:
                    continue  # new research item: full validation covers it
                base_r_item = base_research_by_page[page]
                cur_ko = r_item.get("title") or ""
                base_ko = base_r_item.get("title") or ""
                if cur_ko == base_ko:
                    continue
                cur_en = r_item.get("titleEn")
                base_en = base_r_item.get("titleEn")
                if cur_en is not None and cur_en == base_en:
                    issues.append(
                        Issue(
                            file_label,
                            f"profiles.{slug}.research[{page}]",
                            "title changed but titleEn unchanged (stale translation)",
                        )
                    )

    # professor.sections[] matched by "title" (no better stable key available).
    cur_prof_root = current.get("professor") if isinstance(current.get("professor"), dict) else {}
    base_prof_root = base.get("professor") if isinstance(base.get("professor"), dict) else {}
    cur_sections = cur_prof_root.get("sections") if isinstance(cur_prof_root.get("sections"), list) else []
    base_sections = base_prof_root.get("sections") if isinstance(base_prof_root.get("sections"), list) else []
    base_sections_by_title = {
        s.get("title"): s
        for s in base_sections
        if isinstance(s, dict) and s.get("title")
    }
    if base_sections_by_title:
        for section in cur_sections:
            if not isinstance(section, dict):
                continue
            title = section.get("title")
            if not title or title not in base_sections_by_title:
                continue  # new section: full validation covers it
            base_section = base_sections_by_title[title]
            cur_lines = section.get("lines")
            base_lines = base_section.get("lines")
            if cur_lines == base_lines:
                continue
            cur_lines_en = section.get("linesEn")
            base_lines_en = base_section.get("linesEn")
            if cur_lines_en is not None and cur_lines_en == base_lines_en:
                issues.append(
                    Issue(
                        file_label,
                        f"professor.sections[{title}]",
                        "lines changed but linesEn unchanged (stale translation)",
                    )
                )

    def flat_members(d: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for group in d.get("researchers") or []:
            if not isinstance(group, dict):
                continue
            for m in group.get("members") or []:
                if isinstance(m, dict) and m.get("slug"):
                    out[m["slug"]] = m
        for m in d.get("alumni") or []:
            if isinstance(m, dict) and m.get("slug"):
                out[m["slug"]] = m
        return out

    cur_flat = flat_members(current)
    base_flat = flat_members(base)
    for slug, cur_m in cur_flat.items():
        base_m = base_flat.get(slug)
        if not base_m:
            continue
        cur_ko = cur_m.get("name") or ""
        base_ko = base_m.get("name") or ""
        if cur_ko == base_ko:
            continue
        cur_en = cur_m.get("nameEn")
        base_en = base_m.get("nameEn")
        if cur_en is not None and cur_en == base_en:
            issues.append(Issue(file_label, f"member:{slug}", "name changed but nameEn unchanged (stale translation)"))
    return issues


# ---------------------------------------------------------------------------
# Orchestration.
# ---------------------------------------------------------------------------


def collect_full_issues(root: Path) -> Tuple[List[Issue], Dict[str, Any]]:
    issues: List[Issue] = []
    loaded: Dict[str, Any] = {}

    news_data, errs = load_json_file(root / NEWS_PATH, NEWS_PATH)
    issues += errs
    loaded["news"] = news_data
    if isinstance(news_data, list):
        issues += validate_news_blog_records(news_data, NEWS_PATH)

    blog_data, errs = load_json_file(root / BLOG_PATH, BLOG_PATH)
    issues += errs
    loaded["blog"] = blog_data
    if isinstance(blog_data, list):
        issues += validate_news_blog_records(blog_data, BLOG_PATH)

    loaded["pubs"] = {}
    all_pub_ids: Dict[str, str] = {}
    for rel_path, requires_en in PUBLICATION_FILES:
        data, errs = load_json_file(root / rel_path, rel_path)
        issues += errs
        loaded["pubs"][rel_path] = data
        if isinstance(data, list):
            file_issues, ids = validate_publications_records(data, rel_path, requires_en)
            issues += file_issues
            for rid, item in ids.items():
                if rid in all_pub_ids:
                    issues.append(
                        Issue(rel_path, item, f"duplicate id across publications (also used by {all_pub_ids[rid]})")
                    )
                else:
                    all_pub_ids[rid] = f"{rel_path}:{item}"

    research_data, errs = load_json_file(root / RESEARCH_PATH, RESEARCH_PATH)
    issues += errs
    loaded["research"] = research_data
    if isinstance(research_data, list):
        issues += validate_research_records(research_data)

    members_data, errs = load_json_file(root / MEMBERS_PATH, MEMBERS_PATH)
    issues += errs
    loaded["members"] = members_data
    if isinstance(members_data, (dict, list)):
        issues += validate_members_data(members_data)

    html_issues, scanner, en_data = validate_html_and_i18n(root)
    issues += html_issues
    loaded["html_scanner"] = scanner
    loaded["en_data"] = en_data

    return issues, loaded


def collect_diff_issues(root: Path, base_ref: str, loaded: Dict[str, Any]) -> List[Issue]:
    issues: List[Issue] = []

    base_news = load_base_json(root, base_ref, NEWS_PATH)
    issues += diff_id_collection(NEWS_PATH, loaded.get("news") or [], base_news,
                                  [("title", "titleEn"), ("body", "bodyEn")])
    issues += diff_images_by_src(NEWS_PATH, loaded.get("news") or [], base_news)

    base_blog = load_base_json(root, base_ref, BLOG_PATH)
    issues += diff_id_collection(BLOG_PATH, loaded.get("blog") or [], base_blog,
                                  [("title", "titleEn"), ("body", "bodyEn")])
    issues += diff_images_by_src(BLOG_PATH, loaded.get("blog") or [], base_blog)

    for rel_path, _requires_en in PUBLICATION_FILES:
        base_pub = load_base_json(root, base_ref, rel_path)
        cur = (loaded.get("pubs") or {}).get(rel_path) or []
        issues += diff_id_collection(rel_path, cur, base_pub, [("citation", "citationEn")])

    base_research = load_base_json(root, base_ref, RESEARCH_PATH)
    issues += diff_id_collection(
        RESEARCH_PATH, loaded.get("research") or [], base_research,
        [("title", "titleEn"), ("status", "statusEn"), ("background", "backgroundEn"), ("goal", "goalEn")],
    )
    issues += diff_research_researchers(RESEARCH_PATH, loaded.get("research") or [], base_research)

    base_members = load_base_json(root, base_ref, MEMBERS_PATH)
    issues += diff_members_data(loaded.get("members") or {}, base_members)

    scanner: Optional[HtmlI18nScanner] = loaded.get("html_scanner")
    if scanner is not None:
        base_html_text = git_show(root, base_ref, HTML_PATH)
        if base_html_text is not None:
            base_scanner = scan_html(base_html_text, HTML_PATH)
            base_en_data = flatten_en_json(load_base_json(root, base_ref, EN_JSON_PATH) or {})
            issues += diff_html_keys(
                scanner.key_source, base_scanner.key_source,
                loaded.get("en_data") or {}, base_en_data,
            )

    return issues


def run(root: Path, base_ref: Optional[str]) -> List[Issue]:
    issues, loaded = collect_full_issues(root)
    if base_ref:
        if not resolve_base_ref(root, base_ref):
            issues.append(
                Issue(
                    "--base",
                    base_ref,
                    f"base ref {base_ref!r} does not resolve to a commit in this "
                    "repository; skipping stale-translation checks (fix the ref, "
                    "e.g. fetch depth or a typo, rather than ignoring this)",
                )
            )
        else:
            issues += collect_diff_issues(root, base_ref, loaded)
    return issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate bilingual site content and i18n coverage."
    )
    parser.add_argument("--base", metavar="REF", default=None,
                         help="git ref to diff against for stale-translation checks")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    issues = run(root, args.base)

    if issues:
        for issue in issues:
            print(issue.format(), file=sys.stderr)
        print(f"\n{len(issues)} translation validation issue(s) found.", file=sys.stderr)
        return 1

    print("Translation validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
