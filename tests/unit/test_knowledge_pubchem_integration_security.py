from types import SimpleNamespace

import pytest


def test_extract_compound_data_cleans_fields_and_lengths():
    from src.knowledge.pubchem_integration import (
        MAX_FIELD_CHARS,
        MAX_SYNONYM_CHARS,
        PubChemIntegration,
    )

    integration = PubChemIntegration()

    long = "A" * (MAX_FIELD_CHARS + 100)
    long_syn = "S" * (MAX_SYNONYM_CHARS + 100)
    compound = SimpleNamespace(
        cid="123",
        iupac_name="  " + long + "\x00",
        synonyms=[" " + long_syn + "\x00", "dup", "dup"],
        molecular_formula=" C2H6O ",
        molecular_weight="46.07",
        canonical_smiles=long,
        isomeric_smiles=None,
        inchi=long,
        inchikey=long,
        xlogp="1.2",
        exact_mass=None,
        monoisotopic_mass="46.0419",
        tpsa="20.2",
        complexity="1",
        h_bond_donor_count="1",
        h_bond_acceptor_count="1",
        rotatable_bond_count="0",
        heavy_atom_count="3",
        charge="0",
    )

    data = integration._extract_compound_data(compound)

    assert isinstance(data["cid"], int)
    assert data["cid"] == 123
    assert len(data["name"]) <= MAX_FIELD_CHARS
    assert "\x00" not in data["name"]
    assert len(data["common_name"]) <= MAX_SYNONYM_CHARS
    assert data["synonyms"][0] == data["common_name"]
    assert len(data["synonyms"]) == 2  # 去重
    assert all("\x00" not in s for s in data["synonyms"])


def test_auto_fill_reagent_truncates_untrusted_data(monkeypatch):
    from src.knowledge.pubchem_integration import MAX_FIELD_CHARS, MAX_SYNONYM_CHARS, PubChemIntegration

    integration = PubChemIntegration()
    integration.available = False

    huge_name = "X" * 1000
    reagent = integration.auto_fill_reagent(huge_name)
    assert len(reagent.name) <= MAX_SYNONYM_CHARS
    assert len(reagent.description) <= MAX_FIELD_CHARS


def test_batch_update_reagents_has_upper_bound():
    from src.knowledge.pubchem_integration import MAX_BATCH_SIZE, PubChemIntegration

    integration = PubChemIntegration()
    names = [f"r{i}" for i in range(MAX_BATCH_SIZE + 1)]
    with pytest.raises(ValueError):
        integration.batch_update_reagents(names)


def test_throttle_sleeps_when_too_fast(monkeypatch):
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()
    integration.available = True
    integration._last_request_ts = 0.0

    sleeps: list[float] = []

    def fake_sleep(sec: float) -> None:
        sleeps.append(sec)

    monkeypatch.setattr("src.knowledge.pubchem_integration.time.sleep", fake_sleep)
    monkeypatch.setattr(
        "src.knowledge.pubchem_integration.time.monotonic", lambda: 0.0
    )

    integration._throttle()
    assert sleeps


def test_search_compound_and_safety_info_use_throttle(monkeypatch):
    from types import SimpleNamespace

    from src.knowledge import pubchem_integration as mod
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()
    integration.available = True

    calls = {"throttle": 0}

    def fake_throttle() -> None:
        calls["throttle"] += 1

    integration._throttle = fake_throttle  # type: ignore[method-assign]

    fake_compound = SimpleNamespace(
        cid=1,
        iupac_name="name",
        synonyms=["common"],
        molecular_formula="H2O",
        molecular_weight=18.0,
        canonical_smiles="O",
        isomeric_smiles="O",
        inchi="inchi",
        inchikey="key",
        xlogp=None,
        exact_mass=None,
        monoisotopic_mass=None,
        tpsa=None,
        complexity=None,
        h_bond_donor_count=None,
        h_bond_acceptor_count=None,
        rotatable_bond_count=None,
        heavy_atom_count=None,
        charge=None,
    )

    class FakePcp:
        @staticmethod
        def get_compounds(identifier, namespace):
            return [fake_compound]

    monkeypatch.setattr(mod, "pcp", FakePcp())

    data = integration.search_compound("water")
    assert data is not None
    assert calls["throttle"] == 1

    safety = integration.get_safety_info("water")
    assert safety["available"] is True
    assert calls["throttle"] == 2


def test_search_compound_handles_empty_result(monkeypatch):
    from src.knowledge import pubchem_integration as mod
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()
    integration.available = True

    class FakePcp:
        @staticmethod
        def get_compounds(identifier, namespace):
            return []

    monkeypatch.setattr(mod, "pcp", FakePcp())
    assert integration.search_compound("missing") is None


def test_auto_fill_reagent_updates_existing_data(monkeypatch):
    from src.knowledge.pubchem_integration import PubChemIntegration
    from src.models.knowledge import ReagentInfo

    integration = PubChemIntegration()
    integration.search_compound = lambda name: {  # type: ignore[method-assign]
        "molecular_formula": "H2O",
        "molecular_weight": 18.0,
        "canonical_smiles": "O",
        "name": "Water",
        "cid": 1,
        "common_name": "水",
    }

    existing = ReagentInfo(
        name="water",
        formula="",
        cas_number="",
        description="x",
        hazards=[],
        safety_measures=[],
    )
    updated = integration.auto_fill_reagent("water", existing_data=existing)

    assert updated.formula == "H2O"
    assert updated.molecular_weight == 18.0


def test_batch_update_reagents_success(monkeypatch):
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()
    integration.auto_fill_reagent = lambda name: name  # type: ignore[method-assign]
    results = integration.batch_update_reagents(["a", "b"])
    assert results == {"a": "a", "b": "b"}


def test_get_safety_info_unavailable_returns_available_false():
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()
    integration.available = False
    assert integration.get_safety_info("x") == {"available": False}


def test_search_compound_handles_exception(monkeypatch):
    from src.knowledge import pubchem_integration as mod
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()
    integration.available = True

    class FakePcp:
        @staticmethod
        def get_compounds(identifier, namespace):
            raise RuntimeError("boom")

    monkeypatch.setattr(mod, "pcp", FakePcp())
    assert integration.search_compound("x") is None


def test_pubchem_clean_helpers_and_safety_error_paths(monkeypatch):
    from src.knowledge import pubchem_integration as mod
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()
    assert integration._clean_float("not-a-number", default=1.5) == 1.5
    assert integration._clean_int("not-a-number", default=7) == 7
    assert integration._clean_synonyms(" single ") == ["single"]

    integration.available = True

    class FakePcpEmpty:
        @staticmethod
        def get_compounds(identifier, namespace):
            return []

    monkeypatch.setattr(mod, "pcp", FakePcpEmpty())
    assert integration.get_safety_info("missing")["available"] is False

    class FakePcpBoom:
        @staticmethod
        def get_compounds(identifier, namespace):
            raise RuntimeError("boom")

    monkeypatch.setattr(mod, "pcp", FakePcpBoom())
    assert integration.get_safety_info("x")["available"] is False


def test_auto_fill_reagent_creates_hazards_and_measures(monkeypatch):
    from src.knowledge.pubchem_integration import PubChemIntegration

    integration = PubChemIntegration()

    integration.search_compound = lambda name: {  # type: ignore[method-assign]
        "cid": 1,
        "name": "ethanol",
        "common_name": "乙醇",
        "molecular_formula": "C2H6O",
        "molecular_weight": 46.07,
        "canonical_smiles": "CCO",
        "synonyms": ["ethanol"],
    }

    reagent = integration.auto_fill_reagent("ethanol")
    assert reagent.hazards
    assert reagent.safety_measures
