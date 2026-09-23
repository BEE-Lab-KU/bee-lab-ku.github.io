#!/usr/bin/env python3
"""Unit tests for .github/scripts/validate_translations.py.

These tests never touch the real repository content. Most call the module's
pure functions directly with hand-built Python dicts/lists (no I/O at all);
the handful that need actual files (index.html / i18n/en.json parsing, and
the end-to-end `run()` smoke tests) write them into a `tempfile` directory
that is torn down at the end of each test.

Run with:

    python3 -m unittest discover -s .github/scripts/tests -p "test_*.py" -v

or directly:

    python3 .github/scripts/tests/test_validate_translations.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# validate_translations.py is a standalone script (not a package, and its
# parent directory starts with a dot), so import it by inserting its
# directory onto sys.path rather than trying to import it as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_translations as vt  # noqa: E402


def _write_minimal_valid_site(root: Path) -> None:
    """Write a fully self-contained, fully valid minimal site into `root`.

    Shared by the end-to-end `run()` tests and the `--base` ref tests below,
    neither of which ever touches the real repository -- everything lives
    under a `tempfile.TemporaryDirectory()` supplied by the caller.
    """
    (root / "News_Blog_JPG" / "beelab_content").mkdir(parents=True)
    (root / "News_Blog_JPG" / "beelab_content" / "news.json").write_text("[]", encoding="utf-8")
    (root / "News_Blog_JPG" / "beelab_content" / "blog.json").write_text("[]", encoding="utf-8")
    (root / "publications").mkdir()
    for name in ("international.json", "domestic.json", "int-conf.json", "dom-conf.json"):
        (root / "publications" / name).write_text("[]", encoding="utf-8")
    (root / "research-content").mkdir()
    (root / "research-content" / "research.json").write_text("[]", encoding="utf-8")
    (root / "members.json").write_text('{"professor": {"name": "Hyunwoo Lim"}}', encoding="utf-8")
    (root / "i18n").mkdir()
    (root / "i18n" / "en.json").write_text('{"greeting": "Hello"}', encoding="utf-8")
    (root / "index.html").write_text(
        '<html><body><p data-i18n="greeting">안녕하세요</p></body></html>', encoding="utf-8"
    )


def _init_git_repo(root: Path) -> None:
    """Initialize a throwaway git repo at `root` with everything committed.

    `root` is always a fresh `tempfile.TemporaryDirectory()`, so this never
    touches the real repository or its history.
    """
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(root), check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(root), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=str(root), check=True)


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(root), check=True,
        capture_output=True, text=True,
    )
    return result.stdout.strip()


class HangulAndUuidHelpersTest(unittest.TestCase):
    def test_has_hangul_detects_syllables(self):
        self.assertTrue(vt.has_hangul("안녕하세요"))
        self.assertTrue(vt.has_hangul("Hello 안녕"))

    def test_has_hangul_false_for_pure_english(self):
        self.assertFalse(vt.has_hangul("Hello, world!"))
        self.assertFalse(vt.has_hangul(""))
        self.assertFalse(vt.has_hangul(None))

    def test_uuid_validation(self):
        self.assertTrue(vt.is_valid_uuid("3f2504e0-4f89-41d3-9a0c-0305e82c3301"))
        self.assertFalse(vt.is_valid_uuid("not-a-uuid"))
        self.assertFalse(vt.is_valid_uuid(""))
        self.assertFalse(vt.is_valid_uuid(None))
        self.assertFalse(vt.is_valid_uuid(12345))

    def test_uuid_validation_rejects_non_v4_version(self):
        # A v1 (time-based) UUID: valid hex shape, wrong version nibble.
        self.assertFalse(vt.is_valid_uuid("6ba7b810-9dad-11d1-80b4-00c04fd430c8"))

    def test_uuid_validation_rejects_nil_uuid(self):
        self.assertFalse(vt.is_valid_uuid("00000000-0000-0000-0000-000000000000"))

    def test_uuid_validation_accepts_uppercase_standard_form(self):
        # Pages CMS guarantees UUID v4 but does not document letter case.
        self.assertTrue(vt.is_valid_uuid("3F2504E0-4F89-41D3-9A0C-0305E82C3301"))

    def test_uuid_validation_rejects_non_standard_form(self):
        self.assertFalse(vt.is_valid_uuid("3f2504e04f8941d39a0c0305e82c3301"))
        self.assertFalse(vt.is_valid_uuid("{3f2504e0-4f89-41d3-9a0c-0305e82c3301}"))

    def test_uuid_identity_normalizes_case(self):
        value = "3F2504E0-4F89-41D3-9A0C-0305E82C3301"
        self.assertEqual(vt.normalized_stable_id(value), value.lower())

    def test_bee_lab_name_accepts_canonical_spelling_and_sentence_period(self):
        self.assertFalse(vt.has_noncanonical_bee_lab("BEE Lab의 새 소식"))
        self.assertFalse(vt.has_noncanonical_bee_lab("Welcome to BEE Lab."))
        self.assertFalse(vt.has_noncanonical_bee_lab("BEE Lab's retreat"))
        self.assertFalse(vt.has_noncanonical_bee_lab("beelab.ku@gmail.com"))
        self.assertFalse(vt.has_noncanonical_bee_lab("https://beelab.kr/news"))
        self.assertFalse(
            vt.has_noncanonical_bee_lab(
                "Welcome to BEE Lab. We study buildings.",
                allow_mid_sentence_period=True,
            )
        )

    def test_bee_lab_name_rejects_case_separator_and_attached_period_variants(self):
        for value in (
            "BEE LAB retreat",
            "BeeLab retreat",
            "Bee_LAB retreat",
            "BEE-Lab retreat",
            "BEE.Lab retreat",
            "BEE Lab . retreat",
            "BEE Lab.의 새 소식",
            "BEE Lab.'s retreat",
            "BEE Lab. Retreat",
        ):
            with self.subTest(value=value):
                self.assertTrue(vt.has_noncanonical_bee_lab(value))


class NewsBlogValidationTest(unittest.TestCase):
    """Covers: missing translation, empty optional source, Hangul-in-English, duplicate id."""

    def test_missing_translation_is_flagged(self):
        records = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "안녕하세요", "titleEn": ""}]
        issues = vt.validate_news_blog_records(records, "news.json")
        messages = [i.message for i in issues]
        self.assertTrue(any("missing titleEn" in m for m in messages), messages)

    def test_empty_optional_source_does_not_require_companion(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "제목",
            "titleEn": "Title",
            "body": "",
            "bodyEn": "",
            "images": [{"caption": "", "captionEn": ""}],
        }]
        issues = vt.validate_news_blog_records(records, "news.json")
        self.assertEqual(issues, [])

    def test_hangul_in_english_companion_is_flagged_even_if_present(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "제목",
            "titleEn": "제목 in English",  # still contains Hangul
        }]
        issues = vt.validate_news_blog_records(records, "news.json")
        messages = [i.message for i in issues]
        self.assertTrue(any("titleEn contains Hangul" in m for m in messages), messages)

    def test_duplicate_id_is_flagged(self):
        records = [
            {"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "가", "titleEn": "A"},
            {"id": "3F2504E0-4F89-41D3-9A0C-0305E82C3301", "title": "나", "titleEn": "B"},
        ]
        issues = vt.validate_news_blog_records(records, "news.json")
        messages = [i.message for i in issues]
        self.assertTrue(any("duplicate id" in m for m in messages), messages)

    def test_invalid_uuid_is_flagged(self):
        records = [{"id": "not-a-uuid", "title": "가", "titleEn": "A"}]
        issues = vt.validate_news_blog_records(records, "news.json")
        messages = [i.message for i in issues]
        self.assertTrue(any("not a valid UUID" in m for m in messages), messages)

    def test_valid_paired_record_passes(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "제목",
            "titleEn": "Title",
            "body": "본문",
            "bodyEn": "Body",
            "images": [{"caption": "설명", "captionEn": "Caption"}],
        }]
        self.assertEqual(vt.validate_news_blog_records(records, "news.json"), [])

    def test_english_only_body_passes_without_bodyen(self):
        # body/bodyEn use the "hangul" trigger: an already-English source
        # body must not demand a bodyEn companion.
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "제목",
            "titleEn": "Title",
            "body": "Congratulations to our lab members on the new publication.",
        }]
        self.assertEqual(vt.validate_news_blog_records(records, "news.json"), [])

    def test_english_only_caption_passes_without_captionen(self):
        # caption/captionEn also use the "hangul" trigger (item 1 fix): an
        # English-only caption must pass without a captionEn.
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "제목",
            "titleEn": "Title",
            "images": [{"src": "retreat.jpg", "caption": "Lab retreat, 2026"}],
        }]
        self.assertEqual(vt.validate_news_blog_records(records, "news.json"), [])

    def test_titleen_still_required_for_english_only_title(self):
        # title/titleEn keep the "nonempty" trigger regardless of the
        # body/caption fix: titleEn is required whenever title is non-empty,
        # even when title itself has no Hangul.
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "Lab Notice",
        }]
        issues = vt.validate_news_blog_records(records, "news.json")
        messages = [i.message for i in issues]
        self.assertTrue(any("missing titleEn" in m for m in messages), messages)

    def test_missing_title_and_titleen_are_both_flagged(self):
        records = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301"}]
        issues = vt.validate_news_blog_records(records, "news.json")
        messages = [i.message for i in issues]
        self.assertTrue(any("missing or empty title" in m for m in messages), messages)
        self.assertTrue(any("missing titleEn" in m for m in messages), messages)

    def test_non_string_companion_is_flagged_without_crashing(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "제목",
            "titleEn": ["Title"],
        }]
        issues = vt.validate_news_blog_records(records, "news.json")
        self.assertTrue(any("titleEn must be a string" in i.message for i in issues), issues)

    def test_noncanonical_bee_lab_name_is_flagged_in_record_and_image_copy(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "BEE LAB 소식",
            "titleEn": "BEE Lab News",
            "images": [{
                "src": "BEE Lab. legacy folder/photo.jpg",
                "caption": "BEE Lab.의 행사",
                "captionEn": "An event at BEE Lab.",
            }],
        }]
        issues = vt.validate_news_blog_records(records, "news.json")
        messages = [i.message for i in issues]
        self.assertIn("title must spell the lab name as 'BEE Lab'", messages)
        self.assertIn("src must spell the lab name as 'BEE Lab'", messages)
        self.assertIn("caption must spell the lab name as 'BEE Lab'", messages)

    def test_canonical_bee_lab_name_passes_in_korean_and_english_copy(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "title": "BEE Lab의 새 소식",
            "titleEn": "News from BEE Lab",
            "body": "BEE Lab에서 행사를 열었습니다.",
            "bodyEn": "We held an event at BEE Lab.",
        }]
        self.assertEqual(vt.validate_news_blog_records(records, "news.json"), [])


class PublicationsValidationTest(unittest.TestCase):
    """Covers: English-only existing publication passes; domestic citationEn required."""

    def test_english_only_international_publication_passes(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "citation": "Lee, S., Lim, H. (2026). Some paper. Energy and Buildings.",
        }]
        issues, ids = vt.validate_publications_records(records, "publications/international.json",
                                                         require_citation_en=False)
        self.assertEqual(issues, [])
        self.assertIn("3f2504e0-4f89-41d3-9a0c-0305e82c3301", ids)

    def test_domestic_publication_requires_citation_en(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "citation": "황정윤, 임현우. (2026). 논문 제목. 대한건축학회 논문집.",
        }]
        issues, _ids = vt.validate_publications_records(records, "publications/domestic.json",
                                                          require_citation_en=True)
        messages = [i.message for i in issues]
        self.assertTrue(any("missing citationEn" in m for m in messages), messages)

    def test_domestic_publication_with_citation_en_passes(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "citation": "황정윤, 임현우. (2026). 논문 제목. 대한건축학회 논문집.",
            "citationEn": "Hwang, J., Lim, H. (2026). Paper title. Journal of AIK.",
        }]
        issues, _ids = vt.validate_publications_records(records, "publications/domestic.json",
                                                          require_citation_en=True)
        self.assertEqual(issues, [])

    def test_empty_domestic_citation_and_companion_are_flagged(self):
        records = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301"}]
        issues, _ids = vt.validate_publications_records(
            records, "publications/domestic.json", require_citation_en=True
        )
        messages = [i.message for i in issues]
        self.assertTrue(any("missing or empty citation" in m for m in messages), messages)
        self.assertTrue(any("missing citationEn" in m for m in messages), messages)

    def test_hangul_in_international_citation_is_flagged(self):
        records = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "citation": "영문이어야 하는 국제 인용문",
        }]
        issues, _ids = vt.validate_publications_records(
            records, "publications/international.json", require_citation_en=False
        )
        self.assertTrue(any("international collection" in i.message for i in issues), issues)


class ResearchValidationTest(unittest.TestCase):
    def test_hangul_trigger_requires_companion(self):
        records = [{"id": "research-x", "title": "제목", "status": "진행 중"}]
        issues = vt.validate_research_records(records)
        messages = [i.message for i in issues]
        self.assertTrue(any("missing titleEn" in m for m in messages), messages)
        self.assertTrue(any("missing statusEn" in m for m in messages), messages)

    def test_non_hangul_source_does_not_require_companion(self):
        # An already-English field (no Hangul) should not demand a companion.
        records = [{"id": "research-x", "title": "English Title", "researchers": []}]
        issues = vt.validate_research_records(records)
        self.assertEqual(issues, [])

    def test_researcher_name_translation_required(self):
        records = [{
            "id": "research-x",
            "title": "Title",
            "researchers": [{"slug": "hyunwoo", "name": "임현우"}],
        }]
        issues = vt.validate_research_records(records)
        messages = [i.message for i in issues]
        self.assertTrue(any("missing nameEn" in m for m in messages), messages)


class MembersValidationTest(unittest.TestCase):
    def test_recursive_missing_bio_translation(self):
        data = {"profiles": {"sangmin": {"name": "이상민", "bio": "연구 중입니다."}}}
        issues = vt.validate_members_data(data)
        messages = [i.message for i in issues]
        self.assertTrue(any("missing nameEn" in m for m in messages), messages)
        self.assertTrue(any("missing bioEn" in m for m in messages), messages)

    def test_english_only_professor_fields_not_flagged(self):
        data = {"professor": {"name": "Hyunwoo Lim", "title": "Associate Professor"}}
        self.assertEqual(vt.validate_members_data(data), [])

    def test_lines_pair_length_mismatch(self):
        data = {
            "professor": {
                "sections": [{
                    "title": "Activities",
                    "lines": ["한국건축학회, 2021", "another"],
                    "linesEn": ["Only one line"],
                }]
            }
        }
        issues = vt.validate_members_data(data)
        messages = [i.message for i in issues]
        self.assertTrue(any("linesEn has 1 entries but lines has 2" in m for m in messages), messages)

    def test_lines_pair_ok_when_matched(self):
        data = {
            "professor": {
                "sections": [{
                    "title": "Activities",
                    "lines": ["한국건축학회, 2021"],
                    "linesEn": ["Architectural Institute of Korea, 2021"],
                }]
            }
        }
        self.assertEqual(vt.validate_members_data(data), [])

    def test_technical_tags_are_not_demanded_translation(self):
        # "tags" has no documented English companion; must not be flagged.
        data = {"profiles": {"x": {"research": [{"page": "research-x", "tags": "#UBEM #calibration"}]}}}
        self.assertEqual(vt.validate_members_data(data), [])


class EnJsonValidationTest(unittest.TestCase):
    def test_hangul_value_rejected(self):
        issues = vt.validate_en_json_values({"nav.about": "소개"})
        messages = [i.message for i in issues]
        self.assertTrue(any("contains Hangul" in m for m in messages), messages)

    def test_empty_value_rejected(self):
        issues = vt.validate_en_json_values({"nav.about": ""})
        messages = [i.message for i in issues]
        self.assertTrue(any("value is empty" in m for m in messages), messages)

    def test_valid_values_pass(self):
        self.assertEqual(vt.validate_en_json_values({"nav.about": "About"}), [])

    def test_nested_values_are_validated_and_flattened(self):
        nested = {"nav": {"menuOpen": "Open menu"}, "dynamic": {"research": {"goal": "Goal"}}}
        self.assertEqual(vt.validate_en_json_values(nested), [])
        self.assertEqual(
            vt.flatten_en_json(nested),
            {"nav.menuOpen": "Open menu", "dynamic.research.goal": "Goal"},
        )

    def test_nested_hangul_value_reports_dotted_key(self):
        issues = vt.validate_en_json_values({"nav": {"menuOpen": "메뉴 열기"}})
        self.assertTrue(any(i.item == "nav.menuOpen" and "contains Hangul" in i.message for i in issues))


class HtmlScannerTest(unittest.TestCase):
    def test_uncovered_hangul_text_is_flagged(self):
        html = "<html><body><p>안녕하세요</p></body></html>"
        scanner = vt.scan_html(html)
        messages = [i.message for i in scanner.issues]
        self.assertTrue(any("not covered" in m for m in messages), messages)

    def test_data_i18n_covers_descendant_text(self):
        html = '<html><body><p data-i18n="greeting">안녕하세요</p></body></html>'
        scanner = vt.scan_html(html)
        self.assertEqual(scanner.issues, [])
        self.assertEqual(scanner.key_source.get("greeting"), "안녕하세요")

    def test_ancestor_covers_nested_text(self):
        html = '<div data-ko-parallel="true"><p><span>안녕하세요</span></p></div>'
        scanner = vt.scan_html(html)
        self.assertEqual(scanner.issues, [])

    def test_script_and_style_text_ignored(self):
        html = "<html><head><style>.a::before{content:'안녕'}</style></head>" \
               "<body><script>var x = '안녕하세요';</script></body></html>"
        scanner = vt.scan_html(html)
        self.assertEqual(scanner.issues, [])

    def test_attribute_hangul_requires_companion(self):
        html = '<img src="x.png" alt="설명 사진">'
        scanner = vt.scan_html(html)
        messages = [i.message for i in scanner.issues]
        self.assertTrue(any("data-i18n-alt" in m for m in messages), messages)

    def test_attribute_with_companion_passes(self):
        html = '<img src="x.png" alt="설명 사진" data-i18n-alt="photo.alt">'
        scanner = vt.scan_html(html)
        self.assertEqual(scanner.issues, [])
        self.assertEqual(scanner.key_source.get("photo.alt"), "설명 사진")

    def test_noncanonical_bee_lab_name_is_flagged_in_text_and_attribute(self):
        html = '<h1>BEE LAB News</h1><img src="x.png" alt="BEE Lab. Logo">'
        scanner = vt.scan_html(html)
        messages = [i.message for i in scanner.issues]
        self.assertIn("must spell the lab name as 'BEE Lab'", messages)
        self.assertIn("alt must spell the lab name as 'BEE Lab'", messages)

    def test_canonical_bee_lab_name_passes_in_text_and_attribute(self):
        html = '<h1>BEE Lab News</h1><img src="x.png" alt="BEE Lab Logo">'
        scanner = vt.scan_html(html)
        self.assertEqual(scanner.issues, [])

    def test_reused_key_with_different_source_is_flagged(self):
        html = '<p data-i18n="dup">가</p><p data-i18n="dup">나</p>'
        scanner = vt.scan_html(html)
        scanner_messages = [i.message for i in scanner.issues]
        self.assertTrue(any("different source values" in m for m in scanner_messages), scanner_messages)

    def test_reused_key_with_same_source_passes(self):
        html = '<p data-i18n="shared">같음</p><span data-i18n="shared">같음</span>'
        scanner = vt.scan_html(html)
        self.assertEqual(scanner.issues, [])

    def test_empty_data_ko_parallel_attribute_covers_text(self):
        scanner = vt.scan_html('<p data-ko-parallel>한국어 병렬 문단</p>')
        self.assertEqual(scanner.issues, [])

    def test_void_elements_do_not_break_stack(self):
        html = '<div><img src="a.png"><p data-i18n="k">텍스트</p></div>'
        scanner = vt.scan_html(html)
        self.assertEqual(scanner.key_source.get("k"), "텍스트")

    def test_dynamic_prefixed_keys_need_not_appear_in_html(self):
        # dynamic.* keys are consumed only by JS (BeeI18n.text); en.json may
        # contain them even though no data-i18n in the HTML references them.
        issues = vt.check_html_keys_exist_in_en(set(), {"dynamic.research.goal": "Goal"})
        self.assertEqual(issues, [])


class HtmlEnJsonIntegrationTest(unittest.TestCase):
    """Uses a temp directory to exercise the file-reading path end to end."""

    def test_full_validation_against_temp_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "i18n").mkdir()
            (root / "i18n" / "en.json").write_text('{"greeting": "Hello"}', encoding="utf-8")
            (root / "index.html").write_text(
                '<html><body><p data-i18n="greeting">안녕하세요</p></body></html>',
                encoding="utf-8",
            )
            issues, scanner, en_data = vt.validate_html_and_i18n(root)
            self.assertEqual(issues, [])
            self.assertIsNotNone(scanner)
            self.assertEqual(en_data, {"greeting": "Hello"})

    def test_missing_en_json_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<html><body>Hi</body></html>", encoding="utf-8")
            issues, _scanner, _en = vt.validate_html_and_i18n(root)
            messages = [i.message for i in issues]
            self.assertTrue(any(i.file == "i18n/en.json" and "not found" in i.message for i in issues), messages)


class DiffModeTest(unittest.TestCase):
    """Covers: source-only edit fails, paired edit passes, bootstrap base without ids,
    static stale key (HTML/en.json)."""

    def test_source_only_edit_fails(self):
        base = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "가", "titleEn": "A"}]
        current = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "나", "titleEn": "A"}]
        issues = vt.diff_id_collection("news.json", current, base, [("title", "titleEn")])
        messages = [i.message for i in issues]
        self.assertTrue(any("stale translation" in m for m in messages), messages)

    def test_paired_edit_passes(self):
        base = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "가", "titleEn": "A"}]
        current = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "나", "titleEn": "B"}]
        issues = vt.diff_id_collection("news.json", current, base, [("title", "titleEn")])
        self.assertEqual(issues, [])

    def test_uuid_case_change_does_not_bypass_stale_check(self):
        base = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "가", "titleEn": "A"}]
        current = [{"id": "3F2504E0-4F89-41D3-9A0C-0305E82C3301", "title": "나", "titleEn": "A"}]
        issues = vt.diff_id_collection("news.json", current, base, [("title", "titleEn")])
        messages = [i.message for i in issues]
        self.assertTrue(any("stale translation" in m for m in messages), messages)

    def test_unchanged_record_passes(self):
        base = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "가", "titleEn": "A"}]
        current = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "가", "titleEn": "A"}]
        issues = vt.diff_id_collection("news.json", current, base, [("title", "titleEn")])
        self.assertEqual(issues, [])

    def test_new_record_with_valid_pair_passes(self):
        base = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "가", "titleEn": "A"}]
        current = base + [{"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "title": "새 글", "titleEn": "New post"}]
        issues = vt.diff_id_collection("news.json", current, base, [("title", "titleEn")])
        self.assertEqual(issues, [])

    def test_bootstrap_base_without_ids_is_skipped_gracefully(self):
        # Simulates a pre-UUID-migration base file: records exist but carry no id.
        base = [{"title": "가", "titleEn": "A"}]
        current = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "나", "titleEn": "A"}]
        issues = vt.diff_id_collection("news.json", current, base, [("title", "titleEn")])
        self.assertEqual(issues, [])

    def test_bootstrap_base_missing_entirely_is_skipped_gracefully(self):
        current = [{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "나", "titleEn": "A"}]
        issues = vt.diff_id_collection("news.json", current, None, [("title", "titleEn")])
        self.assertEqual(issues, [])

    def test_members_diff_source_only_edit_fails(self):
        base = {"profiles": {"sangmin": {"name": "이상민", "nameEn": "Sangmin Lee"}}}
        current = {"profiles": {"sangmin": {"name": "이상민2", "nameEn": "Sangmin Lee"}}}
        issues = vt.diff_members_data(current, base)
        messages = [i.message for i in issues]
        self.assertTrue(any("stale translation" in m for m in messages), messages)

    def test_static_stale_key_in_html_is_flagged(self):
        current_key_source = {"greeting": "안녕히 가세요"}
        base_key_source = {"greeting": "안녕하세요"}
        current_en = {"greeting": "Hello"}
        base_en = {"greeting": "Hello"}
        issues = vt.diff_html_keys(current_key_source, base_key_source, current_en, base_en)
        messages = [i.message for i in issues]
        self.assertTrue(any("stale translation" in m for m in messages), messages)

    def test_html_key_change_with_updated_translation_passes(self):
        current_key_source = {"greeting": "안녕히 가세요"}
        base_key_source = {"greeting": "안녕하세요"}
        current_en = {"greeting": "Goodbye"}
        base_en = {"greeting": "Hello"}
        issues = vt.diff_html_keys(current_key_source, base_key_source, current_en, base_en)
        self.assertEqual(issues, [])

    def test_html_diff_tolerates_base_predating_i18n_migration(self):
        # Base has no i18n keys at all (pre-migration index.html): nothing to compare.
        current_key_source = {"greeting": "안녕하세요"}
        issues = vt.diff_html_keys(current_key_source, {}, {"greeting": "Hello"}, {})
        self.assertEqual(issues, [])

    # -- image diff by src (item 2) ------------------------------------------

    def test_image_caption_diff_by_src_flags_stale_translation(self):
        base = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [{"src": "photo.jpg", "caption": "설명", "captionEn": "Caption"}],
        }]
        current = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [{"src": "photo.jpg", "caption": "새로운 설명", "captionEn": "Caption"}],
        }]
        issues = vt.diff_images_by_src("news.json", current, base)
        messages = [i.message for i in issues]
        self.assertTrue(any("caption changed but captionEn unchanged" in m for m in messages), messages)

    def test_image_caption_diff_by_src_passes_when_captionen_updated(self):
        base = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [{"src": "photo.jpg", "caption": "설명", "captionEn": "Caption"}],
        }]
        current = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [{"src": "photo.jpg", "caption": "새로운 설명", "captionEn": "New caption"}],
        }]
        issues = vt.diff_images_by_src("news.json", current, base)
        self.assertEqual(issues, [])

    def test_image_diff_matches_by_src_even_if_order_changes(self):
        base = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [
                {"src": "a.jpg", "caption": "가", "captionEn": "A"},
                {"src": "b.jpg", "caption": "나", "captionEn": "B"},
            ],
        }]
        # Reordered in current, plus b.jpg's caption changed without captionEn.
        current = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [
                {"src": "b.jpg", "caption": "나2", "captionEn": "B"},
                {"src": "a.jpg", "caption": "가", "captionEn": "A"},
            ],
        }]
        issues = vt.diff_images_by_src("news.json", current, base)
        self.assertEqual(len(issues), 1)
        self.assertTrue(any("b.jpg" in i.item for i in issues), issues)

    def test_image_diff_bootstraps_when_base_predates_src(self):
        base = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [{"caption": "설명", "captionEn": "Caption"}],  # no src at all
        }]
        current = [{
            "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "images": [{"src": "photo.jpg", "caption": "새로운 설명", "captionEn": "Caption"}],
        }]
        issues = vt.diff_images_by_src("news.json", current, base)
        self.assertEqual(issues, [])

    # -- research diff by slug (item 3) --------------------------------------

    def test_research_diff_by_slug_flags_stale_translation(self):
        base = [{
            "id": "research-x",
            "researchers": [{"slug": "hyunwoo", "name": "임현우", "nameEn": "Hyunwoo Lim"}],
        }]
        current = [{
            "id": "research-x",
            "researchers": [{"slug": "hyunwoo", "name": "임현우2", "nameEn": "Hyunwoo Lim"}],
        }]
        issues = vt.diff_research_researchers("research-content/research.json", current, base)
        messages = [i.message for i in issues]
        self.assertTrue(any("stale translation" in m for m in messages), messages)

    def test_research_diff_by_slug_passes_when_nameen_updated(self):
        base = [{
            "id": "research-x",
            "researchers": [{"slug": "hyunwoo", "name": "임현우", "nameEn": "Hyunwoo Lim"}],
        }]
        current = [{
            "id": "research-x",
            "researchers": [{"slug": "hyunwoo", "name": "임현우2", "nameEn": "Hyunwoo Lim Jr."}],
        }]
        issues = vt.diff_research_researchers("research-content/research.json", current, base)
        self.assertEqual(issues, [])

    def test_research_diff_bootstraps_when_base_predates_slug(self):
        base = [{"id": "research-x", "researchers": [{"name": "임현우", "nameEn": "Hyunwoo Lim"}]}]
        current = [{
            "id": "research-x",
            "researchers": [{"slug": "hyunwoo", "name": "임현우2", "nameEn": "Hyunwoo Lim"}],
        }]
        issues = vt.diff_research_researchers("research-content/research.json", current, base)
        self.assertEqual(issues, [])

    # -- members diff: professor.sections by title, profile research by page (item 4) --

    def test_members_diff_sections_by_title_flags_stale_translation(self):
        base = {"professor": {"sections": [{"title": "Education", "lines": ["가"], "linesEn": ["A"]}]}}
        current = {"professor": {"sections": [{"title": "Education", "lines": ["가2"], "linesEn": ["A"]}]}}
        issues = vt.diff_members_data(current, base)
        messages = [i.message for i in issues]
        self.assertTrue(any("lines changed but linesEn unchanged" in m for m in messages), messages)

    def test_members_diff_sections_by_title_passes_when_linesen_updated(self):
        base = {"professor": {"sections": [{"title": "Education", "lines": ["가"], "linesEn": ["A"]}]}}
        current = {"professor": {"sections": [{"title": "Education", "lines": ["가2"], "linesEn": ["A2"]}]}}
        issues = vt.diff_members_data(current, base)
        self.assertEqual(issues, [])

    def test_members_diff_profile_research_by_page_flags_stale_translation(self):
        base = {"profiles": {"sangmin": {"research": [{"page": "research-chpwh", "title": "가", "titleEn": "A"}]}}}
        current = {"profiles": {"sangmin": {"research": [{"page": "research-chpwh", "title": "가2", "titleEn": "A"}]}}}
        issues = vt.diff_members_data(current, base)
        messages = [i.message for i in issues]
        self.assertTrue(any("title changed but titleEn unchanged" in m for m in messages), messages)

    def test_members_diff_profile_research_by_page_passes_when_titleen_updated(self):
        base = {"profiles": {"sangmin": {"research": [{"page": "research-chpwh", "title": "가", "titleEn": "A"}]}}}
        current = {"profiles": {"sangmin": {"research": [{"page": "research-chpwh", "title": "가2", "titleEn": "A2"}]}}}
        issues = vt.diff_members_data(current, base)
        self.assertEqual(issues, [])


class EndToEndRunTest(unittest.TestCase):
    """Golden-path smoke test for the top-level `run()` orchestrator using a
    fully self-contained temp directory (no repository files touched)."""

    def test_run_passes_on_fully_valid_minimal_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_valid_site(root)
            issues = vt.run(root, base_ref=None)
            self.assertEqual([i.format() for i in issues], [])

    def test_main_returns_nonzero_on_broken_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_valid_site(root)
            # Break it: Hangul text with no i18n coverage.
            (root / "index.html").write_text("<html><body><p>안녕하세요</p></body></html>", encoding="utf-8")
            rc = vt.main(["--root", str(root)])
            self.assertEqual(rc, 1)

    def test_main_returns_zero_on_valid_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_valid_site(root)
            rc = vt.main(["--root", str(root)])
            self.assertEqual(rc, 0)


class BaseRefValidationTest(unittest.TestCase):
    """Covers item 6: an invalid `--base` ref must fail clearly instead of
    silently skipping every stale-translation check, while a valid ref that
    predates individual files/ids must still bootstrap gracefully.

    Uses real `git` subprocesses, but only ever against a throwaway repo
    inside a fresh `tempfile.TemporaryDirectory()` -- the real repository is
    never touched.
    """

    def test_invalid_base_ref_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_valid_site(root)
            _init_git_repo(root)
            issues = vt.run(root, base_ref="this-ref-does-not-exist-anywhere")
            self.assertTrue(
                any(i.file == "--base" and "does not resolve to a commit" in i.message for i in issues),
                [i.format() for i in issues],
            )

    def test_invalid_base_ref_makes_main_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_valid_site(root)
            _init_git_repo(root)
            rc = vt.main(["--root", str(root), "--base", "totally-bogus-ref"])
            self.assertEqual(rc, 1)

    def test_valid_base_ref_with_no_stale_translations_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_valid_site(root)
            _init_git_repo(root)
            base_sha = _git_head(root)
            issues = vt.run(root, base_ref=base_sha)
            self.assertEqual([i.format() for i in issues], [])

    def test_valid_base_predating_ids_bootstraps_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Commit an initial site whose news.json predates the UUID
            # migration entirely (no "id" field at all).
            _write_minimal_valid_site(root)
            (root / "News_Blog_JPG" / "beelab_content" / "news.json").write_text(
                '[{"title": "가", "titleEn": "A"}]', encoding="utf-8"
            )
            _init_git_repo(root)
            base_sha = _git_head(root)

            # Working tree now has the same record migrated to a stable id
            # (uncommitted) -- `run()` reads current state from disk and the
            # base from git, so this simulates "base predates this id".
            (root / "News_Blog_JPG" / "beelab_content" / "news.json").write_text(
                '[{"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "title": "나", "titleEn": "A"}]',
                encoding="utf-8",
            )

            issues = vt.run(root, base_ref=base_sha)
            self.assertEqual([i.format() for i in issues], [])


if __name__ == "__main__":
    unittest.main()
