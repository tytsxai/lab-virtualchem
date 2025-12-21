"""知识库加载器"""

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.models.knowledge import KnowledgeCard, KnowledgeType

logger = logging.getLogger(__name__)

MAX_KNOWLEDGE_FILE_BYTES = 256 * 1024  # 256 KiB
TRUSTED_KNOWLEDGE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "assets" / "knowledge"
)


class KnowledgeLoader:
    """知识库加载器"""

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        """初始化加载器

        Args:
            knowledge_dir: 知识库目录（忽略外部输入，固定使用受信任目录）
        """
        if knowledge_dir is not None:
            logger.warning("KnowledgeLoader 已固定使用受信任目录，忽略外部 knowledge_dir 参数")

        self.knowledge_dir = TRUSTED_KNOWLEDGE_DIR
        self._cards_cache: dict[str, KnowledgeCard] = {}

    def _validate_card_path(self, card_path: Path) -> Path:
        knowledge_dir_resolved = self.knowledge_dir.resolve(strict=False)
        card_path = Path(card_path)

        if card_path.is_symlink():
            raise ValueError("拒绝符号链接文件")

        card_path_resolved = card_path.resolve(strict=True)
        knowledge_dir_resolved = knowledge_dir_resolved.resolve(strict=True)

        try:
            card_path_resolved.relative_to(knowledge_dir_resolved)
        except ValueError as e:
            raise ValueError("card_path 必须位于 knowledge_dir 内") from e

        for parent in card_path_resolved.parents:
            if parent == knowledge_dir_resolved:
                break
            if parent.is_symlink():
                raise ValueError("拒绝路径中的符号链接目录")

        return card_path_resolved

    def _validate_file_size(self, file_path: Path) -> None:
        size = file_path.stat().st_size
        if size > MAX_KNOWLEDGE_FILE_BYTES:
            raise ValueError(
                f"知识文件过大: {size} bytes (max {MAX_KNOWLEDGE_FILE_BYTES})"
            )

    def load_card(self, card_path: Path) -> KnowledgeCard | None:
        """加载知识卡片

        Args:
            card_path: 卡片文件路径

        Returns:
            知识卡片对象或None
        """
        try:
            validated_path = self._validate_card_path(card_path)
            self._validate_file_size(validated_path)

            with open(validated_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"知识卡片文件为空: {validated_path}")
                return None

            card = KnowledgeCard(**data)
            self._cards_cache[card.id] = card

            logger.info(f"成功加载知识卡片: {card.id} - {card.title}")
            return card

        except FileNotFoundError:
            logger.error(f"知识卡片文件不存在: {card_path}")
        except yaml.YAMLError as e:
            logger.error(f"YAML解析错误 {card_path}: {e}")
        except ValidationError as e:
            logger.error(f"知识卡片验证失败 {card_path}: {e}")
        except ValueError as e:
            logger.error(f"拒绝加载知识卡片 {card_path}: {e}")
        except Exception as e:
            logger.error(f"加载知识卡片失败 {card_path}: {e}")

        return None

    def load_cards_by_type(self, card_type: KnowledgeType) -> list[KnowledgeCard]:
        """根据类型加载知识卡片

        Args:
            card_type: 卡片类型

        Returns:
            知识卡片列表
        """
        cards = []
        type_dir = self.knowledge_dir / card_type.value

        if not type_dir.exists():
            logger.warning(f"知识库目录不存在: {type_dir}")
            return cards

        if type_dir.is_symlink():
            logger.error(f"拒绝符号链接知识目录: {type_dir}")
            return cards

        for card_file in type_dir.glob("*.yaml"):
            card = self.load_card(card_file)
            if card and card.type == card_type:
                cards.append(card)

        return cards

    def get_card_by_id(self, card_id: str) -> KnowledgeCard | None:
        """根据ID获取知识卡片

        Args:
            card_id: 卡片ID

        Returns:
            知识卡片或None
        """
        # 先查缓存
        if card_id in self._cards_cache:
            return self._cards_cache[card_id]

        # 遍历所有类型目录查找
        for card_type in KnowledgeType:
            type_dir = self.knowledge_dir / card_type.value
            if not type_dir.exists():
                continue

            card_file = type_dir / f"{card_id}.yaml"
            if card_file.exists():
                return self.load_card(card_file)

        logger.warning(f"找不到知识卡片: {card_id}")
        return None

    def search_cards(
        self, query: str, card_type: KnowledgeType | None = None
    ) -> list[KnowledgeCard]:
        """搜索知识卡片

        Args:
            query: 搜索关键词
            card_type: 卡片类型(可选)

        Returns:
            匹配的知识卡片列表
        """
        results = []
        query_lower = query.lower()

        # 确定搜索范围
        types_to_search = [card_type] if card_type else list(KnowledgeType)

        for ctype in types_to_search:
            cards = self.load_cards_by_type(ctype)
            for card in cards:
                # 搜索标题、内容、标签
                if (
                    query_lower in card.title.lower()
                    or query_lower in card.content.lower()
                    or any(query_lower in tag.lower() for tag in card.tags)
                ):
                    results.append(card)

        return results

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cards_cache.clear()
        logger.info("知识库缓存已清空")
