"""Tests for all Pydantic v2 health .md schemas.

Each schema gets at least 2 tests:
    1. Valid minimal data — ensures construction succeeds with defaults.
    2. Missing required field — ensures ValidationError is raised.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalysisSchema,
    CommonBase,
    DiagnosisItem,
    DiagnosticFinding,
    FluorographyRecord,
    FluorographySchema,
    InboxItemSchema,
    InsurancePolicy,
    InsuranceSchema,
    MedicineSchema,
    OcrStatus,
    ParameterItem,
    ProfileSchema,
    ScheduleSchema,
    StrategySchema,
    StrategyStep,
    SymptomDiarySchema,
    SymptomEntry,
    TrustTier,
    VisitItem,
    VisitSchema,
    from_frontmatter,
    to_frontmatter,
)

# ═══════════════════════════════════════════════════════════════════
# CommonBase
# ═══════════════════════════════════════════════════════════════════


class TestCommonBase:
    def test_valid_minimal(self):
        """CommonBase with only required fields."""
        obj = CommonBase(trust_tier="verified", date="2026-06-10")
        assert obj.trust_tier == "verified"
        assert obj.date == "2026-06-10"
        assert obj.tags == []  # default_factory
        assert obj.id is None

    def test_all_fields(self):
        """CommonBase with all fields populated."""
        obj = CommonBase(
            id="test-123",
            trust_tier="trusted",
            tags=["терапевт", "анализы"],
            date="2026-06-10",
            source="электронный кабинет",
            content="# Test\n\nBody text",
        )
        assert obj.id == "test-123"
        assert obj.trust_tier == "trusted"
        assert obj.tags == ["терапевт", "анализы"]
        assert obj.source == "электронный кабинет"
        assert obj.content == "# Test\n\nBody text"

    def test_missing_trust_tier_raises(self):
        """trust_tier is required."""
        with pytest.raises(ValidationError):
            CommonBase(date="2026-06-10")

    def test_missing_date_raises(self):
        """date is required."""
        with pytest.raises(ValidationError):
            CommonBase(trust_tier="verified")

    def test_invalid_trust_tier_raises(self):
        """Only 'unverified', 'verified', 'trusted' are allowed."""
        with pytest.raises(ValidationError):
            CommonBase(trust_tier="super-duper", date="2026-06-10")


# ═══════════════════════════════════════════════════════════════════
# ProfileSchema
# ═══════════════════════════════════════════════════════════════════


class TestProfileSchema:
    def test_valid_minimal(self):
        """Profile with only required fields."""
        p = ProfileSchema(
            full_name="Калинов Александр Игоревич",
            birth_date="1993-08-26",
            trust_tier="verified",
            date="2026-06-30",
        )
        assert p.full_name == "Калинов Александр Игоревич"
        assert p.birth_date == "1993-08-26"
        assert p.diagnoses == []
        assert p.allergies == []

    def test_with_diagnoses_and_allergies(self):
        """Profile with nested DiagnosisItem entries."""
        p = ProfileSchema(
            full_name="Калинов Александр Игоревич",
            birth_date="1993-08-26",
            trust_tier="verified",
            date="2026-06-30",
            diagnoses=[
                DiagnosisItem(
                    status="🔴 Активен",
                    name="Жировой гепатоз",
                    source="УЗИ 01.2024",
                    trust_tier="trusted",
                    date="2024-01-06",
                ),
                DiagnosisItem(
                    status="🟡 Ремиссия",
                    name="ЯБ луковицы ДПК",
                    trust_tier="verified",
                    date="2026-06-10",
                ),
            ],
            allergies=["Парлазин Нео"],
        )
        assert len(p.diagnoses) == 2
        assert p.diagnoses[0].name == "Жировой гепатоз"
        assert p.diagnoses[1].status == "🟡 Ремиссия"
        assert p.allergies == ["Парлазин Нео"]

    def test_missing_full_name_raises(self):
        with pytest.raises(ValidationError):
            ProfileSchema(
                birth_date="1993-08-26",
                trust_tier="verified",
                date="2026-06-30",
            )

    def test_missing_birth_date_raises(self):
        with pytest.raises(ValidationError):
            ProfileSchema(
                full_name="Калинов А.И.",
                trust_tier="verified",
                date="2026-06-30",
            )


# ═══════════════════════════════════════════════════════════════════
# StrategySchema
# ═══════════════════════════════════════════════════════════════════


class TestStrategySchema:
    def test_valid_minimal(self):
        """Strategy with only required fields."""
        s = StrategySchema(
            title="Стратегия здоровья — июнь 2026",
            updated="2026-06-07",
            trust_tier="verified",
            date="2026-06-07",
        )
        assert s.title == "Стратегия здоровья — июнь 2026"
        assert s.updated == "2026-06-07"
        assert s.steps == []

    def test_with_steps(self):
        """Strategy with nested StrategyStep entries."""
        s = StrategySchema(
            title="Стратегия здоровья",
            updated="2026-06-07",
            trust_tier="verified",
            date="2026-06-07",
            steps=[
                StrategyStep(
                    section="ДО СТРАХОВКИ",
                    priority=1,
                    symptom="Нос не дышит",
                    reason="Ночная гипоксия + АГ",
                    preparation="Не нужна",
                    what_to_say="С детства нос плохо дышит",
                    trust_tier="verified",
                    date="2026-06-07",
                ),
            ],
        )
        assert len(s.steps) == 1
        assert s.steps[0].section == "ДО СТРАХОВКИ"
        assert s.steps[0].what_to_say is not None
        assert "нос" in s.steps[0].symptom.lower()

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            StrategySchema(
                updated="2026-06-07",
                trust_tier="verified",
                date="2026-06-07",
            )

    def test_missing_updated_raises(self):
        with pytest.raises(ValidationError):
            StrategySchema(
                title="Стратегия здоровья",
                trust_tier="verified",
                date="2026-06-07",
            )


# ═══════════════════════════════════════════════════════════════════
# ScheduleSchema
# ═══════════════════════════════════════════════════════════════════


class TestScheduleSchema:
    def test_valid_minimal(self):
        """Schedule with only required fields."""
        s = ScheduleSchema(
            trust_tier="verified",
            date="2026-06-14",
        )
        assert s.visits == []
        assert s.reminders == []

    def test_with_visits(self):
        """Schedule with nested VisitItem entries."""
        s = ScheduleSchema(
            trust_tier="verified",
            date="2026-06-14",
            visits=[
                VisitItem(
                    date="2026-07-05",
                    time="10:00",
                    doctor="Спицарева О.Е. (кардиолог)",
                    institution="Новамед",
                    purpose="Кардиолог + Эхо-КГ",
                    status="planned",
                    trust_tier="verified",
                ),
                VisitItem(
                    date="2026-06-08",
                    doctor="Кабаев Ф.С.",
                    institution="Поликлиника №10",
                    purpose="Осмотр",
                    status="completed",
                    trust_tier="trusted",
                ),
            ],
            reminders=["Напомнить записаться на ЭКГ"],
        )
        assert len(s.visits) == 2
        assert s.visits[0].status == "planned"
        assert s.visits[1].status == "completed"
        assert s.reminders == ["Напомнить записаться на ЭКГ"]

    def test_missing_visits_ok(self):
        """visits field defaults to empty list, no error."""
        s = ScheduleSchema(trust_tier="verified", date="2026-06-14")
        assert s.visits == []

    def test_invalid_visit_status_raises(self):
        """VisitStatus must be one of the literal values."""
        with pytest.raises(ValidationError):
            VisitItem(
                date="2026-07-05",
                doctor="Доктор",
                purpose="Осмотр",
                status="unknown_status",
                trust_tier="verified",
            )


# ═══════════════════════════════════════════════════════════════════
# MedicineSchema
# ═══════════════════════════════════════════════════════════════════


class TestMedicineSchema:
    def test_valid_minimal(self):
        """Medicine with only required fields."""
        m = MedicineSchema(
            name="Магний",
            dose="200 мг",
            frequency="на ночь",
            trust_tier="verified",
            date="2026-06-07",
        )
        assert m.name == "Магний"
        assert m.dose == "200 мг"
        assert m.stock is None

    def test_with_all_fields(self):
        """Medicine with all optional fields."""
        m = MedicineSchema(
            name="Парлазин Нео",
            dose="5 мг",
            frequency="при аллергии",
            stock="20 таб",
            prescription_expiry="2026-12-31",
            notes="Сезонная аллергия, весна",
            trust_tier="verified",
            date="2026-06-07",
        )
        assert m.stock == "20 таб"
        assert m.prescription_expiry == "2026-12-31"
        assert m.notes == "Сезонная аллергия, весна"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            MedicineSchema(
                dose="200 мг",
                frequency="на ночь",
                trust_tier="verified",
                date="2026-06-07",
            )

    def test_missing_dose_raises(self):
        with pytest.raises(ValidationError):
            MedicineSchema(
                name="Магний",
                frequency="на ночь",
                trust_tier="verified",
                date="2026-06-07",
            )


# ═══════════════════════════════════════════════════════════════════
# InsuranceSchema
# ═══════════════════════════════════════════════════════════════════


class TestInsuranceSchema:
    def test_valid_minimal(self):
        """Insurance with only required fields."""
        i = InsuranceSchema(
            trust_tier="verified",
            date="2026-06-07",
        )
        assert i.policies == []

    def test_with_policies(self):
        """Insurance with nested InsurancePolicy entries."""
        i = InsuranceSchema(
            trust_tier="verified",
            date="2026-06-07",
            policies=[
                InsurancePolicy(
                    policy="Даша (как муж)",
                    sum_insured=930.0,
                    spent=0,
                    remaining=930.0,
                    expiry="2026-12-31",
                    trust_tier="trusted",
                    date="2026-01-01",
                ),
                InsurancePolicy(
                    policy="Беларусбанк",
                    sum_insured=480.0,
                    spent=100.0,
                    remaining=380.0,
                    trust_tier="verified",
                    date="2026-01-01",
                ),
            ],
        )
        assert len(i.policies) == 2
        assert i.policies[0].remaining == 930.0
        assert i.policies[1].spent == 100.0

    def test_negative_sum_insured_raises(self):
        with pytest.raises(ValidationError):
            InsurancePolicy(
                policy="Тест",
                sum_insured=-100,
                spent=0,
                remaining=0,
                trust_tier="verified",
                date="2026-01-01",
            )


# ═══════════════════════════════════════════════════════════════════
# FluorographySchema
# ═══════════════════════════════════════════════════════════════════


class TestFluorographySchema:
    def test_valid_minimal(self):
        """Fluorography with only required fields."""
        f = FluorographySchema(
            trust_tier="trusted",
            date="2026-07-02",
        )
        assert f.history == []
        assert f.next_due is None

    def test_with_history(self):
        """Fluorography with nested FluorographyRecord entries."""
        f = FluorographySchema(
            trust_tier="trusted",
            date="2026-07-02",
            source="Электронный кабинет (tutmed.by)",
            tags=["флюорография", "профилактика"],
            history=[
                FluorographyRecord(
                    date="2026-06-10",
                    number="10254",
                    result="Отрицательный (норма) ✅",
                    institution="УЗ «Могилёвская поликлиника №10»",
                    trust_tier="trusted",
                ),
                FluorographyRecord(
                    date="2025-03-11",
                    number="3322",
                    result="Отрицательный (норма) ✅",
                    institution="УЗ «Могилёвская поликлиника №10»",
                    trust_tier="trusted",
                ),
                FluorographyRecord(
                    date="2023-12-18",
                    number="9130",
                    result="Отрицательный (норма) ✅",
                    institution="УЗ «Могилёвская поликлиника №10'",
                    trust_tier="trusted",
                ),
                FluorographyRecord(
                    date="2021-12-16",
                    number="Н13552",
                    result="Отрицательный (норма) ✅",
                    institution="УЗ «Могилёвская поликлиника №10'",
                    trust_tier="trusted",
                ),
            ],
            next_due="2027-06-01",
        )
        assert len(f.history) == 4
        assert f.history[0].number == "10254"
        assert f.history[0].result == "Отрицательный (норма) ✅"
        assert f.history[3].number == "Н13552"
        assert f.next_due == "2027-06-01"

    def test_missing_number_raises(self):
        """FluorographyRecord requires number."""
        with pytest.raises(ValidationError):
            FluorographyRecord(
                date="2026-06-10",
                result="Отрицательный (норма) ✅",
                institution="УЗ «Могилёвская поликлиника №10»",
                trust_tier="trusted",
            )

    def test_missing_result_raises(self):
        """FluorographyRecord requires result."""
        with pytest.raises(ValidationError):
            FluorographyRecord(
                date="2026-06-10",
                number="10254",
                institution="УЗ «Могилёвская поликлиника №10»",
                trust_tier="trusted",
            )

    def test_missing_institution_raises(self):
        """FluorographyRecord requires institution."""
        with pytest.raises(ValidationError):
            FluorographyRecord(
                date="2026-06-10",
                number="10254",
                result="Отрицательный (норма) ✅",
                trust_tier="trusted",
            )


# ═══════════════════════════════════════════════════════════════════
# SymptomDiarySchema
# ═══════════════════════════════════════════════════════════════════


class TestSymptomDiarySchema:
    def test_valid_minimal(self):
        """Symptom diary with only required fields."""
        s = SymptomDiarySchema(
            trust_tier="verified",
            date="2026-06-07",
        )
        assert s.entries == []

    def test_with_entries(self):
        """Symptom diary with SymptomEntry items."""
        s = SymptomDiarySchema(
            trust_tier="verified",
            date="2026-06-07",
            entries=[
                SymptomEntry(
                    date="2026-06-07",
                    symptom="Одышка в покое лёжа",
                    severity=4,
                    notes="После чашки кофе",
                    trust_tier="verified",
                ),
                SymptomEntry(
                    date="2026-06-06",
                    symptom="Экстрасистолы",
                    severity=3,
                    trust_tier="verified",
                ),
            ],
        )
        assert len(s.entries) == 2
        assert s.entries[0].severity == 4
        assert s.entries[1].symptom == "Экстрасистолы"

    def test_severity_out_of_range_raises(self):
        """Severity must be 1-10."""
        with pytest.raises(ValidationError):
            SymptomEntry(
                date="2026-06-07",
                symptom="Боль",
                severity=0,
                trust_tier="verified",
            )

        with pytest.raises(ValidationError):
            SymptomEntry(
                date="2026-06-07",
                symptom="Боль",
                severity=11,
                trust_tier="verified",
            )


# ═══════════════════════════════════════════════════════════════════
# AnalysisSchema
# ═══════════════════════════════════════════════════════════════════


class TestAnalysisSchema:
    def test_valid_minimal(self):
        """Analysis with only required fields."""
        a = AnalysisSchema(
            test_name="Биохимический анализ крови",
            trust_tier="trusted",
            date="2026-06-10",
        )
        assert a.test_name == "Биохимический анализ крови"
        assert a.parameters == []

    def test_with_parameters(self):
        """Analysis with ParameterItem entries and conclusion."""
        a = AnalysisSchema(
            test_name="Биохимический анализ крови",
            trust_tier="trusted",
            date="2026-06-10",
            institution="УЗ «Могилевская поликлиника N10»",
            parameters=[
                ParameterItem(
                    name="Белок общий",
                    value="76,0 г/л",
                    unit="г/л",
                    ref_range="65–85",
                    flag="✅",
                    trust_tier="trusted",
                    date="2026-06-10",
                ),
                ParameterItem(
                    name="Билирубин общий",
                    value="22,29 мкмоль/л",
                    unit="мкмоль/л",
                    ref_range="0–18",
                    flag="🔴",
                    trust_tier="trusted",
                    date="2026-06-10",
                ),
            ],
            conclusion="Билирубин снижается, но ещё выше нормы. АлАТ снижается.",
        )
        assert len(a.parameters) == 2
        assert a.parameters[0].flag == "✅"
        assert a.parameters[1].flag == "🔴"
        assert "билирубин" in a.conclusion.lower()

    def test_missing_test_name_raises(self):
        with pytest.raises(ValidationError):
            AnalysisSchema(
                trust_tier="trusted",
                date="2026-06-10",
            )


# ═══════════════════════════════════════════════════════════════════
# VisitSchema
# ═══════════════════════════════════════════════════════════════════


class TestVisitSchema:
    def test_valid_minimal(self):
        """Visit with only required fields."""
        v = VisitSchema(
            date="2026-06-10",
            doctor="Кабаев Ф.С. (ВОП)",
            institution="УЗ «Могилёвская поликлиника №10»",
            trust_tier="verified",
        )
        assert v.doctor == "Кабаев Ф.С. (ВОП)"
        assert v.objective_data == []

    def test_with_full_data(self):
        """Visit with all fields including objective data."""
        v = VisitSchema(
            date="2026-06-10",
            doctor="Кабаев Филипп Сергеевич",
            institution="УЗ «Могилёвская поликлиника №10»",
            trust_tier="verified",
            complaint="Иногда высокий пульс, чувство сердцебиения",
            objective_status="Состояние удовлетворительное.",
            objective_data=[
                DiagnosticFinding(
                    parameter="АД",
                    recorded_value="120/80",
                    real_value="не мерялось",
                    reliability="❌ выдумано",
                    trust_tier="unverified",
                    date="2026-06-10",
                ),
                DiagnosticFinding(
                    parameter="SpO₂",
                    recorded_value="97%",
                    reliability="✅",
                    trust_tier="verified",
                    date="2026-06-10",
                ),
            ],
            diagnosis="АГ 2 ст., риск 2. ЯБ луковицы ДПК, ремиссия.",
            recommendations="ЗОЖ, режим, контроль АД, бессолевая диета.",
            conclusion="Данные в бланке частично недостоверны.",
        )
        assert v.complaint is not None
        assert "пульс" in v.complaint
        assert len(v.objective_data) == 2
        assert v.objective_data[0].reliability == "❌ выдумано"

    def test_missing_doctor_raises(self):
        with pytest.raises(ValidationError):
            VisitSchema(
                date="2026-06-10",
                institution="Поликлиника",
                trust_tier="verified",
            )

    def test_missing_institution_raises(self):
        with pytest.raises(ValidationError):
            VisitSchema(
                date="2026-06-10",
                doctor="Врач",
                trust_tier="verified",
            )


# ═══════════════════════════════════════════════════════════════════
# InboxItemSchema
# ═══════════════════════════════════════════════════════════════════


class TestInboxItemSchema:
    def test_valid_minimal(self):
        """Inbox item with only required fields."""
        item = InboxItemSchema(
            filename="жалоба_гермес_10.06.2026.md",
            created_at="2026-06-10T11:00:00",
            trust_tier="unverified",
            date="2026-06-10",
        )
        assert item.filename == "жалоба_гермес_10.06.2026.md"
        assert item.ocr_status == "pending"
        assert item.extracted_data == {}
        assert item.processed is False

    def test_with_all_fields(self):
        """Inbox item with processed data."""
        item = InboxItemSchema(
            filename="направление_биохимия.jpg",
            original_path="/Hermes/.../направление_биохимия.jpg",
            ocr_status="completed",
            extracted_data={"test_name": "Биохимия", "date": "2026-06-10"},
            created_at="2026-06-10T14:30:00",
            processed=True,
            source_tier="verified",
            trust_tier="verified",
            date="2026-06-10",
        )
        assert item.ocr_status == "completed"
        assert item.extracted_data["test_name"] == "Биохимия"
        assert item.processed is True
        assert item.source_tier == "verified"

    def test_missing_filename_raises(self):
        with pytest.raises(ValidationError):
            InboxItemSchema(
                created_at="2026-06-10T11:00:00",
                trust_tier="unverified",
                date="2026-06-10",
            )

    def test_missing_created_at_raises(self):
        with pytest.raises(ValidationError):
            InboxItemSchema(
                filename="test.md",
                trust_tier="unverified",
                date="2026-06-10",
            )

    def test_invalid_ocr_status_raises(self):
        with pytest.raises(ValidationError):
            InboxItemSchema(
                filename="test.md",
                ocr_status="unknown",
                created_at="2026-06-10T11:00:00",
                trust_tier="unverified",
                date="2026-06-10",
            )


# ═══════════════════════════════════════════════════════════════════
# Frontmatter
# ═══════════════════════════════════════════════════════════════════


class TestFrontmatter:
    def test_to_frontmatter_roundtrip(self):
        """to_frontmatter produces dict, from_frontmatter reconstructs."""
        original = MedicineSchema(
            name="Магний",
            dose="200 мг",
            frequency="на ночь",
            stock="60 таб",
            trust_tier="verified",
            date="2026-06-07",
            source="Hermes",
        )

        fm_dict = to_frontmatter(original)
        assert fm_dict["name"] == "Магний"
        assert fm_dict["dose"] == "200 мг"
        assert fm_dict["trust_tier"] == "verified"
        assert "content" not in fm_dict  # exclude_none

        restored = from_frontmatter(MedicineSchema, fm_dict)
        assert restored.name == original.name
        assert restored.dose == original.dose
        assert restored.trust_tier == original.trust_tier
        assert restored.stock == original.stock

    def test_to_frontmatter_none_excluded(self):
        """None values are excluded from the dict."""
        schema = MedicineSchema(
            name="Аэртал",
            dose="100 мг",
            frequency="редко",
            trust_tier="verified",
            date="2026-06-07",
        )
        fm = to_frontmatter(schema)
        assert "stock" not in fm
        assert "prescription_expiry" not in fm

    def test_from_frontmatter_with_content(self):
        """Content string is passed through to the schema."""
        fm_dict = {
            "name": "Тест",
            "dose": "5 мг",
            "frequency": "ежедневно",
            "trust_tier": "verified",
            "date": "2026-06-07",
        }
        body = "# Тест\n\nSome markdown content."
        restored = from_frontmatter(MedicineSchema, fm_dict, content=body)
        assert restored.content == body


# ═══════════════════════════════════════════════════════════════════
# TrustTier type guard
# ═══════════════════════════════════════════════════════════════════


class TestTrustTier:
    def test_valid_values(self):
        """All three valid tiers are accepted."""
        for tier in ("unverified", "verified", "trusted"):
            obj = CommonBase(trust_tier=tier, date="2026-06-10")
            assert obj.trust_tier == tier

    def test_invalid_values_raises(self):
        """Any value outside the literal union raises ValidationError."""
        for bad in ("super", "unknown", "gold", 123, None, ""):
            with pytest.raises(ValidationError):
                CommonBase(trust_tier=bad, date="2026-06-10")
