"""AI化学助手模块

使用本地Ollama模型 + RAG实现智能化学问答助手:
- 完全本地运行，零成本
- 化学知识库检索增强
- 实验指导与建议
- 错误诊断与纠正
- 个性化学习路径
"""

import json
import logging
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from hashlib import sha256
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain_community.llms import Ollama

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain未安装，AI功能不可用")

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma

    VECTORSTORE_AVAILABLE = True
except ImportError:
    VECTORSTORE_AVAILABLE = False
    logger.warning("向量存储未安装，知识库功能受限")


class ChemistryAI:
    """化学AI助手"""

    MAX_INPUT_CHARS = 10_000
    MAX_REQUESTS_PER_MINUTE = 10
    REQUEST_TIMEOUT_SECONDS = 30

    # 化学专业提示模板
    CHEMISTRY_PROMPT = """你是一位专业的化学实验指导助手。请基于以下化学知识库内容回答学生的问题。

知识库内容:
{context}

学生问题: {question}

请提供:
1. 清晰的解释（适合学生理解）
2. 相关的化学原理
3. 实验操作建议（如适用）
4. 安全注意事项（如涉及危险操作）

回答:"""

    # 实验指导提示
    EXPERIMENT_PROMPT = """你是化学实验指导专家。请为学生提供详细的实验指导。

实验名称: {experiment_name}
学生问题: {question}

请提供:
1. 实验步骤说明
2. 关键操作要点
3. 可能的错误及纠正方法
4. 安全防护措施
5. 预期结果分析

指导:"""

    # 错误诊断提示
    ERROR_DIAGNOSIS_PROMPT = """你是化学实验问题诊断专家。请帮助学生分析实验中的问题。

实验情况:
{experiment_data}

观察到的问题:
{problem_description}

请分析:
1. 可能的错误原因
2. 如何验证诊断
3. 纠正措施
4. 预防类似错误的建议

诊断:"""

    def __init__(
        self, model_name: str = "qwen:7b", knowledge_base_path: Path | None = None
    ):
        """初始化AI助手

        Args:
            model_name: Ollama模型名称 (qwen:7b中文/mistral:7b英文)
            knowledge_base_path: 知识库路径
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain未安装，请运行: pip install langchain ollama")

        self.model_name = model_name
        self.knowledge_base_path = knowledge_base_path or Path("data/knowledge_base")

        # 初始化Ollama模型
        self.llm = None
        self.qa_chain = None
        self.vectorstore = None
        self._request_timestamps: deque[float] = deque()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="chem_ai")

        self._init_model()
        self._init_knowledge_base()

    def _enforce_input_limits(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("question must be a str")
        if len(text) > self.MAX_INPUT_CHARS:
            raise ValueError(
                f"输入过长（{len(text)} 字符），最大允许 {self.MAX_INPUT_CHARS} 字符"
            )

    def _enforce_rate_limit(self) -> None:
        now = time.monotonic()
        window_start = now - 60.0
        while self._request_timestamps and self._request_timestamps[0] < window_start:
            self._request_timestamps.popleft()
        if len(self._request_timestamps) >= self.MAX_REQUESTS_PER_MINUTE:
            raise RuntimeError("请求过于频繁，请稍后再试")
        self._request_timestamps.append(now)

    @staticmethod
    def _input_fingerprint(text: str) -> tuple[int, str]:
        digest = sha256(text.encode("utf-8")).hexdigest()[:16]
        return len(text), digest

    def _call_with_timeout(self, func, *args) -> str:
        future = self._executor.submit(func, *args)
        try:
            return future.result(timeout=self.REQUEST_TIMEOUT_SECONDS)
        except FutureTimeoutError as e:
            raise TimeoutError("AI请求超时") from e

    def _init_model(self):
        """初始化Ollama模型"""
        try:
            self.llm = Ollama(
                model=self.model_name,
                temperature=0.3,  # 较低温度保证答案准确性
            )
            logger.info(f"成功初始化Ollama模型: {self.model_name}")
        except Exception as e:
            logger.error(f"初始化Ollama失败: {e}")
            logger.info("请确保Ollama已安装并运行: ollama serve")
            raise

    def _init_knowledge_base(self):
        """初始化化学知识库"""
        if not VECTORSTORE_AVAILABLE:
            logger.warning("向量存储不可用，将使用基础问答模式")
            return

        try:
            # 使用本地嵌入模型
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )

            # 加载或创建向量数据库
            persist_directory = self.knowledge_base_path / "chroma"

            if persist_directory.exists():
                # 加载现有知识库
                self.vectorstore = Chroma(
                    persist_directory=str(persist_directory),
                    embedding_function=embeddings,
                )
                logger.info("成功加载化学知识库")
            else:
                logger.info("知识库不存在，将创建新的知识库")
                self.vectorstore = None

            # 创建检索问答链
            if self.vectorstore:
                prompt = PromptTemplate(
                    template=self.CHEMISTRY_PROMPT,
                    input_variables=["context", "question"],
                )

                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
                    chain_type_kwargs={"prompt": prompt},
                )
                logger.info("成功创建检索问答链")

        except Exception as e:
            logger.error(f"初始化知识库失败: {e}")

    def ask(self, question: str) -> str:
        """通用问答

        Args:
            question: 学生问题

        Returns:
            AI回答
        """
        try:
            self._enforce_input_limits(question)
            self._enforce_rate_limit()

            # 使用三元运算符简化if-else
            if self.qa_chain:
                result = self._call_with_timeout(self.qa_chain.run, question)
            else:
                result = self._call_with_timeout(self.llm, question)

            length, digest = self._input_fingerprint(question)
            logger.info(f"问答成功: input_len={length} sha256_16={digest}")
            return result

        except Exception as e:
            q = question if isinstance(question, str) else str(question)
            length, digest = self._input_fingerprint(q)
            logger.error(f"问答失败: input_len={length} sha256_16={digest} err={e}")
            return f"抱歉，处理问题时出错: {str(e)}"

    def guide_experiment(self, experiment_name: str, question: str) -> str:
        """实验指导

        Args:
            experiment_name: 实验名称
            question: 具体问题

        Returns:
            实验指导
        """
        try:
            prompt = self.EXPERIMENT_PROMPT.format(
                experiment_name=experiment_name, question=question
            )

            result = self.llm(prompt)
            logger.info(f"实验指导成功: {experiment_name}")
            return result

        except Exception as e:
            logger.error(f"实验指导失败: {e}")
            return f"抱歉，生成实验指导时出错: {str(e)}"

    def diagnose_error(
        self, experiment_data: dict[str, Any], problem_description: str
    ) -> str:
        """错误诊断

        Args:
            experiment_data: 实验数据
            problem_description: 问题描述

        Returns:
            诊断结果
        """
        try:
            # 格式化实验数据
            data_str = json.dumps(experiment_data, indent=2, ensure_ascii=False)

            prompt = self.ERROR_DIAGNOSIS_PROMPT.format(
                experiment_data=data_str, problem_description=problem_description
            )

            result = self.llm(prompt)
            logger.info("错误诊断成功")
            return result

        except Exception as e:
            logger.error(f"错误诊断失败: {e}")
            return f"抱歉，诊断错误时出错: {str(e)}"

    def suggest_learning_path(
        self, _student_level: str, _completed_experiments: list[str]
    ) -> str:
        """学习路径建议

        Args:
            student_level: 学生水平 (初级/中级/高级)
            completed_experiments: 已完成实验列表

        Returns:
            学习建议
        """
        try:
            prompt = """作为化学教学顾问，请为以下学生提供个性化学习建议:

学生水平: {student_level}
已完成实验: {', '.join(completed_experiments)}

请建议:
1. 下一步应该学习的知识点
2. 推荐的实验项目
3. 需要加强的技能
4. 学习顺序和难度安排

建议:"""

            result = self.llm(prompt)
            logger.info("学习路径建议成功")
            return result

        except Exception as e:
            logger.error(f"学习路径建议失败: {e}")
            return f"抱歉，生成学习建议时出错: {str(e)}"

    def explain_concept(self, concept: str, _level: str = "中学") -> str:
        """概念解释

        Args:
            concept: 化学概念
            level: 解释级别 (小学/中学/大学)

        Returns:
            概念解释
        """
        try:
            prompt = """请用{level}生能理解的方式解释化学概念: {concept}

要求:
1. 使用简单易懂的语言
2. 提供生活中的例子
3. 避免过于专业的术语
4. 如有必要，使用类比说明

解释:"""

            result = self.llm(prompt)
            logger.info(f"概念解释成功: {concept}")
            return result

        except Exception as e:
            logger.error(f"概念解释失败: {e}")
            return f"抱歉，解释概念时出错: {str(e)}"

    def add_to_knowledge_base(
        self, documents: list[str], metadata: list[dict] | None = None
    ) -> bool:
        """添加文档到知识库

        Args:
            documents: 文档内容列表
            metadata: 文档元数据列表

        Returns:
            是否成功添加
        """
        if not VECTORSTORE_AVAILABLE:
            logger.error("向量存储不可用")
            return False

        try:
            from langchain.schema import Document

            # 创建Document对象
            docs = []
            for i, text in enumerate(documents):
                meta = metadata[i] if metadata and i < len(metadata) else {}
                docs.append(Document(page_content=text, metadata=meta))

            # 添加到向量数据库
            if self.vectorstore is None:
                # 创建新的向量数据库
                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                )

                persist_directory = self.knowledge_base_path / "chroma"
                persist_directory.parent.mkdir(parents=True, exist_ok=True)

                self.vectorstore = Chroma.from_documents(
                    documents=docs,
                    embedding=embeddings,
                    persist_directory=str(persist_directory),
                )
            else:
                # 添加到现有数据库
                self.vectorstore.add_documents(docs)

            # 持久化
            self.vectorstore.persist()

            logger.info(f"成功添加 {len(documents)} 个文档到知识库")
            return True

        except Exception as e:
            logger.error(f"添加知识库失败: {e}")
            return False


# 便捷函数
def quick_ask(question: str, model: str = "qwen:7b") -> str:
    """快速问答

    Args:
        question: 问题
        model: 模型名称

    Returns:
        回答
    """
    ai = ChemistryAI(model_name=model)
    return ai.ask(question)


def check_ollama_available() -> bool:
    """检查Ollama是否可用"""
    try:
        from langchain_community.llms import Ollama

        llm = Ollama(model="qwen:7b")
        # 调用llm作为函数
        _ = llm.invoke("test")
        return True
    except Exception:
        return False


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 检查Ollama
    if not check_ollama_available():
        logger.info("❌ Ollama未运行或未安装")
        logger.info("\n请先安装Ollama:")
        logger.info("  Windows: https://ollama.ai/download/windows")
        logger.info("  Linux/Mac: curl -fsSL https://ollama.ai/install.sh | sh")
        logger.info("\n然后拉取中文模型:")
        logger.info("  ollama pull qwen:7b")
        sys.exit(1)

    logger.info("✅ Ollama运行正常\n")

    # 创建AI助手
    logger.info("初始化AI助手...")
    ai = ChemistryAI(model_name="qwen:7b")

    # 测试问答
    print("\n" + "=" * 60)
    logger.info("测试1: 化学问答")
    print("=" * 60)
    question = "如何配制0.1M的氯化钠溶液?"
    logger.info(f"\n问题: {question}")
    answer = ai.ask(question)
    logger.info(f"\n回答:\n{answer}")

    # 测试实验指导
    print("\n" + "=" * 60)
    logger.info("测试2: 实验指导")
    print("=" * 60)
    guidance = ai.guide_experiment(
        experiment_name="酸碱滴定", question="滴定时如何准确判断终点?"
    )
    logger.info(f"\n指导:\n{guidance}")

    # 测试概念解释
    print("\n" + "=" * 60)
    logger.info("测试3: 概念解释")
    print("=" * 60)
    explanation = ai.explain_concept("氧化还原反应", level="中学")
    logger.info(f"\n解释:\n{explanation}")

