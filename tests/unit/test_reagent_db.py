"""试剂数据库单元测试"""

from pathlib import Path
from unittest.mock import Mock, patch

from src.knowledge.reagent_db import ReagentDatabase
from src.models.knowledge import Hazard, HazardLevel, KnowledgeCard, KnowledgeType


class TestReagentDatabase:
    """试剂数据库基本功能测试"""

    def setup_method(self):
        """测试前准备"""
        # Mock knowledge cards
        self.mock_hcl = KnowledgeCard(
            id="hcl",
            title="盐酸",
            type=KnowledgeType.REAGENT,
            content="盐酸是氯化氢的水溶液",
            cas="7647-01-0",
            hazards=[
                Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")
            ],
        )

        self.mock_naoh = KnowledgeCard(
            id="naoh",
            title="氢氧化钠",
            type=KnowledgeType.REAGENT,
            content="氢氧化钠是强碱",
            cas="1310-73-2",
            hazards=[
                Hazard(type="corrosive", level=HazardLevel.SEVERE, hint="强腐蚀性")
            ],
        )

        self.mock_h2so4 = KnowledgeCard(
            id="h2so4_conc",
            title="浓硫酸",
            type=KnowledgeType.REAGENT,
            content="浓硫酸具有强腐蚀性",
            cas="7664-93-9",
            hazards=[
                Hazard(
                    type="oxidizing",
                    level=HazardLevel.CRITICAL,
                    hint="强氧化性和脱水性",
                )
            ],
        )

    def test_initialization(self):
        """测试数据库初始化"""
        with patch.object(ReagentDatabase, "_load_reagents"):
            db = ReagentDatabase(Path("data/knowledge"))
            assert db._reagents == {}
            assert db.loader is not None

    def test_load_reagents(self):
        """测试加载试剂数据"""
        mock_loader = Mock()
        mock_loader.load_cards_by_type.return_value = [self.mock_hcl, self.mock_naoh]

        db = ReagentDatabase.__new__(ReagentDatabase)
        db.loader = mock_loader
        db._reagents = {}
        db._load_reagents()

        assert len(db._reagents) == 2
        assert "hcl" in db._reagents
        assert "naoh" in db._reagents
        mock_loader.load_cards_by_type.assert_called_once_with(KnowledgeType.REAGENT)

    def test_get_reagent(self):
        """测试获取试剂信息"""
        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {"hcl": self.mock_hcl}

        reagent = db.get_reagent("hcl")
        assert reagent is not None
        assert reagent.id == "hcl"
        assert reagent.title == "盐酸"

        # 不存在的试剂
        reagent = db.get_reagent("unknown")
        assert reagent is None

    def test_get_reagent_by_cas(self):
        """测试根据CAS号获取试剂"""
        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {"hcl": self.mock_hcl, "naoh": self.mock_naoh}

        # 找到试剂
        reagent = db.get_reagent_by_cas("7647-01-0")
        assert reagent is not None
        assert reagent.id == "hcl"

        # 不存在的CAS
        reagent = db.get_reagent_by_cas("0000-00-0")
        assert reagent is None

    def test_search_reagents(self):
        """测试搜索试剂"""
        mock_loader = Mock()
        mock_loader.search_cards.return_value = [self.mock_hcl]

        db = ReagentDatabase.__new__(ReagentDatabase)
        db.loader = mock_loader

        results = db.search_reagents("盐酸")
        assert len(results) == 1
        assert results[0].id == "hcl"
        mock_loader.search_cards.assert_called_once_with("盐酸", KnowledgeType.REAGENT)

    def test_get_hazardous_reagents_warning_level(self):
        """测试获取危险试剂(WARNING级别)"""
        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {
            "hcl": self.mock_hcl,  # WARNING
            "naoh": self.mock_naoh,  # SEVERE
            "h2so4_conc": self.mock_h2so4,  # CRITICAL
        }

        # 获取WARNING及以上级别
        hazardous = db.get_hazardous_reagents(HazardLevel.WARNING)
        assert len(hazardous) == 3
        # 应该按危害等级降序排列
        assert hazardous[0].id == "h2so4_conc"  # CRITICAL最高

    def test_get_hazardous_reagents_severe_level(self):
        """测试获取危险试剂(SEVERE级别)"""
        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {
            "hcl": self.mock_hcl,  # WARNING
            "naoh": self.mock_naoh,  # SEVERE
            "h2so4_conc": self.mock_h2so4,  # CRITICAL
        }

        # 获取SEVERE及以上级别
        hazardous = db.get_hazardous_reagents(HazardLevel.SEVERE)
        assert len(hazardous) == 2
        assert all(r.id in ["naoh", "h2so4_conc"] for r in hazardous)

    def test_get_hazardous_reagents_sorting(self):
        """测试危险试剂排序"""
        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {
            "hcl": self.mock_hcl,  # WARNING
            "naoh": self.mock_naoh,  # SEVERE
            "h2so4_conc": self.mock_h2so4,  # CRITICAL
        }

        hazardous = db.get_hazardous_reagents(HazardLevel.INFO)
        # 应该按CRITICAL > SEVERE > WARNING排序
        levels = [r.get_highest_hazard_level() for r in hazardous]
        assert levels[0] == HazardLevel.CRITICAL
        assert levels[1] == HazardLevel.SEVERE
        assert levels[2] == HazardLevel.WARNING

    def test_get_incompatible_pairs(self):
        """测试获取不兼容试剂对"""
        db = ReagentDatabase.__new__(ReagentDatabase)

        pairs = db.get_incompatible_pairs()
        assert isinstance(pairs, list)
        assert len(pairs) > 0
        # 验证返回的是四元组列表 (reagent1, reagent2, risk, description)
        assert all(isinstance(p, tuple) and len(p) == 4 for p in pairs)
        # 验证包含已知的不兼容对
        assert any(p[0] == "h2so4_conc" and p[1] == "h2o" for p in pairs)
        assert any(p[0] == "na" and p[1] == "h2o" for p in pairs)

    def test_reload(self):
        """测试重新加载数据"""
        mock_loader = Mock()
        mock_loader.load_cards_by_type.return_value = [self.mock_hcl]

        db = ReagentDatabase.__new__(ReagentDatabase)
        db.loader = mock_loader
        db._reagents = {"old": Mock()}

        db.reload()

        # 应该清空旧数据
        assert "old" not in db._reagents
        # 应该加载新数据
        assert "hcl" in db._reagents
        # 应该清除加载器缓存
        mock_loader.clear_cache.assert_called_once()


class TestReagentDatabaseEdgeCases:
    """边界情况和异常处理测试"""

    def test_empty_database(self):
        """测试空数据库"""
        mock_loader = Mock()
        mock_loader.load_cards_by_type.return_value = []

        db = ReagentDatabase.__new__(ReagentDatabase)
        db.loader = mock_loader
        db._reagents = {}
        db._load_reagents()

        assert len(db._reagents) == 0
        assert db.get_reagent("any") is None

    def test_get_hazardous_with_no_hazards(self):
        """测试获取危险试剂但试剂无危害信息"""
        safe_reagent = KnowledgeCard(
            id="water",
            title="水",
            type=KnowledgeType.REAGENT,
            content="纯水",
            hazards=[],
        )

        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {"water": safe_reagent}

        hazardous = db.get_hazardous_reagents(HazardLevel.WARNING)
        assert len(hazardous) == 0

    def test_search_with_empty_query(self):
        """测试空搜索关键词"""
        mock_loader = Mock()
        mock_loader.search_cards.return_value = []

        db = ReagentDatabase.__new__(ReagentDatabase)
        db.loader = mock_loader

        results = db.search_reagents("")
        assert results == []
        mock_loader.search_cards.assert_called_once_with("", KnowledgeType.REAGENT)

    def test_get_reagent_by_cas_with_multiple_matches(self):
        """测试CAS号查询(虽然CAS应该唯一,但测试第一个匹配)"""
        reagent1 = KnowledgeCard(
            id="reagent1",
            title="试剂1",
            type=KnowledgeType.REAGENT,
            content="测试",
            cas="123-45-6",
        )
        reagent2 = KnowledgeCard(
            id="reagent2",
            title="试剂2",
            type=KnowledgeType.REAGENT,
            content="测试",
            cas="123-45-6",  # 重复CAS(理论上不应该出现)
        )

        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {"reagent1": reagent1, "reagent2": reagent2}

        # 应该返回找到的第一个
        result = db.get_reagent_by_cas("123-45-6")
        assert result is not None
        assert result.id in ["reagent1", "reagent2"]

    def test_hazard_level_edge_cases(self):
        """测试危害等级边界情况"""
        info_reagent = KnowledgeCard(
            id="info",
            title="Info级",
            type=KnowledgeType.REAGENT,
            content="测试",
            hazards=[Hazard(type="info", level=HazardLevel.INFO, hint="注意")],
        )

        db = ReagentDatabase.__new__(ReagentDatabase)
        db._reagents = {"info": info_reagent}

        # INFO级别应该包含所有
        hazardous = db.get_hazardous_reagents(HazardLevel.INFO)
        assert len(hazardous) == 1

        # CRITICAL级别应该为空
        hazardous = db.get_hazardous_reagents(HazardLevel.CRITICAL)
        assert len(hazardous) == 0


class TestReagentDatabaseIntegration:
    """集成测试(使用实际数据结构)"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 准备测试数据
        reagents = [
            KnowledgeCard(
                id="hcl",
                title="盐酸",
                type=KnowledgeType.REAGENT,
                content="盐酸溶液",
                cas="7647-01-0",
                hazards=[
                    Hazard(type="corrosive", level=HazardLevel.WARNING, hint="腐蚀性")
                ],
            ),
            KnowledgeCard(
                id="naoh",
                title="氢氧化钠",
                type=KnowledgeType.REAGENT,
                content="强碱",
                cas="1310-73-2",
                hazards=[
                    Hazard(type="corrosive", level=HazardLevel.SEVERE, hint="强腐蚀")
                ],
            ),
        ]

        mock_loader = Mock()
        mock_loader.load_cards_by_type.return_value = reagents
        mock_loader.search_cards.return_value = [reagents[0]]

        # 创建数据库
        with patch(
            "src.knowledge.reagent_db.KnowledgeLoader", return_value=mock_loader
        ):
            db = ReagentDatabase(Path("data/knowledge"))

        # 测试各种操作
        assert len(db._reagents) == 2

        # 1. 通过ID获取
        reagent = db.get_reagent("hcl")
        assert reagent.title == "盐酸"

        # 2. 通过CAS获取
        reagent = db.get_reagent_by_cas("1310-73-2")
        assert reagent.id == "naoh"

        # 3. 搜索
        results = db.search_reagents("盐酸")
        assert len(results) == 1

        # 4. 获取危险试剂
        hazardous = db.get_hazardous_reagents(HazardLevel.WARNING)
        assert len(hazardous) == 2

        # 5. 重新加载
        mock_loader.load_cards_by_type.return_value = [reagents[0]]
        db.reload()
        assert len(db._reagents) == 1
