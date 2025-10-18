"""
游戏交互系统测试
"""

from unittest.mock import Mock

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from src.ui.game_interaction import (
    GamePhysicsItem,
    GamePhysicsScene,
    GamePhysicsView,
    InteractionType,
    PhysicsState,
)


class TestGamePhysicsItem:
    """游戏物理物品测试"""

    def setup_method(self):
        """测试前准备"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.pixmap = QPixmap(50, 50)
        self.item = GamePhysicsItem("test_item", "test_type", self.pixmap)

    def test_item_creation(self):
        """测试物品创建"""
        assert self.item.item_id == "test_item"
        assert self.item.item_type == "test_type"
        assert self.item.mass == 1.0
        assert self.item.physics_state == PhysicsState.STATIC
        assert self.item.is_interactive is True
        assert self.item.is_draggable is True
        assert self.item.is_clickable is True
        assert self.item.rarity == "common"

    def test_physics_properties(self):
        """测试物理属性"""
        # 测试质量
        self.item.mass = 2.0
        assert self.item.mass == 2.0

        # 测试摩擦力
        self.item.friction = 0.8
        assert self.item.friction == 0.8

        # 测试弹跳系数
        self.item.bounce_factor = 0.7
        assert self.item.bounce_factor == 0.7

        # 测试重力
        self.item.gravity = QPointF(0, 1.0)
        assert self.item.gravity == QPointF(0, 1.0)

    def test_physics_state(self):
        """测试物理状态"""
        # 测试设置静态状态
        self.item.set_physics_state(PhysicsState.STATIC)
        assert self.item.physics_state == PhysicsState.STATIC

        # 测试设置移动状态
        self.item.set_physics_state(PhysicsState.MOVING)
        assert self.item.physics_state == PhysicsState.MOVING

        # 测试设置下落状态
        self.item.set_physics_state(PhysicsState.FALLING)
        assert self.item.physics_state == PhysicsState.FALLING

        # 测试设置弹跳状态
        self.item.set_physics_state(PhysicsState.BOUNCING)
        assert self.item.physics_state == PhysicsState.BOUNCING

    def test_force_application(self):
        """测试力应用"""
        # 测试施加力
        force = QPointF(10, 0)
        self.item.apply_force(force)
        assert self.item.acceleration == force / self.item.mass

        # 测试施加冲量
        impulse = QPointF(0, 10)
        self.item.apply_impulse(impulse)
        assert self.item.velocity == impulse / self.item.mass

    def test_physics_update(self):
        """测试物理更新"""
        # 设置初始状态
        self.item.set_physics_state(PhysicsState.FALLING)
        self.item.velocity = QPointF(0, 10)
        self.item.gravity = QPointF(0, 0.5)

        # 记录初始位置
        initial_pos = self.item.pos()

        # 更新物理
        self.item.update_physics(0.016)  # 60 FPS

        # 验证位置已更新
        new_pos = self.item.pos()
        assert new_pos != initial_pos

    def test_interaction_properties(self):
        """测试交互属性"""
        # 测试拖拽
        self.item.is_draggable = True
        assert self.item.is_draggable is True

        # 测试点击
        self.item.is_clickable = True
        assert self.item.is_clickable is True

        # 测试滑动
        self.item.is_swipeable = True
        assert self.item.is_swipeable is True

        # 测试交互阈值
        self.item.interaction_threshold = 15.0
        assert self.item.interaction_threshold == 15.0

    def test_rarity_properties(self):
        """测试稀有度属性"""
        # 测试稀有度
        self.item.rarity = "rare"
        assert self.item.rarity == "rare"

        # 测试发光颜色
        from PySide6.QtGui import QColor

        glow_color = QColor(255, 0, 0, 100)
        self.item.glow_color = glow_color
        assert self.item.glow_color == glow_color


class TestGamePhysicsScene:
    """游戏物理场景测试"""

    def setup_method(self):
        """测试前准备"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.scene = GamePhysicsScene()

    def test_scene_creation(self):
        """测试场景创建"""
        assert self.scene is not None
        assert isinstance(self.scene.physics_items, dict)
        assert self.scene.gravity_enabled is True
        assert self.scene.collision_enabled is True
        assert self.scene.physics_speed == 1.0

    def test_add_physics_item(self):
        """测试添加物理物品"""
        pixmap = QPixmap(50, 50)

        item = self.scene.add_physics_item("test_item", "test_type", pixmap, (100, 100), {"mass": 2.0, "friction": 0.8})

        assert item is not None
        assert item.item_id == "test_item"
        assert item.item_type == "test_type"
        assert item.mass == 2.0
        assert item.friction == 0.8
        assert "test_item" in self.scene.physics_items

    def test_physics_update(self):
        """测试物理更新"""
        # 添加一个物品
        pixmap = QPixmap(50, 50)
        item = self.scene.add_physics_item("test_item", "test_type", pixmap, (100, 100))

        # 设置物品为下落状态
        item.set_physics_state(PhysicsState.FALLING)
        item.velocity = QPointF(0, 10)

        # 记录初始位置
        initial_pos = item.pos()

        # 更新物理
        self.scene.update_physics()

        # 验证位置已更新
        new_pos = item.pos()
        assert new_pos != initial_pos

    def test_collision_detection(self):
        """测试碰撞检测"""
        # 添加两个物品
        pixmap = QPixmap(50, 50)
        item1 = self.scene.add_physics_item("item1", "type1", pixmap, (100, 100))
        item2 = self.scene.add_physics_item("item2", "type2", pixmap, (120, 100))

        # 设置碰撞半径
        item1.collision_radius = 30
        item2.collision_radius = 30

        # 检测碰撞
        self.scene._check_collisions()

        # 验证碰撞检测方法存在
        assert hasattr(self.scene, "_check_collisions")
        assert hasattr(self.scene, "_items_collide")
        assert hasattr(self.scene, "_handle_collision")

    def test_global_force(self):
        """测试全局力"""
        # 添加一个物品
        pixmap = QPixmap(50, 50)
        item = self.scene.add_physics_item("test_item", "test_type", pixmap, (100, 100))

        # 应用全局力
        force = QPointF(10, 0)
        self.scene.apply_global_force(force)

        # 验证力已应用
        assert item.acceleration == force / item.mass

    def test_gravity_control(self):
        """测试重力控制"""
        # 添加一个物品
        pixmap = QPixmap(50, 50)
        self.scene.add_physics_item("test_item", "test_type", pixmap, (100, 100))

        # 禁用重力
        self.scene.enable_gravity(False)
        assert self.scene.gravity_enabled is False

        # 启用重力
        self.scene.enable_gravity(True)
        assert self.scene.gravity_enabled is True

    def test_physics_speed(self):
        """测试物理速度"""
        # 设置物理速度
        self.scene.set_physics_speed(2.0)
        assert self.scene.physics_speed == 2.0

        # 重置物理速度
        self.scene.set_physics_speed(1.0)
        assert self.scene.physics_speed == 1.0


class TestGamePhysicsView:
    """游戏物理视图测试"""

    def setup_method(self):
        """测试前准备"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.scene = GamePhysicsScene()
        self.view = GamePhysicsView(self.scene)

    def test_view_creation(self):
        """测试视图创建"""
        assert self.view is not None
        assert self.view.scene() == self.scene

    def test_get_scene(self):
        """测试获取场景"""
        scene = self.view.get_scene()
        assert scene == self.scene
        assert isinstance(scene, GamePhysicsScene)

    def test_view_properties(self):
        """测试视图属性"""
        # 测试渲染提示
        assert self.view.renderHints() & self.view.RenderHint.Antialiasing
        assert self.view.renderHints() & self.view.RenderHint.SmoothPixmapTransform

        # 测试视口更新模式
        assert self.view.viewportUpdateMode() == self.view.FullViewportUpdate

        # 测试滚动条策略
        assert self.view.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert self.view.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


class TestInteractionTypes:
    """交互类型测试"""

    def test_interaction_type_enum(self):
        """测试交互类型枚举"""
        assert InteractionType.DRAG == "drag"
        assert InteractionType.CLICK == "click"
        assert InteractionType.SWIPE == "swipe"

    def test_physics_state_enum(self):
        """测试物理状态枚举"""
        assert PhysicsState.STATIC == "static"
        assert PhysicsState.MOVING == "moving"
        assert PhysicsState.FALLING == "falling"
        assert PhysicsState.BOUNCING == "bouncing"


class TestIntegration:
    """集成测试"""

    def setup_method(self):
        """测试前准备"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 创建场景
        scene = GamePhysicsScene()

        # 创建视图
        view = GamePhysicsView(scene)

        # 添加物品
        pixmap = QPixmap(50, 50)
        item = scene.add_physics_item("test_item", "test_type", pixmap, (100, 100))

        # 设置物品状态
        item.set_physics_state(PhysicsState.FALLING)
        item.velocity = QPointF(0, 10)

        # 更新物理
        scene.update_physics()

        # 验证工作流程
        assert item in scene.physics_items.values()
        assert view.scene() == scene
        assert item.physics_state == PhysicsState.FALLING

    def test_signal_connections(self):
        """测试信号连接"""
        scene = GamePhysicsScene()

        # 创建模拟接收器
        receiver = Mock()

        # 连接信号
        scene.physics_updated.connect(receiver.physics_updated)
        scene.collision_detected.connect(receiver.collision_detected)
        scene.item_interacted.connect(receiver.item_interacted)

        # 触发信号
        scene.physics_updated.emit()
        scene.collision_detected.emit("item1", "item2")
        scene.item_interacted.emit("item1", InteractionType.DRAG, {})

        # 验证信号已触发
        assert receiver.physics_updated.called
        assert receiver.collision_detected.called
        assert receiver.item_interacted.called
