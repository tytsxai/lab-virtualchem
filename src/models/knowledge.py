"""知识库数据模型"""

from enum import Enum

from pydantic import BaseModel, Field


class KnowledgeType(str, Enum):
    """知识卡片类型"""

    REAGENT = "reagent"  # 试剂
    APPARATUS = "apparatus"  # 器皿/装置
    PROCEDURE = "procedure"  # 操作规程
    FAQ = "faq"  # 常见问题


class HazardLevel(str, Enum):
    """危害等级"""

    INFO = "info"  # 信息提示
    WARNING = "warning"  # 警告
    SEVERE = "severe"  # 严重
    CRITICAL = "critical"  # 致命


class Hazard(BaseModel):
    """危害信息"""

    type: str = Field(..., description="危害类型: corrosive/toxic/flammable/reactive/...")
    level: HazardLevel = Field(..., description="危害等级")
    hint: str = Field(..., description="安全提示")
    emergency: str | None = Field(default=None, description="应急处理")


class PhysicalProperties(BaseModel):
    """物理性质"""

    density: float | None = Field(default=None, description="密度(g/cm³)")
    boiling_point: float | None = Field(default=None, description="沸点(°C)")
    melting_point: float | None = Field(default=None, description="熔点(°C)")
    molecular_weight: float | None = Field(default=None, description="分子量(g/mol)")
    solubility: str | None = Field(default=None, description="溶解性描述")
    appearance: str | None = Field(default=None, description="外观")


class KnowledgeCard(BaseModel):
    """知识卡片"""

    id: str = Field(..., description="唯一标识符")
    type: KnowledgeType = Field(..., description="卡片类型")
    title: str = Field(..., description="标题")
    title_en: str | None = Field(default=None, description="英文标题")
    content: str = Field(..., description="内容(Markdown格式)")
    cas: str | None = Field(default=None, description="CAS号(用于试剂)")
    formula: str | None = Field(default=None, description="化学式")
    properties: PhysicalProperties | None = Field(default=None, description="物理性质")
    hazards: list[Hazard] = Field(default_factory=list, description="危害列表")
    images: list[str] = Field(default_factory=list, description="图片路径列表")
    videos: list[str] = Field(default_factory=list, description="视频路径列表")
    references: list[str] = Field(default_factory=list, description="参考资料")
    tags: list[str] = Field(default_factory=list, description="标签")
    version: str = Field(default="1.0.0", description="版本号")
    author: str | None = Field(default=None, description="作者/审校人")
    metadata: dict[str, str] = Field(default_factory=dict, description="元数据")

    def get_highest_hazard_level(self) -> HazardLevel | None:
        """获取最高危害等级"""
        if not self.hazards:
            return None

        level_priority = {
            HazardLevel.CRITICAL: 4,
            HazardLevel.SEVERE: 3,
            HazardLevel.WARNING: 2,
            HazardLevel.INFO: 1,
        }

        max_level = max(self.hazards, key=lambda h: level_priority[h.level])
        return max_level.level

    def has_hazard_type(self, hazard_type: str) -> bool:
        """检查是否包含特定类型的危害"""
        return any(h.type == hazard_type for h in self.hazards)
