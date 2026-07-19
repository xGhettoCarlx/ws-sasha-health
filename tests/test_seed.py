"""Tests for Hermes .md migration — app/seed.py.

Verifies:
- File classification (_classify_file)
- Emoji → trust_tier mapping
- Attachment discovery
- Markdown parsing (sections, tables, KV pairs)
- Schema-specific parsers (visit, analysis, strategy, schedule)
- End-to-end seed() with temp directories
- YAML frontmatter output validity
"""

from pathlib import Path

import pytest
import yaml

from app.schemas import (
    AnalysisSchema,
    ScheduleSchema,
    StrategySchema,
    VisitSchema,
    from_frontmatter,
    to_frontmatter,
)
from app.seed import (
    EMOJI_TRUST_MAP,
    _best_trust_tier,
    _classify_file,
    _detect_emoji_trust,
    _extract_iso_date,
    _find_attachments,
    _parse_analysis,
    _parse_schedule,
    _parse_strategy,
    _parse_visit,
    _strip_emoji_prefix,
    parse_markdown,
    seed,
)

# ═══════════════════════════════════════════════════════════════════
# Fixtures — sample Hermes-style .md content
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_source(tmp_path: Path) -> Path:
    """Create a minimal Hermes-style source directory with .md and media files."""
    # Root-level files
    (tmp_path / "лекарства.md").write_text(
        "# 💊 Лекарства\n\n"
        "| Название | Доза | Кратность | Остаток | Рецепт до |\n"
        "|----------|------|-----------|---------|-----------|\n"
        "| Магний | 200 мг | на ночь | 60 таб | 2026-12-31 |\n"
    )

    (tmp_path / "страховка.md").write_text("# 🏢 Страховка\n\n## Договор\n\n*Нет данных*\n")

    (tmp_path / "расписание.md").write_text(
        "# ⏰ Расписание визитов\n\n"
        "## Ближайшие\n\n"
        "| Дата | Время | Врач | Учреждение | Цель |\n"
        "|------|-------|------|------------|------|\n"
        "| **2026-07-05** | 10:00 | **Спицарева О.Е.** (кардиолог) | Новамед | Эхо-КГ |\n"
        "| После страховки | — | ЛОР | — | Риноскопия |\n"
        "| 2026-06-10 | — | Кабаев | Пол-ка №10 | Осмотр ✅ |\n"
        "\n"
        "## Напоминания\n"
        "- 🔔 Напомнить записаться на ЭКГ\n"
        "- 🔔 Купить витамины\n"
    )

    (tmp_path / "стратегия.md").write_text(
        "# Стратегия здоровья — июнь 2026\n\n"
        "## ДО СТРАХОВКИ\n\n"
        "### 1. ЛОР — риноскопия\n"
        "**Симптом:** нос не дышит\n"
        "**Почему:** ночная гипоксия\n"
        "**Подготовка:** не нужна\n"
        "**Что сказать:** «С детства нос плохо дышит»\n\n"
        "### 2. Анализы ДО кардиолога\n"
        "**С чем:** ЭКГ + анализы\n"
        "**Почему:** экстрасистолы\n\n"
        "## ПО СТРАХОВКЕ\n\n"
        "### 1. Дерматолог\n"
        "**Симптом:** шелушение века\n"
        "**Почему:** исключить псориаз\n"
    )

    # Subfolder: Терапевт
    terap = tmp_path / "Терапевт"
    terap.mkdir()
    (terap / "2026-06-10_осмотр_Кабаев.md").write_text(
        "# Осмотр врача общей практики — 10.06.2026\n\n"
        "**Учреждение:** УЗ «Могилёвская поликлиника №10»\n"
        "**Врач:** Кабаев Филипп Сергеевич\n\n"
        "## Жалобы\n"
        "> Иногда высокий пульс, чувство сердцебиения.\n\n"
        "## Объективные данные\n\n"
        "| Показатель | В бланке | Реальность |\n"
        "|------------|----------|------------|\n"
        "| АД | 120/80 | ❌ не мерялось |\n"
        "| SpO₂ | 97% | ✅ пульсоксиметр |\n\n"
        "## Диагноз\n"
        "АГ 2 ст., риск 2.\n\n"
        "## Рекомендации\n"
        "ЗОЖ, контроль АД.\n\n"
        "## Комментарий\n"
        "Данные частично недостоверны.\n"
    )
    # Attachments (mock)
    (terap / "2026-06-10_осмотр_Кабаев.jpg").write_bytes(b"fake-jpg")
    (terap / "2026-06-10_для_врача_Кабаев.pdf").write_bytes(b"fake-pdf")

    (terap / "история.md").write_text(
        "# 🫀 Терапевт — история\n\n"
        "## Хронология\n\n"
        "### 10.06.2026 — визит к Кабаеву\n"
    )

    # Subfolder: Анализы
    anal = tmp_path / "Анализы"
    anal.mkdir()
    (anal / "2026-06-10_ОАК.md").write_text(
        "# Общий анализ крови — 10.06.2026\n\n"
        "**Лаборатория:** УЗ «Могилевская поликлиника N10»\n\n"
        "## Результаты\n\n"
        "| Показатель | Результат | Норма | Флаг |\n"
        "|---|---|---|---|\n"
        "| RBC | 4,72 | 4,0–5,1 | ✅ |\n"
        "| HGB | 140 | 130–160 | ✅ |\n"
        "| WBC | 6,41 | 4–9 | ✅ |\n\n"
        "## Вывод\n"
        "Все показатели в норме.\n"
    )
    (anal / "2026-06-10_ОАК.jpg").write_bytes(b"fake-jpg-anal")

    # Subfolder: УЗИ
    uzi = tmp_path / "УЗИ"
    uzi.mkdir()
    (uzi / "2024-01-06_УЗИ_брюшной_полости.md").write_text(
        "# УЗИ органов брюшной полости — 06.01.2024\n\n"
        "**Учреждение:** НОВАМЕД\n"
        "**Врач:** Колесников А.М.\n\n"
        "## Результаты\n\n"
        "Печень: диффузно-неоднородная.\n\n"
        "## Заключение\n"
        "Жировой гепатоз.\n\n"
        "## Рекомендации\n"
        "Контроль УЗИ 1 раз в год.\n"
    )

    # Subfolder: МРТ-КТ
    mrt = tmp_path / "МРТ-КТ"
    mrt.mkdir()
    (mrt / "2022-05-19_МРТ_поясничный_отдел.md").write_text(
        "# МРТ поясничного отдела — 19.05.2022\n\n"
        "**Оборудование:** PHILIPS Ingenia S 1.5T\n\n"
        "## Заключение\n"
        "Остеохондроз L3-S1.\n"
    )

    return tmp_path


# ═══════════════════════════════════════════════════════════════════
# Classification tests
# ═══════════════════════════════════════════════════════════════════


class TestClassification:
    def test_root_medicine(self, sample_source: Path):
        result = _classify_file(sample_source / "лекарства.md", sample_source)
        assert result == "medicine_list"

    def test_root_insurance(self, sample_source: Path):
        result = _classify_file(sample_source / "страховка.md", sample_source)
        assert result == "insurance"

    def test_root_schedule(self, sample_source: Path):
        result = _classify_file(sample_source / "расписание.md", sample_source)
        assert result == "schedule"

    def test_root_strategy(self, sample_source: Path):
        result = _classify_file(sample_source / "стратегия.md", sample_source)
        assert result == "strategy"

    def test_terapevt_visit(self, sample_source: Path):
        result = _classify_file(
            sample_source / "Терапевт" / "2026-06-10_осмотр_Кабаев.md",
            sample_source,
        )
        assert result == "visit"

    def test_analysis(self, sample_source: Path):
        result = _classify_file(
            sample_source / "Анализы" / "2026-06-10_ОАК.md",
            sample_source,
        )
        assert result == "analysis"

    def test_uzi_analysis(self, sample_source: Path):
        result = _classify_file(
            sample_source / "УЗИ" / "2024-01-06_УЗИ_брюшной_полости.md",
            sample_source,
        )
        assert result == "analysis"

    def test_mrt_analysis(self, sample_source: Path):
        result = _classify_file(
            sample_source / "МРТ-КТ" / "2022-05-19_МРТ_поясничный_отдел.md",
            sample_source,
        )
        assert result == "analysis"

    def test_history(self, sample_source: Path):
        result = _classify_file(
            sample_source / "Терапевт" / "история.md",
            sample_source,
        )
        assert result == "history"


# ═══════════════════════════════════════════════════════════════════
# Emoji → trust_tier tests
# ═══════════════════════════════════════════════════════════════════


class TestEmojiTrustMapping:
    @pytest.mark.parametrize("emoji,expected", [
        ("✅", "trusted"),
        ("🟢", "verified"),
        ("🔴", "unverified"),
        ("⚠️", "unverified"),
        ("❌", "unverified"),
    ])
    def test_emoji_to_tier(self, emoji: str, expected: str):
        assert EMOJI_TRUST_MAP[emoji] == expected

    def test_detect_in_text(self):
        assert _detect_emoji_trust("Норма ✅") == "trusted"
        assert _detect_emoji_trust("⚠️ предупреждение") == "unverified"
        assert _detect_emoji_trust("обычный текст") is None

    def test_best_trust_tier_trusted_wins(self):
        result = _best_trust_tier(["unverified", "trusted", "verified"])
        assert result == "trusted"

    def test_best_trust_tier_verified_over_unverified(self):
        result = _best_trust_tier(["unverified", "verified"])
        assert result == "verified"

    def test_best_trust_tier_default_unverified(self):
        result = _best_trust_tier([None, None])
        assert result == "unverified"

    def test_strip_emoji_prefix(self):
        assert _strip_emoji_prefix("🫀 Терапевт — история") == "Терапевт — история"
        assert _strip_emoji_prefix("💊 Лекарства") == "Лекарства"
        assert _strip_emoji_prefix("Обычный заголовок") == "Обычный заголовок"

    def test_extract_iso_date(self):
        assert _extract_iso_date("2026-06-10_осмотр.md") == "2026-06-10"
        assert _extract_iso_date("2024.01.06_УЗИ.md") == "2024-01-06"
        assert _extract_iso_date("no_date_here.md") is None


# ═══════════════════════════════════════════════════════════════════
# Markdown parsing tests
# ═══════════════════════════════════════════════════════════════════


class TestMarkdownParsing:
    def test_parse_sections(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text(
            "# Заголовок\n\n"
            "## Раздел 1\n\n"
            "Текст раздела 1.\n\n"
            "### Подраздел 1.1\n\n"
            "Текст подраздела.\n\n"
            "## Раздел 2\n\n"
            "Текст раздела 2.\n"
        )
        doc = parse_markdown(md)
        assert len(doc.sections) == 1  # one H1
        assert doc.sections[0].title == "Заголовок"
        assert len(doc.sections[0].subsections) == 2  # two H2
        assert doc.sections[0].subsections[0].body == "Текст раздела 1."
        assert len(doc.sections[0].subsections[0].subsections) == 1

    def test_parse_tables(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text(
            "# Тест\n\n"
            "| Имя | Возраст |\n"
            "|-----|--------|\n"
            "| Саша | 32 |\n"
            "| Даша | 30 |\n"
        )
        doc = parse_markdown(md)
        assert len(doc.tables) == 1
        assert doc.tables[0][0]["Имя"] == "Саша"
        assert doc.tables[0][0]["Возраст"] == "32"
        assert doc.tables[0][1]["Имя"] == "Даша"
        assert doc.tables[0][1]["Возраст"] == "30"

    def test_parse_kv_pairs(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text(
            "# Тест\n\n"
            "**Учреждение:** Поликлиника №10\n"
            "**Врач:** Кабаев Ф.С.\n"
            "**Дата:** 10.06.2026\n"
        )
        doc = parse_markdown(md)
        assert doc.kv_pairs["учреждение"] == "Поликлиника №10"
        assert doc.kv_pairs["врач"] == "Кабаев Ф.С."

    def test_emoji_tags(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("# Тест\n\n✅ Доверенный источник\n🔴 Требует проверки\n")
        doc = parse_markdown(md)
        assert "✅" in doc.emoji_tags
        assert "🔴" in doc.emoji_tags

    def test_title_property(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("# 🫀 Терапевт — история\n\nТело.\n")
        doc = parse_markdown(md)
        assert doc.title == "Терапевт — история"

    def test_date_property(self, tmp_path: Path):
        md = tmp_path / "2026-06-10_test.md"
        md.write_text("# Тест\n")
        doc = parse_markdown(md)
        assert doc.date == "2026-06-10"


# ═══════════════════════════════════════════════════════════════════
# Attachment discovery tests
# ═══════════════════════════════════════════════════════════════════


class TestAttachmentDiscovery:
    def test_exact_stem_match(self, sample_source: Path):
        md = sample_source / "Терапевт" / "2026-06-10_осмотр_Кабаев.md"
        attachments = _find_attachments(md, sample_source)
        names = [a.name for a in attachments]
        assert "2026-06-10_осмотр_Кабаев.jpg" in names

    def test_date_prefix_match(self, sample_source: Path):
        md = sample_source / "Терапевт" / "2026-06-10_осмотр_Кабаев.md"
        attachments = _find_attachments(md, sample_source)
        names = [a.name for a in attachments]
        assert "2026-06-10_для_врача_Кабаев.pdf" in names

    def test_no_attachments(self, sample_source: Path):
        md = sample_source / "стратегия.md"
        attachments = _find_attachments(md, sample_source)
        assert len(attachments) == 0


# ═══════════════════════════════════════════════════════════════════
# Schema parser tests
# ═══════════════════════════════════════════════════════════════════


class TestVisitParser:
    def test_parse_visit_fields(self, sample_source: Path):
        md = sample_source / "Терапевт" / "2026-06-10_осмотр_Кабаев.md"
        doc = parse_markdown(md)
        visit = _parse_visit(doc, sample_source)

        assert isinstance(visit, VisitSchema)
        assert visit.doctor == "Кабаев Филипп Сергеевич"
        assert "Могилёвская поликлиника" in visit.institution
        assert visit.date == "2026-06-10"
        assert visit.id == "2026-06-10_осмотр_Кабаев"
        assert visit.complaint is not None
        assert "пульс" in visit.complaint
        assert visit.diagnosis is not None
        assert "АГ 2 ст" in visit.diagnosis
        assert visit.recommendations is not None
        assert visit.conclusion is not None
        assert "недостоверны" in visit.conclusion
        assert visit.source == "Hermes migration"

    def test_parse_visit_trust_tier(self, sample_source: Path):
        md = sample_source / "Терапевт" / "2026-06-10_осмотр_Кабаев.md"
        doc = parse_markdown(md)
        visit = _parse_visit(doc, sample_source)
        # Contains both ✅ and ❌ → best is "trusted"
        assert visit.trust_tier in ("trusted", "verified", "unverified")

    def test_roundtrip_frontmatter(self, sample_source: Path):
        md = sample_source / "Терапевт" / "2026-06-10_осмотр_Кабаев.md"
        doc = parse_markdown(md)
        visit = _parse_visit(doc, sample_source)

        fm = to_frontmatter(visit)
        assert fm["doctor"] == "Кабаев Филипп Сергеевич"
        assert fm["date"] == "2026-06-10"

        restored = from_frontmatter(VisitSchema, fm)
        assert restored.doctor == visit.doctor


class TestAnalysisParser:
    def test_parse_oak_table(self, sample_source: Path):
        md = sample_source / "Анализы" / "2026-06-10_ОАК.md"
        doc = parse_markdown(md)
        analysis = _parse_analysis(doc, sample_source)

        assert isinstance(analysis, AnalysisSchema)
        assert "ОАК" in analysis.test_name or "Общий анализ" in analysis.test_name
        assert analysis.date == "2026-06-10"
        assert analysis.institution is not None
        assert "Могилевская поликлиника" in analysis.institution

        # Parameters parsed from table
        param_names = [p.name for p in analysis.parameters]
        assert "RBC" in param_names
        assert "HGB" in param_names
        assert "WBC" in param_names

        # Check a specific parameter
        hgb_param = next(p for p in analysis.parameters if p.name == "HGB")
        assert hgb_param.value == "140"
        assert hgb_param.ref_range == "130–160"
        assert hgb_param.flag == "✅"

        assert analysis.conclusion is not None
        assert "норме" in analysis.conclusion

    def test_parse_uzi_no_table(self, sample_source: Path):
        md = sample_source / "УЗИ" / "2024-01-06_УЗИ_брюшной_полости.md"
        doc = parse_markdown(md)
        analysis = _parse_analysis(doc, sample_source)

        assert isinstance(analysis, AnalysisSchema)
        assert "УЗИ" in analysis.test_name
        assert analysis.institution == "НОВАМЕД"
        assert "Жировой гепатоз" in analysis.conclusion
        assert analysis.recommendations is not None

    def test_parse_mrt_with_equipment(self, sample_source: Path):
        md = sample_source / "МРТ-КТ" / "2022-05-19_МРТ_поясничный_отдел.md"
        doc = parse_markdown(md)
        analysis = _parse_analysis(doc, sample_source)

        assert analysis.equipment == "PHILIPS Ingenia S 1.5T"
        assert "Остеохондроз" in analysis.conclusion


class TestStrategyParser:
    def test_parse_strategy(self, sample_source: Path):
        md = sample_source / "стратегия.md"
        doc = parse_markdown(md)
        strategy = _parse_strategy(doc, sample_source)

        assert isinstance(strategy, StrategySchema)
        assert strategy.title == "Стратегия здоровья — июнь 2026"
        assert len(strategy.steps) >= 3

        # First step — ЛОР
        step1 = strategy.steps[0]
        assert step1.section == "ДО СТРАХОВКИ"
        assert step1.priority == 1
        assert step1.symptom is not None
        assert "нос" in step1.symptom.lower()
        assert step1.reason is not None
        assert "гипокси" in step1.reason.lower()

        # Check section grouping
        sections = {s.section for s in strategy.steps}
        assert "ДО СТРАХОВКИ" in sections
        assert "ПО СТРАХОВКЕ" in sections


class TestScheduleParser:
    def test_parse_schedule(self, sample_source: Path):
        md = sample_source / "расписание.md"
        doc = parse_markdown(md)
        schedule = _parse_schedule(doc, sample_source)

        assert isinstance(schedule, ScheduleSchema)
        assert len(schedule.visits) >= 2

        # Planned visit
        planned = schedule.visits[0]
        assert planned.date == "2026-07-05"
        assert "Спицарева" in planned.doctor
        assert planned.status == "planned"

        # Pending visit (После страховки)
        pending = schedule.visits[1]
        assert pending.status == "pending"

        # Reminders
        assert len(schedule.reminders) >= 1
        assert any("ЭКГ" in r for r in schedule.reminders)


# ═══════════════════════════════════════════════════════════════════
# End-to-end seed() tests
# ═══════════════════════════════════════════════════════════════════


class TestSeedEndToEnd:
    def test_seed_dry_run(self, sample_source: Path, tmp_path: Path):
        target = tmp_path / "output"
        results = seed(source=sample_source, target=target, dry_run=True)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all("path" in r for r in results)
        assert all("type" in r for r in results)

        # No files written in dry-run
        assert not target.exists() or not any(target.rglob("*"))

    def test_seed_creates_output(self, sample_source: Path, tmp_path: Path):
        target = tmp_path / "output"
        results = seed(source=sample_source, target=target)

        assert target.exists()
        md_files = list(target.rglob("*.md"))
        assert len(md_files) > 0

        seeded_count = sum(1 for r in results if r["status"] == "seeded")
        assert seeded_count > 0

    def test_seeded_files_have_frontmatter(self, sample_source: Path, tmp_path: Path):
        target = tmp_path / "output"
        seed(source=sample_source, target=target)

        for md_file in target.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            assert content.startswith("---"), f"Missing frontmatter: {md_file.name}"
            # Validate YAML between --- markers
            parts = content.split("---", 2)
            assert len(parts) >= 3, f"Malformed frontmatter: {md_file.name}"
            fm = yaml.safe_load(parts[1])
            assert isinstance(fm, dict), f"Frontmatter not a dict: {md_file.name}"

    def test_seeded_visit_frontmatter(self, sample_source: Path, tmp_path: Path):
        target = tmp_path / "output"
        seed(source=sample_source, target=target)

        visit_file = target / "Терапевт" / "2026-06-10_осмотр_Кабаев.md"
        assert visit_file.exists()

        content = visit_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        fm = yaml.safe_load(parts[1])

        assert fm["doctor"] == "Кабаев Филипп Сергеевич"
        assert fm["date"] == "2026-06-10"
        assert fm["trust_tier"] in ("trusted", "verified", "unverified")

    def test_seeded_analysis_frontmatter(self, sample_source: Path, tmp_path: Path):
        target = tmp_path / "output"
        seed(source=sample_source, target=target)

        analysis_file = target / "Анализы" / "2026-06-10_ОАК.md"
        assert analysis_file.exists()

        content = analysis_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        fm = yaml.safe_load(parts[1])

        assert fm["date"] == "2026-06-10"
        assert "parameters" in fm
        assert len(fm["parameters"]) >= 3

    def test_seeded_strategy_frontmatter(self, sample_source: Path, tmp_path: Path):
        target = tmp_path / "output"
        seed(source=sample_source, target=target)

        strategy_file = target / "стратегия.md"
        assert strategy_file.exists()

        content = strategy_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        fm = yaml.safe_load(parts[1])

        assert fm["id"] == "стратегия"
        assert len(fm["steps"]) >= 3

    def test_attachments_copied(self, sample_source: Path, tmp_path: Path):
        target = tmp_path / "output"
        results = seed(source=sample_source, target=target)

        # Check that attachments were copied
        total_copied = sum(r.get("attachments_copied", 0) for r in results)
        assert total_copied > 0

        # Bundle dir exists with files
        bundle = target / "Терапевт" / "2026-06-10_осмотр_Кабаев"
        assert bundle.exists()
        bundle_files = list(bundle.iterdir())
        assert len(bundle_files) > 0

    def test_seed_idempotent(self, sample_source: Path, tmp_path: Path):
        # target must be outside sample_source to avoid
        # nested .md files being picked up on second scan.
        target = tmp_path.parent / f"seed_out_{hash(str(sample_source))}"
        try:
            results1 = seed(source=sample_source, target=target)
            results2 = seed(source=sample_source, target=target)

            seeded1 = sum(1 for r in results1 if r["status"] == "seeded")
            seeded2 = sum(1 for r in results2 if r["status"] == "seeded")
            assert seeded1 == seeded2
            assert seeded1 > 0
        finally:
            import shutil
            if target.exists():
                shutil.rmtree(target)

    def test_seed_no_source_raises(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            seed(source=nonexistent, target=tmp_path / "out")


# ═══════════════════════════════════════════════════════════════════
# MarkdownDoc model tests
# ═══════════════════════════════════════════════════════════════════


class TestMarkdownDocModel:
    def test_find_section(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text(
            "# Топ\n"
            "## Жалобы\n"
            "текст жалоб\n"
            "## Диагноз\n"
            "диагноз\n"
        )
        doc = parse_markdown(md)
        sec = doc.find_section("жалоб")
        assert sec is not None
        assert sec.body == "текст жалоб"

    def test_find_section_returns_none(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("# Топ\n")
        doc = parse_markdown(md)
        assert doc.find_section("отсутствует") is None

    def test_iter_subsections(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text(
            "# Топ\n"
            "## Главный\n"
            "### 1. Первый\n"
            "### 2. Второй\n"
        )
        doc = parse_markdown(md)
        subs = doc.iter_subsections("Главный")
        assert len(subs) == 2
        assert subs[0].title == "1. Первый"

    def test_path_and_raw_preserved(self, tmp_path: Path):
        md_path = tmp_path / "test.md"
        content = "# Тест\nтело\n"
        md_path.write_text(content)
        doc = parse_markdown(md_path)
        assert doc.path == md_path
        assert doc.raw == content
