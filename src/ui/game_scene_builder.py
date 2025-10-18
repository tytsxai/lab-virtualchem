"""
游戏化场景构建器
提供预设的游戏化实验场景配置
"""

from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class GameSceneBuilder:
    """游戏化场景构建器"""

    @staticmethod
    def get_preset_scenes() -> dict[str, dict[str, Any]]:
        """获取预设场景配置"""
        return {
            "titration_game": {
                "width": 1000,
                "height": 700,
                "background_color": "#1a1a2e",
                "background_image": "lab_background.png",
                "physics_items": [
                    {
                        "id": "beaker_100ml",
                        "type": "beaker",
                        "position": [150, 500],
                        "size": [80, 100],
                        "image": "beaker.png",
                        "physics_props": {"mass": 1.0, "friction": 0.9, "bounce_factor": 0.6, "rarity": "common"},
                    },
                    {
                        "id": "erlenmeyer_flask",
                        "type": "flask",
                        "position": [400, 480],
                        "size": [90, 120],
                        "image": "flask.png",
                        "physics_props": {"mass": 1.2, "friction": 0.9, "bounce_factor": 0.7, "rarity": "uncommon"},
                    },
                    {
                        "id": "burette",
                        "type": "burette",
                        "position": [600, 300],
                        "size": [60, 200],
                        "image": "burette.png",
                        "physics_props": {"mass": 0.8, "friction": 0.95, "bounce_factor": 0.5, "rarity": "rare"},
                    },
                    {
                        "id": "reagent_hcl",
                        "type": "reagent",
                        "position": [50, 100],
                        "size": [60, 80],
                        "image": "reagent_bottle.png",
                        "physics_props": {"mass": 0.6, "friction": 0.8, "bounce_factor": 0.8, "rarity": "common"},
                    },
                    {
                        "id": "reagent_naoh",
                        "type": "reagent",
                        "position": [150, 100],
                        "size": [60, 80],
                        "image": "reagent_bottle.png",
                        "physics_props": {"mass": 0.6, "friction": 0.8, "bounce_factor": 0.8, "rarity": "common"},
                    },
                    {
                        "id": "indicator_phenolphthalein",
                        "type": "indicator",
                        "position": [250, 100],
                        "size": [40, 60],
                        "image": "indicator_bottle.png",
                        "physics_props": {"mass": 0.3, "friction": 0.7, "bounce_factor": 0.9, "rarity": "epic"},
                    },
                ],
                "interactive_zones": [
                    {
                        "id": "workbench",
                        "rect": [100, 400, 800, 200],
                        "type": "workbench",
                        "accepted_items": ["beaker", "flask", "burette"],
                        "visual_effect": "glow",
                    },
                    {
                        "id": "reagent_shelf",
                        "rect": [30, 50, 300, 150],
                        "type": "storage",
                        "accepted_items": ["reagent", "indicator"],
                        "visual_effect": "sparkle",
                    },
                ],
                "game_mechanics": {
                    "gravity_enabled": True,
                    "collision_enabled": True,
                    "physics_speed": 60,
                    "interaction_feedback": True,
                    "sound_effects": True,
                    "particle_effects": True,
                },
            },
            "synthesis_game": {
                "width": 1200,
                "height": 800,
                "background_color": "#0f1419",
                "background_image": "synthesis_lab.png",
                "physics_items": [
                    {
                        "id": "round_bottom_flask",
                        "type": "flask",
                        "position": [300, 500],
                        "size": [100, 120],
                        "image": "round_flask.png",
                        "physics_props": {"mass": 1.5, "friction": 0.9, "bounce_factor": 0.6, "rarity": "rare"},
                    },
                    {
                        "id": "condenser",
                        "type": "condenser",
                        "position": [500, 400],
                        "size": [80, 150],
                        "image": "condenser.png",
                        "physics_props": {"mass": 2.0, "friction": 0.95, "bounce_factor": 0.4, "rarity": "epic"},
                    },
                    {
                        "id": "heating_mantle",
                        "type": "heater",
                        "position": [200, 600],
                        "size": [120, 80],
                        "image": "heating_mantle.png",
                        "physics_props": {"mass": 3.0, "friction": 0.98, "bounce_factor": 0.2, "rarity": "legendary"},
                    },
                    {
                        "id": "thermometer",
                        "type": "thermometer",
                        "position": [400, 300],
                        "size": [30, 100],
                        "image": "thermometer.png",
                        "physics_props": {"mass": 0.4, "friction": 0.8, "bounce_factor": 0.7, "rarity": "uncommon"},
                    },
                    {
                        "id": "reagent_a",
                        "type": "reagent",
                        "position": [50, 200],
                        "size": [60, 80],
                        "image": "reagent_bottle.png",
                        "physics_props": {"mass": 0.6, "friction": 0.8, "bounce_factor": 0.8, "rarity": "common"},
                    },
                    {
                        "id": "reagent_b",
                        "type": "reagent",
                        "position": [150, 200],
                        "size": [60, 80],
                        "image": "reagent_bottle.png",
                        "physics_props": {"mass": 0.6, "friction": 0.8, "bounce_factor": 0.8, "rarity": "common"},
                    },
                ],
                "interactive_zones": [
                    {
                        "id": "synthesis_setup",
                        "rect": [150, 450, 600, 300],
                        "type": "workbench",
                        "accepted_items": ["flask", "condenser", "heater"],
                        "visual_effect": "glow",
                    },
                    {
                        "id": "reagent_area",
                        "rect": [30, 150, 250, 200],
                        "type": "storage",
                        "accepted_items": ["reagent"],
                        "visual_effect": "sparkle",
                    },
                ],
                "game_mechanics": {
                    "gravity_enabled": True,
                    "collision_enabled": True,
                    "physics_speed": 60,
                    "interaction_feedback": True,
                    "sound_effects": True,
                    "particle_effects": True,
                },
            },
            "crystal_growth_game": {
                "width": 900,
                "height": 600,
                "background_color": "#2d1b69",
                "background_image": "crystal_lab.png",
                "physics_items": [
                    {
                        "id": "crystal_dish",
                        "type": "dish",
                        "position": [300, 400],
                        "size": [120, 80],
                        "image": "crystal_dish.png",
                        "physics_props": {"mass": 1.0, "friction": 0.9, "bounce_factor": 0.6, "rarity": "rare"},
                    },
                    {
                        "id": "seed_crystal",
                        "type": "crystal",
                        "position": [350, 350],
                        "size": [20, 20],
                        "image": "seed_crystal.png",
                        "physics_props": {"mass": 0.1, "friction": 0.7, "bounce_factor": 0.9, "rarity": "legendary"},
                    },
                    {
                        "id": "saturated_solution",
                        "type": "solution",
                        "position": [100, 200],
                        "size": [80, 100],
                        "image": "solution_bottle.png",
                        "physics_props": {"mass": 0.8, "friction": 0.8, "bounce_factor": 0.7, "rarity": "uncommon"},
                    },
                    {
                        "id": "heating_plate",
                        "type": "heater",
                        "position": [250, 500],
                        "size": [100, 60],
                        "image": "heating_plate.png",
                        "physics_props": {"mass": 2.0, "friction": 0.98, "bounce_factor": 0.3, "rarity": "epic"},
                    },
                    {
                        "id": "thermometer_precise",
                        "type": "thermometer",
                        "position": [450, 300],
                        "size": [25, 80],
                        "image": "precise_thermometer.png",
                        "physics_props": {"mass": 0.3, "friction": 0.8, "bounce_factor": 0.7, "rarity": "rare"},
                    },
                ],
                "interactive_zones": [
                    {
                        "id": "crystal_growth_area",
                        "rect": [200, 350, 400, 200],
                        "type": "workbench",
                        "accepted_items": ["dish", "crystal", "heater"],
                        "visual_effect": "glow",
                    },
                    {
                        "id": "solution_storage",
                        "rect": [50, 150, 200, 200],
                        "type": "storage",
                        "accepted_items": ["solution"],
                        "visual_effect": "sparkle",
                    },
                ],
                "game_mechanics": {
                    "gravity_enabled": True,
                    "collision_enabled": True,
                    "physics_speed": 60,
                    "interaction_feedback": True,
                    "sound_effects": True,
                    "particle_effects": True,
                },
            },
            "electrochemistry_game": {
                "width": 1100,
                "height": 750,
                "background_color": "#1e3a8a",
                "background_image": "electrochemistry_lab.png",
                "physics_items": [
                    {
                        "id": "electrochemical_cell",
                        "type": "cell",
                        "position": [400, 450],
                        "size": [150, 100],
                        "image": "electrochemical_cell.png",
                        "physics_props": {"mass": 2.5, "friction": 0.95, "bounce_factor": 0.4, "rarity": "epic"},
                    },
                    {
                        "id": "electrode_anode",
                        "type": "electrode",
                        "position": [350, 400],
                        "size": [20, 80],
                        "image": "electrode.png",
                        "physics_props": {"mass": 0.5, "friction": 0.8, "bounce_factor": 0.6, "rarity": "rare"},
                    },
                    {
                        "id": "electrode_cathode",
                        "type": "electrode",
                        "position": [550, 400],
                        "size": [20, 80],
                        "image": "electrode.png",
                        "physics_props": {"mass": 0.5, "friction": 0.8, "bounce_factor": 0.6, "rarity": "rare"},
                    },
                    {
                        "id": "power_supply",
                        "type": "power",
                        "position": [200, 300],
                        "size": [100, 80],
                        "image": "power_supply.png",
                        "physics_props": {"mass": 1.8, "friction": 0.9, "bounce_factor": 0.5, "rarity": "legendary"},
                    },
                    {
                        "id": "electrolyte_solution",
                        "type": "solution",
                        "position": [100, 200],
                        "size": [80, 100],
                        "image": "electrolyte_bottle.png",
                        "physics_props": {"mass": 0.8, "friction": 0.8, "bounce_factor": 0.7, "rarity": "uncommon"},
                    },
                    {
                        "id": "multimeter",
                        "type": "meter",
                        "position": [600, 200],
                        "size": [80, 60],
                        "image": "multimeter.png",
                        "physics_props": {"mass": 0.7, "friction": 0.8, "bounce_factor": 0.6, "rarity": "rare"},
                    },
                ],
                "interactive_zones": [
                    {
                        "id": "electrochemistry_setup",
                        "rect": [300, 350, 500, 250],
                        "type": "workbench",
                        "accepted_items": ["cell", "electrode", "power"],
                        "visual_effect": "glow",
                    },
                    {
                        "id": "equipment_storage",
                        "rect": [50, 150, 300, 200],
                        "type": "storage",
                        "accepted_items": ["solution", "meter"],
                        "visual_effect": "sparkle",
                    },
                ],
                "game_mechanics": {
                    "gravity_enabled": True,
                    "collision_enabled": True,
                    "physics_speed": 60,
                    "interaction_feedback": True,
                    "sound_effects": True,
                    "particle_effects": True,
                },
            },
        }

    @staticmethod
    def build_scene_from_preset(preset_name: str) -> dict[str, Any]:
        """从预设构建场景配置"""
        presets = GameSceneBuilder.get_preset_scenes()

        if preset_name not in presets:
            logger.warning(f"未找到预设场景: {preset_name}, 使用默认场景")
            preset_name = "titration_game"

        return presets[preset_name]

    @staticmethod
    def create_custom_scene(
        width: int = 800,
        height: int = 600,
        background_color: str = "#1a1a2e",
        physics_items: list[dict[str, Any]] | None = None,
        interactive_zones: list[dict[str, Any]] | None = None,
        game_mechanics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建自定义场景配置"""
        physics_items = physics_items or []
        interactive_zones = interactive_zones or []
        game_mechanics = game_mechanics or {
            "gravity_enabled": True,
            "collision_enabled": True,
            "physics_speed": 60,
            "interaction_feedback": True,
            "sound_effects": True,
            "particle_effects": True,
        }

        return {
            "width": width,
            "height": height,
            "background_color": background_color,
            "physics_items": physics_items,
            "interactive_zones": interactive_zones,
            "game_mechanics": game_mechanics,
        }

    @staticmethod
    def get_scene_by_experiment_type(experiment_type: str) -> dict[str, Any]:
        """根据实验类型获取场景配置"""
        type_mapping = {
            "titration": "titration_game",
            "synthesis": "synthesis_game",
            "crystal_growth": "crystal_growth_game",
            "electrochemistry": "electrochemistry_game",
            "general": "titration_game",
        }

        preset_name = type_mapping.get(experiment_type, "titration_game")
        return GameSceneBuilder.build_scene_from_preset(preset_name)

    @staticmethod
    def validate_scene_config(config: dict[str, Any]) -> bool:
        """验证场景配置"""
        required_fields = ["width", "height", "background_color"]

        for field in required_fields:
            if field not in config:
                logger.error(f"场景配置缺少必需字段: {field}")
                return False

        # 验证物理物品配置
        for item in config.get("physics_items", []):
            required_item_fields = ["id", "type", "position"]
            for field in required_item_fields:
                if field not in item:
                    logger.error(f"物理物品配置缺少必需字段: {field}")
                    return False

        # 验证交互区域配置
        for zone in config.get("interactive_zones", []):
            required_zone_fields = ["id", "rect", "type"]
            for field in required_zone_fields:
                if field not in zone:
                    logger.error(f"交互区域配置缺少必需字段: {field}")
                    return False

        logger.info("场景配置验证通过")
        return True
