"""
TemplateEngine 单元测试
测试模板引擎的加载、验证和缓存功能
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.core.template_engine import TemplateEngine, TemplateLoadError
from src.models.experiment import ExperimentTemplate


class TestTemplateEngineInitialization:
    """测试模板引擎初始化"""

    def test_init_with_existing_directory(self, tmp_path):
        """测试使用已存在目录初始化"""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        engine = TemplateEngine(templates_dir)

        assert engine.templates_dir == templates_dir
        assert engine.templates_dir.exists()

    def test_init_creates_missing_directory(self, tmp_path):
        """测试自动创建缺失目录"""
        templates_dir = tmp_path / "nonexistent" / "templates"

        engine = TemplateEngine(templates_dir)

        assert engine.templates_dir.exists()

    def test_init_with_path_string(self, tmp_path):
        """测试使用字符串路径初始化"""
        templates_dir = str(tmp_path / "templates")

        engine = TemplateEngine(Path(templates_dir))

        assert engine.templates_dir == Path(templates_dir)


class TestTemplateLoading:
    """测试模板加载功能"""

    def setup_method(self):
        """每个测试前准备"""
        self.tmp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.tmp_dir) / "templates"
        self.templates_dir.mkdir()
        self.engine = TemplateEngine(self.templates_dir)

    def create_valid_template_file(self, filename="test_exp.yaml"):
        """创建一个有效的模板文件"""
        template_data = {
            "experiment": {
                "id": "test_exp_001",
                "title": "测试实验",
                "category": "测试",
                "difficulty": "basic",
                "duration_minutes": 30,
                "description": "测试描述",
                "objectives": ["目标1"],
                "steps": [{"id": "step1", "text": "步骤1"}],
                "reagents": [{"id": "reagent1", "name": "试剂1", "amount": "10mL"}],
                "score_rules": [{"when": "all_steps_passed == True", "then": 100}],
                "goals": [],
                "curves": [],
            }
        }

        filepath = self.templates_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        return filepath

    def test_load_valid_template(self):
        """测试加载有效模板"""
        filepath = self.create_valid_template_file()

        template = self.engine.load_experiment(filepath)

        assert isinstance(template, ExperimentTemplate)
        assert template.id == "test_exp_001"
        assert template.title == "测试实验"
        assert len(template.steps) == 1
        assert len(template.reagents) == 1

    def test_load_template_caches_result(self):
        """测试模板加载后被缓存"""
        filepath = self.create_valid_template_file()

        # 第一次加载
        template1 = self.engine.load_experiment(filepath)

        # 第二次加载(应该从缓存获取)
        assert template1.id in self.engine._templates_cache
        cached_template = self.engine._templates_cache[template1.id]
        assert cached_template is template1

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        nonexistent = self.templates_dir / "nonexistent.yaml"

        with pytest.raises(TemplateLoadError, match="模板文件不存在"):
            self.engine.load_experiment(nonexistent)

    def test_load_directory_not_file(self):
        """测试加载目录而非文件"""
        dir_path = self.templates_dir / "subdir"
        dir_path.mkdir()

        with pytest.raises(TemplateLoadError, match="路径不是文件"):
            self.engine.load_experiment(dir_path)

    def test_load_empty_file(self):
        """测试加载空文件"""
        empty_file = self.templates_dir / "empty.yaml"
        empty_file.touch()

        with pytest.raises(TemplateLoadError, match="模板文件为空"):
            self.engine.load_experiment(empty_file)

    def test_load_invalid_yaml(self):
        """测试加载无效YAML"""
        invalid_file = self.templates_dir / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("{ invalid yaml content [")

        with pytest.raises(TemplateLoadError, match="YAML解析错误"):
            self.engine.load_experiment(invalid_file)

    def test_load_yaml_list_instead_of_dict(self):
        """测试YAML根节点为列表"""
        list_file = self.templates_dir / "list.yaml"
        with open(list_file, "w", encoding="utf-8") as f:
            yaml.dump([1, 2, 3], f)

        with pytest.raises(TemplateLoadError, match="模板根节点必须是字典类型"):
            self.engine.load_experiment(list_file)

    def test_load_missing_experiment_node(self):
        """测试缺少experiment节点"""
        no_exp_file = self.templates_dir / "no_exp.yaml"
        with open(no_exp_file, "w", encoding="utf-8") as f:
            yaml.dump({"other": "data"}, f)

        with pytest.raises(TemplateLoadError, match="模板缺少 'experiment' 根节点"):
            self.engine.load_experiment(no_exp_file)

    def test_load_experiment_node_not_dict(self):
        """测试experiment节点不是字典"""
        bad_exp_file = self.templates_dir / "bad_exp.yaml"
        with open(bad_exp_file, "w", encoding="utf-8") as f:
            yaml.dump({"experiment": "string"}, f)

        with pytest.raises(TemplateLoadError, match="experiment 节点必须是字典类型"):
            self.engine.load_experiment(bad_exp_file)

    def test_load_template_legacy_score_format(self):
        """测试兼容旧版score格式"""
        template_data = {
            "experiment": {
                "id": "legacy_exp",
                "title": "旧格式实验",
                "category": "测试",
                "difficulty": "basic",
                "duration_minutes": 30,
                "description": "旧格式",
                "objectives": [],
                "steps": [{"id": "s1", "text": "步骤"}],
                "reagents": [],
                "score": {"rules": [{"when": "all_steps_passed == True", "then": 100}]},
                "goals": [],
                "curves": [],
            }
        }

        legacy_file = self.templates_dir / "legacy.yaml"
        with open(legacy_file, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        template = self.engine.load_experiment(legacy_file)

        assert template.id == "legacy_exp"
        assert len(template.score_rules) == 1

    def test_load_template_with_dependency_errors(self):
        """测试加载有依赖错误的模板"""
        template_data = {
            "experiment": {
                "id": "dep_error_exp",
                "title": "依赖错误实验",
                "category": "测试",
                "difficulty": "basic",
                "duration_minutes": 30,
                "description": "依赖错误",
                "objectives": [],
                "steps": [
                    {"id": "step1", "text": "步骤1"},
                    {
                        "id": "step2",
                        "text": "步骤2",
                        "check": {
                            "type": "sequence",
                            "require": ["nonexistent_step"],  # 不存在的步骤
                            "fail_hint": "依赖失败",
                        },
                    },
                ],
                "reagents": [],
                "score_rules": [],
                "goals": [],
                "curves": [],
            }
        }

        dep_error_file = self.templates_dir / "dep_error.yaml"
        with open(dep_error_file, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        with pytest.raises(TemplateLoadError, match="依赖关系验证失败"):
            self.engine.load_experiment(dep_error_file)

    def test_load_very_large_file(self):
        """测试加载过大文件"""
        large_file = self.templates_dir / "large.yaml"
        # 创建超过10MB的文件
        with open(large_file, "wb") as f:
            f.write(b"x" * (11 * 1024 * 1024))

        with pytest.raises(TemplateLoadError, match="模板文件过大"):
            self.engine.load_experiment(large_file)


class TestTemplateLoadingById:
    """测试通过ID加载模板"""

    def setup_method(self):
        """每个测试前准备"""
        self.tmp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.tmp_dir) / "templates"
        self.templates_dir.mkdir()
        self.engine = TemplateEngine(self.templates_dir)

    def create_template_by_id(self, template_id):
        """根据ID创建模板文件"""
        template_data = {
            "experiment": {
                "id": template_id,
                "title": f"实验{template_id}",
                "category": "测试",
                "difficulty": "basic",
                "duration_minutes": 30,
                "description": "描述",
                "objectives": [],
                "steps": [{"id": "s1", "text": "步骤"}],
                "reagents": [],
                "score_rules": [],
                "goals": [],
                "curves": [],
            }
        }

        filepath = self.templates_dir / f"{template_id}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

    def test_load_by_id_success(self):
        """测试通过ID成功加载"""
        self.create_template_by_id("exp001")

        template = self.engine.load_experiment_by_id("exp001")

        assert template.id == "exp001"

    def test_load_by_id_from_cache(self):
        """测试从缓存加载"""
        self.create_template_by_id("cached_exp")

        # 第一次加载
        template1 = self.engine.load_experiment_by_id("cached_exp")

        # 第二次应该从缓存
        template2 = self.engine.load_experiment_by_id("cached_exp")

        assert template1 is template2

    def test_load_by_id_empty_string(self):
        """测试空字符串ID"""
        with pytest.raises(TemplateLoadError, match="实验ID不能为空"):
            self.engine.load_experiment_by_id("")

    def test_load_by_id_whitespace(self):
        """测试仅空白字符ID"""
        with pytest.raises(TemplateLoadError, match="实验ID不能为空"):
            self.engine.load_experiment_by_id("   ")

    def test_load_by_id_not_found(self):
        """测试找不到模板文件"""
        with pytest.raises(TemplateLoadError, match="找不到实验模板"):
            self.engine.load_experiment_by_id("nonexistent")

    def test_load_by_id_tries_yml_extension(self):
        """测试尝试.yml扩展名"""
        template_id = "yml_exp"
        template_data = {
            "experiment": {
                "id": template_id,
                "title": "YML实验",
                "category": "测试",
                "difficulty": "basic",
                "duration_minutes": 30,
                "description": "描述",
                "objectives": [],
                "steps": [{"id": "s1", "text": "步骤"}],
                "reagents": [],
                "score_rules": [],
                "goals": [],
                "curves": [],
            }
        }

        # 创建.yml文件而非.yaml
        filepath = self.templates_dir / f"{template_id}.yml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        template = self.engine.load_experiment_by_id(template_id)

        assert template.id == template_id


class TestTemplateCache:
    """测试模板缓存功能"""

    def setup_method(self):
        """每个测试前准备"""
        self.tmp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.tmp_dir) / "templates"
        self.templates_dir.mkdir()
        self.engine = TemplateEngine(self.templates_dir)

    def create_template(self, template_id):
        """创建模板文件"""
        template_data = {
            "experiment": {
                "id": template_id,
                "title": f"实验{template_id}",
                "category": "测试",
                "difficulty": "basic",
                "duration_minutes": 30,
                "description": "描述",
                "objectives": [],
                "steps": [{"id": "s1", "text": "步骤"}],
                "reagents": [],
                "score_rules": [],
                "goals": [],
                "curves": [],
            }
        }

        filepath = self.templates_dir / f"{template_id}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)
        return filepath

    def test_cache_size_limit(self):
        """测试缓存大小限制"""
        # 设置较小的缓存限制
        self.engine._max_cache_size = 3

        # 加载4个模板
        for i in range(4):
            filepath = self.create_template(f"exp_{i:03d}")
            self.engine.load_experiment(filepath)

        # 缓存应该只保留3个
        assert len(self.engine._templates_cache) == 3
        # 最早的exp_000应该被移除
        assert "exp_000" not in self.engine._templates_cache

    def test_clear_cache(self):
        """测试清空缓存"""
        # 加载一些模板
        for i in range(3):
            filepath = self.create_template(f"exp_{i:03d}")
            self.engine.load_experiment(filepath)

        assert len(self.engine._templates_cache) > 0

        self.engine.clear_cache()

        assert len(self.engine._templates_cache) == 0

    def test_cache_thread_safety(self):
        """测试缓存线程安全(基本测试)"""
        import threading

        def load_template(template_id):
            filepath = self.create_template(template_id)
            self.engine.load_experiment(filepath)

        # 创建多个线程同时加载
        threads = []
        for i in range(5):
            t = threading.Thread(target=load_template, args=(f"thread_exp_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 所有模板都应该被正确加载
        assert len(self.engine._templates_cache) == 5


class TestListAvailableExperiments:
    """测试列出可用实验"""

    def setup_method(self):
        """每个测试前准备"""
        self.tmp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.tmp_dir) / "templates"
        self.templates_dir.mkdir()
        self.engine = TemplateEngine(self.templates_dir)

    def create_template(self, template_id, level="basic"):
        """创建模板文件"""
        template_data = {
            "experiment": {
                "id": template_id,
                "title": f"实验{template_id}",
                "title_en": f"Experiment {template_id}",
                "category": "测试",
                "difficulty": level,
                "duration_minutes": 30,
                "description": "描述",
                "objectives": [],
                "steps": [{"id": "s1", "text": "步骤"}],
                "reagents": [],
                "score_rules": [],
                "goals": [],
                "curves": [],
                "version": "1.0",
            }
        }

        filepath = self.templates_dir / f"{template_id}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

    def test_list_empty_directory(self):
        """测试空目录"""
        experiments = self.engine.list_available_experiments()

        assert experiments == []

    def test_list_multiple_experiments(self):
        """测试列出多个实验"""
        self.create_template("exp001", "basic")
        self.create_template("exp002", "intermediate")
        self.create_template("exp003", "advanced")

        experiments = self.engine.list_available_experiments()

        assert len(experiments) == 3
        assert all("id" in exp for exp in experiments)
        assert all("title" in exp for exp in experiments)

    def test_list_experiments_sorted_by_level(self):
        """测试按难度排序"""
        self.create_template("exp_adv", "advanced")
        self.create_template("exp_bas", "basic")
        self.create_template("exp_int", "intermediate")

        experiments = self.engine.list_available_experiments()

        # 应该按level排序
        levels = [exp["level"] for exp in experiments]
        assert levels == sorted(levels)

    def test_list_experiments_skips_invalid_files(self):
        """测试跳过无效文件"""
        # 创建有效模板
        self.create_template("valid_exp", "basic")

        # 创建无效文件
        invalid_file = self.templates_dir / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("{ invalid }")

        experiments = self.engine.list_available_experiments()

        # 应该只返回有效的实验
        assert len(experiments) == 1
        assert experiments[0]["id"] == "valid_exp"

    def test_list_experiments_nonexistent_directory(self):
        """测试不存在的目录"""
        engine = TemplateEngine(Path("/nonexistent/path"))

        experiments = engine.list_available_experiments()

        assert experiments == []


class TestValidateTemplate:
    """测试模板验证"""

    def setup_method(self):
        """每个测试前准备"""
        self.tmp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.tmp_dir) / "templates"
        self.templates_dir.mkdir()
        self.engine = TemplateEngine(self.templates_dir)

    def create_template(self, **overrides):
        """创建模板文件,支持覆盖默认值"""
        template_data = {
            "experiment": {
                "id": "test_exp",
                "title": "测试实验",
                "category": "测试",
                "difficulty": "basic",
                "duration_minutes": 30,
                "description": "描述",
                "objectives": ["目标1"],
                "steps": [{"id": "s1", "text": "步骤"}],
                "reagents": [],
                "score_rules": [],
                "goals": [
                    {"name": "完成实验", "metric": "completion_rate", "gte": 100.0}
                ],
                "curves": [],
            }
        }

        template_data["experiment"].update(overrides)

        filepath = self.templates_dir / "test_template.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)
        return filepath

    def test_validate_valid_template(self):
        """测试验证有效模板"""
        filepath = self.create_template()

        is_valid, errors = self.engine.validate_template(filepath)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_template_no_steps(self):
        """测试无步骤的模板"""
        filepath = self.create_template(steps=[])

        is_valid, errors = self.engine.validate_template(filepath)

        assert is_valid is False
        # Pydantic会在模型层面验证,错误信息包含validation error、验证失败或"至少"等关键字
        assert any(
            "validation error" in err.lower()
            or "at least 1 item" in err
            or "验证失败" in err
            or "个错误" in err
            for err in errors
        )

    def test_validate_template_no_goals(self):
        """测试无目标的模板"""
        filepath = self.create_template(goals=[])

        is_valid, errors = self.engine.validate_template(filepath)

        # 没有goals只是警告,不是错误
        assert any("建议设置实验目标" in err for err in errors)

    def test_validate_template_titration_curve_missing_params(self):
        """测试滴定曲线缺少参数"""
        filepath = self.create_template(
            curves=[
                {
                    "id": "curve1",
                    "type": "titration_ph",
                    "params": {"acid_M": 0.1},  # 缺少acid_V_ml和base_M
                    "x_label": "体积",
                    "y_label": "pH",
                    "x_unit": "mL",
                    "y_unit": "",
                }
            ]
        )

        is_valid, errors = self.engine.validate_template(filepath)

        assert is_valid is False
        assert any("缺少参数" in err for err in errors)

    def test_validate_invalid_template_file(self):
        """测试无效模板文件"""
        invalid_file = self.templates_dir / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("{ invalid yaml }")

        is_valid, errors = self.engine.validate_template(invalid_file)

        assert is_valid is False
        assert len(errors) > 0


class TestGetTemplateInfo:
    """测试获取模板信息"""

    def setup_method(self):
        """每个测试前准备"""
        self.tmp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.tmp_dir) / "templates"
        self.templates_dir.mkdir()
        self.engine = TemplateEngine(self.templates_dir)

    def test_get_existing_template_info(self):
        """测试获取存在模板的信息"""
        template_data = {
            "experiment": {
                "id": "info_exp",
                "title": "信息实验",
                "level": "intermediate",
                "duration_min": 60,
                "category": "测试",
                "difficulty": "basic",
                "description": "描述",
                "objectives": [],
                "steps": [{"id": "s1", "text": "步骤"}],
                "reagents": [],
                "score_rules": [],
                "goals": [],
                "curves": [],
            }
        }

        filepath = self.templates_dir / "info_exp.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        info = self.engine.get_template_info("info_exp")

        assert info["id"] == "info_exp"
        assert info["title"] == "信息实验"
        assert info["level"] == "intermediate"
        assert info["duration_min"] == "60"

    def test_get_nonexistent_template_info(self):
        """测试获取不存在模板的信息"""
        info = self.engine.get_template_info("nonexistent")

        assert info == {}

    def test_get_template_info_invalid_file(self):
        """测试获取无效文件的信息"""
        invalid_file = self.templates_dir / "invalid_info.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid")

        info = self.engine.get_template_info("invalid_info")

        assert info == {}

    def test_get_template_info_no_experiment_node(self):
        """测试无experiment节点的文件"""
        no_exp_file = self.templates_dir / "no_exp_info.yaml"
        with open(no_exp_file, "w", encoding="utf-8") as f:
            yaml.dump({"other": "data"}, f)

        info = self.engine.get_template_info("no_exp_info")

        assert info == {}
