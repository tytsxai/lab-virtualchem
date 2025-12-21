from __future__ import annotations

import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType

import pytest

import src.ai.chemistry_assistant as chem_mod
from src.ai.chemistry_assistant import ChemistryAI


@pytest.fixture
def bare_ai():
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.qa_chain = None
    ai._request_timestamps = deque()
    ai._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="test_chem_ai")
    ai.MAX_INPUT_CHARS = 10
    ai.MAX_REQUESTS_PER_MINUTE = 2
    ai.REQUEST_TIMEOUT_SECONDS = 0.05
    yield ai
    ai._executor.shutdown(wait=False, cancel_futures=True)


@pytest.fixture
def fake_langchain_and_vectorstore(monkeypatch, tmp_path):
    class DummyOllama:
        def __init__(self, model: str, temperature: float = 0.0):
            self.model = model
            self.temperature = temperature

        def __call__(self, _prompt: str) -> str:
            return "ok"

        def invoke(self, _text: str) -> str:
            return "ok"

    class DummyPromptTemplate:
        def __init__(self, template: str, input_variables: list[str]):
            self.template = template
            self.input_variables = input_variables

    class DummyVectorStore:
        def __init__(self):
            self.persist_called = 0
            self.added = []

        def as_retriever(self, search_kwargs: dict):
            return {"search_kwargs": search_kwargs}

        def add_documents(self, docs):
            self.added.extend(docs)

        def persist(self):
            self.persist_called += 1

    class DummyChroma:
        def __init__(self, persist_directory: str, embedding_function):
            self.persist_directory = persist_directory
            self.embedding_function = embedding_function
            self._store = DummyVectorStore()

        def as_retriever(self, search_kwargs: dict):
            return self._store.as_retriever(search_kwargs)

        def add_documents(self, docs):
            return self._store.add_documents(docs)

        def persist(self):
            return self._store.persist()

        @classmethod
        def from_documents(cls, documents, embedding, persist_directory: str):
            inst = cls(persist_directory=persist_directory, embedding_function=embedding)
            inst.add_documents(documents)
            return inst

    class DummyEmbeddings:
        def __init__(self, model_name: str):
            self.model_name = model_name

    class DummyRetrievalQA:
        def __init__(self, llm):
            self._llm = llm

        def run(self, question: str) -> str:
            return f"qa:{question}"

        @classmethod
        def from_chain_type(cls, llm, chain_type: str, retriever, chain_type_kwargs: dict):
            return cls(llm=llm)

    monkeypatch.setattr(chem_mod, "LANGCHAIN_AVAILABLE", True)
    monkeypatch.setattr(chem_mod, "VECTORSTORE_AVAILABLE", True)
    monkeypatch.setattr(chem_mod, "Ollama", DummyOllama, raising=False)
    monkeypatch.setattr(chem_mod, "PromptTemplate", DummyPromptTemplate, raising=False)
    monkeypatch.setattr(chem_mod, "RetrievalQA", DummyRetrievalQA, raising=False)
    monkeypatch.setattr(chem_mod, "HuggingFaceEmbeddings", DummyEmbeddings, raising=False)
    monkeypatch.setattr(chem_mod, "Chroma", DummyChroma, raising=False)

    schema = ModuleType("langchain.schema")

    class Document:
        def __init__(self, page_content: str, metadata: dict):
            self.page_content = page_content
            self.metadata = metadata

    schema.Document = Document  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain.schema", schema)

    return {"tmp_path": tmp_path, "DummyChroma": DummyChroma, "DummyVectorStore": DummyVectorStore}


def test_enforce_input_limits_rejects_non_str(bare_ai):
    with pytest.raises(TypeError):
        bare_ai._enforce_input_limits(123)  # type: ignore[arg-type]


def test_rate_limit_window_slides(bare_ai, monkeypatch):
    t = 1000.0

    def _mono():
        return t

    monkeypatch.setattr("src.ai.chemistry_assistant.time.monotonic", _mono)

    bare_ai._enforce_rate_limit()
    bare_ai._enforce_rate_limit()

    t += 61.0
    bare_ai._enforce_rate_limit()


def test_rate_limit_rejects_third_request_in_window(bare_ai, monkeypatch):
    t = 1000.0

    def _mono():
        return t

    monkeypatch.setattr("src.ai.chemistry_assistant.time.monotonic", _mono)
    bare_ai._enforce_rate_limit()
    bare_ai._enforce_rate_limit()
    with pytest.raises(RuntimeError):
        bare_ai._enforce_rate_limit()


def test_call_with_timeout_raises_timeout_error(bare_ai):
    def slow(_prompt: str) -> str:
        time.sleep(0.2)
        return "late"

    bare_ai.REQUEST_TIMEOUT_SECONDS = 0.01
    with pytest.raises(TimeoutError):
        bare_ai._call_with_timeout(slow, "hi")


def test_guide_experiment_formats_prompt(bare_ai, caplog):
    captured: dict[str, str] = {}

    def llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "ok"

    bare_ai.llm = llm
    with caplog.at_level("INFO"):
        out = bare_ai.guide_experiment("酸碱滴定", "如何判断终点？")
    assert out == "ok"
    assert "实验名称: 酸碱滴定" in captured["prompt"]
    assert "学生问题: 如何判断终点？" in captured["prompt"]
    assert any("实验指导成功" in r.message for r in caplog.records)


def test_diagnose_error_includes_pretty_json(bare_ai):
    captured: dict[str, str] = {}

    def llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "ok"

    bare_ai.llm = llm
    out = bare_ai.diagnose_error({"a": 1, "b": "中文"}, "颜色异常")
    assert out == "ok"
    assert '"a": 1' in captured["prompt"]
    assert '"b": "中文"' in captured["prompt"]
    assert "颜色异常" in captured["prompt"]


def test_suggest_learning_path_uses_static_template(bare_ai):
    captured: dict[str, str] = {}

    def llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "ok"

    bare_ai.llm = llm
    out = bare_ai.suggest_learning_path("初级", ["实验1"])
    assert out == "ok"
    assert "{student_level}" in captured["prompt"]
    assert "{', '.join(completed_experiments)}" in captured["prompt"]


def test_explain_concept_uses_static_template(bare_ai):
    captured: dict[str, str] = {}

    def llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "ok"

    bare_ai.llm = llm
    out = bare_ai.explain_concept("氧化还原反应", _level="中学")
    assert out == "ok"
    assert "{level}" in captured["prompt"]
    assert "{concept}" in captured["prompt"]


def test_add_to_knowledge_base_vectorstore_unavailable_returns_false(monkeypatch):
    monkeypatch.setattr(chem_mod, "VECTORSTORE_AVAILABLE", False)
    ai = ChemistryAI.__new__(ChemistryAI)
    assert ai.add_to_knowledge_base(["doc"]) is False


def test_init_requires_langchain(monkeypatch):
    monkeypatch.setattr(chem_mod, "LANGCHAIN_AVAILABLE", False)
    with pytest.raises(ImportError):
        ChemistryAI(model_name="qwen:7b")


def test_init_model_raises_when_ollama_constructor_fails(monkeypatch):
    class Boom:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("nope")

    monkeypatch.setattr(chem_mod, "Ollama", Boom, raising=False)
    monkeypatch.setattr(chem_mod, "LANGCHAIN_AVAILABLE", True)
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.model_name = "m"
    with pytest.raises(RuntimeError):
        ai._init_model()


def test_init_knowledge_base_returns_when_vectorstore_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(chem_mod, "VECTORSTORE_AVAILABLE", False)
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.knowledge_base_path = tmp_path
    ai._init_knowledge_base()


def test_init_knowledge_base_logs_error_on_exception(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(chem_mod, "VECTORSTORE_AVAILABLE", True)

    class BoomEmbeddings:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("embeddings fail")

    monkeypatch.setattr(chem_mod, "HuggingFaceEmbeddings", BoomEmbeddings, raising=False)
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.knowledge_base_path = tmp_path
    ai.vectorstore = None
    with caplog.at_level("ERROR"):
        ai._init_knowledge_base()
    assert any("初始化知识库失败" in r.message for r in caplog.records)


def test_init_knowledge_base_creates_qa_chain_when_chroma_exists(
    fake_langchain_and_vectorstore, tmp_path
):
    kb = tmp_path / "kb"
    (kb / "chroma").mkdir(parents=True)
    ai = ChemistryAI(model_name="m", knowledge_base_path=kb)
    assert ai.qa_chain is not None
    assert ai.vectorstore is not None


def test_init_knowledge_base_without_chroma_uses_basic_mode(
    fake_langchain_and_vectorstore, tmp_path
):
    kb = tmp_path / "kb2"
    kb.mkdir(parents=True)
    ai = ChemistryAI(model_name="m", knowledge_base_path=kb)
    assert ai.vectorstore is None
    assert ai.qa_chain is None


def test_ask_uses_qa_chain_run(bare_ai):
    class DummyQA:
        def run(self, question: str) -> str:
            return f"qa:{question}"

    bare_ai.qa_chain = DummyQA()
    bare_ai.llm = lambda _prompt: "llm"
    assert bare_ai.ask("hi") == "qa:hi"


def test_ask_uses_llm_when_no_qa_chain(bare_ai):
    bare_ai.qa_chain = None
    bare_ai.llm = lambda _prompt: "llm:ok"
    assert bare_ai.ask("hi") == "llm:ok"


def test_add_to_knowledge_base_creates_new_vectorstore(fake_langchain_and_vectorstore, tmp_path):
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.vectorstore = None
    ai.knowledge_base_path = tmp_path / "kb"

    ok = ai.add_to_knowledge_base(["doc1"], metadata=[{"k": "v"}])
    assert ok is True
    assert ai.vectorstore is not None
    assert ai.knowledge_base_path.exists()


def test_add_to_knowledge_base_appends_when_vectorstore_exists(
    fake_langchain_and_vectorstore, tmp_path
):
    DummyChroma = fake_langchain_and_vectorstore["DummyChroma"]
    store = DummyChroma(persist_directory=str(tmp_path / "kb" / "chroma"), embedding_function=None)
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.vectorstore = store
    ai.knowledge_base_path = tmp_path / "kb"

    ok = ai.add_to_knowledge_base(["doc1", "doc2"])
    assert ok is True
    assert store._store.persist_called == 1


def test_add_to_knowledge_base_handles_internal_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(chem_mod, "VECTORSTORE_AVAILABLE", True)
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.vectorstore = None
    ai.knowledge_base_path = tmp_path / "kb"
    monkeypatch.delitem(sys.modules, "langchain.schema", raising=False)
    assert ai.add_to_knowledge_base(["doc"]) is False


def test_guide_experiment_error_path(bare_ai):
    def boom(_prompt: str) -> str:
        raise RuntimeError("bad")

    bare_ai.llm = boom
    out = bare_ai.guide_experiment("实验", "问题")
    assert "生成实验指导时出错" in out


def test_diagnose_error_error_path(bare_ai):
    def boom(_prompt: str) -> str:
        raise RuntimeError("bad")

    bare_ai.llm = boom
    out = bare_ai.diagnose_error({"a": 1}, "问题")
    assert "诊断错误时出错" in out


def test_suggest_learning_path_error_path(bare_ai):
    def boom(_prompt: str) -> str:
        raise RuntimeError("bad")

    bare_ai.llm = boom
    out = bare_ai.suggest_learning_path("初级", [])
    assert "生成学习建议时出错" in out


def test_explain_concept_error_path(bare_ai):
    def boom(_prompt: str) -> str:
        raise RuntimeError("bad")

    bare_ai.llm = boom
    out = bare_ai.explain_concept("概念", _level="中学")
    assert "解释概念时出错" in out


def test_quick_ask_delegates_to_ai(monkeypatch):
    class DummyAI:
        def __init__(self, model_name: str):
            self.model_name = model_name

        def ask(self, question: str) -> str:
            return f"{self.model_name}:{question}"

    monkeypatch.setattr(chem_mod, "ChemistryAI", DummyAI)
    assert chem_mod.quick_ask("hi", model="m") == "m:hi"


def test_check_ollama_available_import_error_returns_false(monkeypatch):
    original = sys.modules.pop("langchain_community.llms", None)

    try:
        if "langchain_community" in sys.modules:
            monkeypatch.delitem(sys.modules, "langchain_community", raising=False)
        assert chem_mod.check_ollama_available() is False
    finally:
        if original is not None:
            sys.modules["langchain_community.llms"] = original


def test_check_ollama_available_happy_path(monkeypatch):
    class DummyOllama:
        def __init__(self, model: str):
            self.model = model

        def invoke(self, _text: str) -> str:
            return "ok"

    llms = ModuleType("langchain_community.llms")
    llms.Ollama = DummyOllama  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_community.llms", llms)
    assert chem_mod.check_ollama_available() is True


def test_ask_error_logging_is_redacted(bare_ai, caplog):
    secret = "SECRET_INPUT_DO_NOT_LOG"

    def boom(_prompt: str) -> str:
        raise ValueError("bad")

    bare_ai.llm = boom
    with caplog.at_level("ERROR"):
        out = bare_ai.ask(secret)
    assert "处理问题时出错" in out
    combined = "\n".join(r.message for r in caplog.records)
    assert secret not in combined
    assert "sha256_16=" in combined


def test_import_branches_execute_when_deps_present(monkeypatch):
    import importlib.util
    from pathlib import Path

    module_path = Path(chem_mod.__file__)

    langchain_chains = ModuleType("langchain.chains")

    class RetrievalQA:
        pass

    langchain_chains.RetrievalQA = RetrievalQA  # type: ignore[attr-defined]

    langchain_prompts = ModuleType("langchain.prompts")

    class PromptTemplate:
        pass

    langchain_prompts.PromptTemplate = PromptTemplate  # type: ignore[attr-defined]

    llms = ModuleType("langchain_community.llms")

    class Ollama:
        pass

    llms.Ollama = Ollama  # type: ignore[attr-defined]

    embeddings = ModuleType("langchain_community.embeddings")

    class HuggingFaceEmbeddings:
        pass

    embeddings.HuggingFaceEmbeddings = HuggingFaceEmbeddings  # type: ignore[attr-defined]

    vectorstores = ModuleType("langchain_community.vectorstores")

    class Chroma:
        pass

    vectorstores.Chroma = Chroma  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "langchain", ModuleType("langchain"))
    monkeypatch.setitem(sys.modules, "langchain.chains", langchain_chains)
    monkeypatch.setitem(sys.modules, "langchain.prompts", langchain_prompts)
    monkeypatch.setitem(sys.modules, "langchain_community", ModuleType("langchain_community"))
    monkeypatch.setitem(sys.modules, "langchain_community.llms", llms)
    monkeypatch.setitem(sys.modules, "langchain_community.embeddings", embeddings)
    monkeypatch.setitem(sys.modules, "langchain_community.vectorstores", vectorstores)

    spec = importlib.util.spec_from_file_location(
        "test_dynamic_chemistry_assistant", str(module_path)
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.LANGCHAIN_AVAILABLE is True
    assert module.VECTORSTORE_AVAILABLE is True
    assert hasattr(module, "Ollama")
