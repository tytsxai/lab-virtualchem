"""集成测试"""

import unittest

from src.core.async_service import AsyncServiceManager
from src.core.cache_manager import CacheManager
from src.core.database_pool import DatabaseManager, DatabasePool
from src.core.experiment_controller import ExperimentController
from src.core.security import Permission, RBACManager, Role
from src.models.experiment import CheckPoint, CheckType, ExperimentTemplate, Step


class TestExperimentIntegration(unittest.TestCase):
    """实验集成测试"""

    def setUp(self):
        # 创建测试实验模板
        self.template = ExperimentTemplate(
            id="test_exp_001",
            title="集成测试实验",
            description="用于集成测试的实验",
            level="basic",
            duration_min=30,
            steps=[
                Step(
                    id="step_1",
                    text="第一步：准备试剂",
                    check=CheckPoint(
                        type=CheckType.CONFIRM, fail_hint="请确认已准备好所有试剂"
                    ),
                ),
                Step(
                    id="step_2",
                    text="第二步：开始实验",
                    check=CheckPoint(
                        type=CheckType.INPUT,
                        input={
                            "key": "volume",
                            "label": "体积",
                            "input_type": "float",
                            "range": [0, 100],
                            "unit": "mL",
                        },
                        correct_value=25.0,
                    ),
                ),
            ],
            curves=[],
            score_rules=[],
        )

        # 创建实验控制器
        self.controller = ExperimentController(
            template=self.template, user_id="test_user", enable_monitoring=False
        )

    def test_complete_experiment_flow(self):
        """测试完整实验流程"""
        # 开始实验
        self.controller.start_experiment()
        self.assertEqual(self.controller.state.value, "in_progress")

        # 提交第一步
        result = self.controller.submit_step({"confirmed": True})
        self.assertTrue(result[0])  # 应该通过
        self.controller.next_step()

        # 提交第二步
        result = self.controller.submit_step({"volume": 25.0})
        self.assertTrue(result[0])  # 应该通过

        # 完成实验
        record = self.controller.complete_experiment()
        self.assertEqual(record.status, "completed")
        self.assertGreater(record.score.total, 0)

    def test_experiment_with_errors(self):
        """测试实验错误处理"""
        # 开始实验
        self.controller.start_experiment()

        # 提交错误的第一步
        result = self.controller.submit_step({"confirmed": False})
        self.assertFalse(result[0])  # 应该失败

        # 提交正确的第一步
        result = self.controller.submit_step({"confirmed": True})
        self.assertTrue(result[0])  # 应该通过
        self.controller.next_step()

        # 提交错误的第二步
        result = self.controller.submit_step({"volume": 150.0})  # 超出范围
        self.assertFalse(result[0])  # 应该失败

        # 提交正确的第二步
        result = self.controller.submit_step({"volume": 25.0})
        self.assertTrue(result[0])  # 应该通过

        # 完成实验
        record = self.controller.complete_experiment()
        self.assertEqual(record.status, "completed")
        self.assertGreater(len(record.mistakes_summary), 0)  # 应该有错误记录

    def test_experiment_pause_resume(self):
        """测试实验暂停和恢复"""
        # 开始实验
        self.controller.start_experiment()

        # 暂停实验
        result = self.controller.pause_experiment()
        self.assertTrue(result)
        self.assertEqual(self.controller.state.value, "paused")

        # 恢复实验
        result = self.controller.resume_experiment()
        self.assertTrue(result)
        self.assertEqual(self.controller.state.value, "in_progress")

    def test_experiment_cancellation(self):
        """测试实验取消"""
        # 开始实验
        self.controller.start_experiment()

        # 取消实验
        result = self.controller.cancel_experiment("用户主动取消")
        self.assertTrue(result)
        self.assertEqual(self.controller.state.value, "cancelled")

        # 尝试提交步骤应该失败
        result = self.controller.submit_step({"confirmed": True})
        self.assertFalse(result[0])


class TestSecurityIntegration(unittest.TestCase):
    """安全性集成测试"""

    def setUp(self):
        self.rbac = RBACManager()
        self.student = self.rbac.create_user(
            user_id="student_001", username="student", role=Role.STUDENT
        )
        self.admin = self.rbac.create_user(
            user_id="admin_001", username="admin", role=Role.ADMIN
        )

    def test_permission_hierarchy(self):
        """测试权限层次"""
        # 学生权限
        self.assertTrue(
            self.rbac.has_permission(self.student, Permission.VIEW_EXPERIMENT)
        )
        self.assertFalse(
            self.rbac.has_permission(self.student, Permission.DELETE_EXPERIMENT)
        )

        # 管理员权限
        self.assertTrue(
            self.rbac.has_permission(self.admin, Permission.VIEW_EXPERIMENT)
        )
        self.assertTrue(
            self.rbac.has_permission(self.admin, Permission.DELETE_EXPERIMENT)
        )
        self.assertTrue(self.rbac.has_permission(self.admin, Permission.MANAGE_USERS))
        self.assertTrue(self.rbac.has_permission(self.admin, Permission.VIEW_LOGS))

    def test_resource_access_control(self):
        """测试资源访问控制"""
        # 学生只能查看自己的记录
        self.assertTrue(
            self.rbac.check_resource_access(
                self.student, "record", "student_001", "view"
            )
        )

        # 管理员可以查看所有记录
        self.assertTrue(
            self.rbac.check_resource_access(self.admin, "record", "student_001", "view")
        )

        # 学生不能删除实验
        self.assertFalse(
            self.rbac.check_resource_access(
                self.student, "experiment", "exp_001", "delete"
            )
        )

        # 管理员可以删除实验
        self.assertTrue(
            self.rbac.check_resource_access(
                self.admin, "experiment", "exp_001", "delete"
            )
        )

    def test_session_management(self):
        """测试会话管理"""
        # 创建会话
        session_id = "test_session"
        self.rbac.create_session(self.student, session_id)

        # 获取用户
        user = self.rbac.get_user_from_session(session_id)
        self.assertEqual(user.user_id, self.student.user_id)

        # 移除会话
        self.rbac.remove_session(session_id)

        # 会话应该不存在
        user = self.rbac.get_user_from_session(session_id)
        self.assertIsNone(user)


class TestCacheIntegration(unittest.TestCase):
    """缓存集成测试"""

    def setUp(self):
        self.cache = CacheManager(max_size=100, default_ttl=5)

    def test_cache_with_experiment_data(self):
        """测试实验数据缓存"""
        # 实验数据
        experiment_data = {
            "id": "exp_001",
            "title": "测试实验",
            "steps": [
                {"id": "step_1", "text": "步骤1"},
                {"id": "step_2", "text": "步骤2"},
            ],
        }

        # 设置缓存
        self.cache.set("experiment:exp_001", experiment_data)

        # 获取缓存
        cached_data = self.cache.get("experiment:exp_001")
        self.assertEqual(cached_data, experiment_data)

        # 更新缓存
        experiment_data["title"] = "更新的实验"
        self.cache.set("experiment:exp_001", experiment_data)

        # 验证更新
        cached_data = self.cache.get("experiment:exp_001")
        self.assertEqual(cached_data["title"], "更新的实验")

    def test_cache_with_user_data(self):
        """测试用户数据缓存"""
        # 用户数据
        user_data = {
            "user_id": "user_001",
            "username": "testuser",
            "role": "student",
            "permissions": ["view_experiment", "create_experiment"],
        }

        # 设置缓存
        self.cache.set("user:user_001", user_data)

        # 获取缓存
        cached_data = self.cache.get("user:user_001")
        self.assertEqual(cached_data, user_data)

        # 删除缓存
        self.cache.delete("user:user_001")

        # 缓存应该不存在
        cached_data = self.cache.get("user:user_001")
        self.assertIsNone(cached_data)

    def test_cache_expiration(self):
        """测试缓存过期"""
        # 设置短期缓存
        self.cache.set("temp_key", "temp_value", ttl=1)

        # 立即获取应该成功
        result = self.cache.get("temp_key")
        self.assertEqual(result, "temp_value")

        # 等待过期
        import time

        time.sleep(1.1)

        # 获取应该失败
        result = self.cache.get("temp_key")
        self.assertIsNone(result)


class TestAsyncIntegration(unittest.TestCase):
    """异步服务集成测试"""

    def setUp(self):
        self.async_manager = AsyncServiceManager(max_workers=2, max_processes=1)

    def tearDown(self):
        self.async_manager.shutdown()

    def test_async_experiment_processing(self):
        """测试异步实验处理"""

        def process_experiment(experiment_id):
            # 模拟实验处理
            import time

            time.sleep(0.1)
            return f"processed_{experiment_id}"

        # 提交多个实验处理任务
        task_ids = []
        for i in range(5):
            task_id = self.async_manager.submit_task(process_experiment, f"exp_{i}")
            task_ids.append(task_id)

        # 等待所有任务完成
        results = []
        for task_id in task_ids:
            result = self.async_manager.wait_for_task(task_id, timeout=5)
            results.append(result)

        # 验证结果
        self.assertEqual(len(results), 5)
        for i, result in enumerate(results):
            self.assertEqual(result, f"processed_exp_{i}")

    def test_async_data_processing(self):
        """测试异步数据处理"""

        def process_data(data):
            # 模拟数据处理
            return [x * 2 for x in data]

        # 提交数据处理任务
        task_id = self.async_manager.submit_task(process_data, [1, 2, 3, 4, 5])

        # 等待任务完成
        result = self.async_manager.wait_for_task(task_id, timeout=5)

        # 验证结果
        self.assertEqual(result, [2, 4, 6, 8, 10])

    def test_async_error_handling(self):
        """测试异步错误处理"""

        def error_function():
            raise ValueError("测试错误")

        # 提交错误任务
        task_id = self.async_manager.submit_task(error_function)

        # 等待任务完成
        with self.assertRaises(ValueError):
            self.async_manager.wait_for_task(task_id, timeout=5)

        # 检查任务状态
        status = self.async_manager.get_task_status(task_id)
        self.assertEqual(status["status"], "failed")
        self.assertIsNotNone(status["error"])


class TestDatabaseIntegration(unittest.TestCase):
    """数据库集成测试"""

    def setUp(self):
        # 使用内存SQLite数据库
        self.db_pool = DatabasePool(
            db_type="sqlite",
            config={"database": ":memory:"},
            min_connections=1,
            max_connections=3,
        )
        self.db_manager = DatabaseManager(self.db_pool)

        # 创建测试表
        self.db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def tearDown(self):
        self.db_pool.close_all()

    def test_experiment_crud_operations(self):
        """测试实验CRUD操作"""
        # 创建实验
        self.db_manager.execute_query(
            """
            INSERT INTO experiments (id, title, description, level)
            VALUES (?, ?, ?, ?)
        """,
            ("exp_001", "测试实验", "测试描述", "basic"),
        )

        # 读取实验
        results = self.db_manager.execute_query(
            """
            SELECT * FROM experiments WHERE id = ?
        """,
            ("exp_001",),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "测试实验")

        # 更新实验
        self.db_manager.execute_query(
            """
            UPDATE experiments SET title = ? WHERE id = ?
        """,
            ("更新的实验", "exp_001"),
        )

        # 验证更新
        results = self.db_manager.execute_query(
            """
            SELECT * FROM experiments WHERE id = ?
        """,
            ("exp_001",),
        )

        self.assertEqual(results[0]["title"], "更新的实验")

        # 删除实验
        self.db_manager.execute_query(
            """
            DELETE FROM experiments WHERE id = ?
        """,
            ("exp_001",),
        )

        # 验证删除
        results = self.db_manager.execute_query(
            """
            SELECT * FROM experiments WHERE id = ?
        """,
            ("exp_001",),
        )

        self.assertEqual(len(results), 0)

    def test_user_crud_operations(self):
        """测试用户CRUD操作"""
        # 创建用户
        self.db_manager.execute_query(
            """
            INSERT INTO users (id, username, role)
            VALUES (?, ?, ?)
        """,
            ("user_001", "testuser", "student"),
        )

        # 读取用户
        results = self.db_manager.execute_query(
            """
            SELECT * FROM users WHERE id = ?
        """,
            ("user_001",),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], "testuser")
        self.assertEqual(results[0]["role"], "student")

    def test_batch_operations(self):
        """测试批量操作"""
        # 批量插入
        queries = [
            (
                "INSERT INTO experiments (id, title, level) VALUES (?, ?, ?)",
                ("exp_001", "实验1", "basic"),
            ),
            (
                "INSERT INTO experiments (id, title, level) VALUES (?, ?, ?)",
                ("exp_002", "实验2", "intermediate"),
            ),
            (
                "INSERT INTO experiments (id, title, level) VALUES (?, ?, ?)",
                ("exp_003", "实验3", "advanced"),
            ),
        ]

        results = self.db_manager.execute_batch(queries)
        self.assertEqual(len(results), 3)

        # 验证插入
        all_experiments = self.db_manager.execute_query("SELECT * FROM experiments")
        self.assertEqual(len(all_experiments), 3)

    def test_transaction_rollback(self):
        """测试事务回滚"""
        # 开始事务
        with self.db_pool.get_connection_context() as connection_id:
            connection = self.db_pool.all_connections[connection_id]
            cursor = connection.cursor()

            try:
                # 插入数据
                cursor.execute(
                    "INSERT INTO experiments (id, title) VALUES (?, ?)",
                    ("exp_001", "测试实验"),
                )

                # 故意引发错误
                cursor.execute(
                    "INSERT INTO experiments (id, title) VALUES (?, ?)",
                    ("exp_001", "重复ID"),
                )  # 主键冲突

                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()

        # 验证数据未插入
        results = self.db_manager.execute_query(
            "SELECT * FROM experiments WHERE id = ?", ("exp_001",)
        )
        self.assertEqual(len(results), 0)


class TestFullSystemIntegration(unittest.TestCase):
    """完整系统集成测试"""

    def setUp(self):
        # 初始化所有组件
        self.rbac = RBACManager()
        self.cache = CacheManager(max_size=1000, default_ttl=300)
        self.async_manager = AsyncServiceManager(max_workers=2, max_processes=1)
        self.db_pool = DatabasePool(
            db_type="sqlite",
            config={"database": ":memory:"},
            min_connections=1,
            max_connections=3,
        )
        self.db_manager = DatabaseManager(self.db_pool)

        # 创建测试用户
        self.user = self.rbac.create_user(
            user_id="test_user", username="testuser", role=Role.STUDENT
        )

        # 创建测试表
        self.db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def tearDown(self):
        self.async_manager.shutdown()
        self.db_pool.close_all()

    def test_complete_experiment_workflow(self):
        """测试完整实验工作流"""
        # 1. 权限检查
        self.assertTrue(
            self.rbac.has_permission(self.user, Permission.CREATE_EXPERIMENT)
        )

        # 2. 创建实验数据
        experiment_data = {
            "id": "exp_001",
            "title": "完整工作流测试",
            "description": "测试完整工作流",
            "level": "basic",
        }

        # 3. 缓存实验数据
        self.cache.set(f"experiment:{experiment_data['id']}", experiment_data)

        # 4. 异步处理实验
        def process_experiment(data):
            # 模拟实验处理
            import time

            time.sleep(0.1)
            return f"processed_{data['id']}"

        task_id = self.async_manager.submit_task(process_experiment, experiment_data)
        result = self.async_manager.wait_for_task(task_id, timeout=5)

        # 5. 保存到数据库
        self.db_manager.execute_query(
            """
            INSERT INTO experiments (id, title, description, level)
            VALUES (?, ?, ?, ?)
        """,
            (
                experiment_data["id"],
                experiment_data["title"],
                experiment_data["description"],
                experiment_data["level"],
            ),
        )

        # 6. 验证结果
        self.assertEqual(result, "processed_exp_001")

        # 验证缓存
        cached_data = self.cache.get(f"experiment:{experiment_data['id']}")
        self.assertEqual(cached_data, experiment_data)

        # 验证数据库
        db_results = self.db_manager.execute_query(
            """
            SELECT * FROM experiments WHERE id = ?
        """,
            (experiment_data["id"],),
        )

        self.assertEqual(len(db_results), 1)
        self.assertEqual(db_results[0]["title"], experiment_data["title"])

    def test_error_recovery_workflow(self):
        """测试错误恢复工作流"""
        # 1. 创建实验数据
        experiment_data = {
            "id": "exp_002",
            "title": "错误恢复测试",
            "description": "测试错误恢复",
            "level": "basic",
        }

        # 2. 缓存数据
        self.cache.set(f"experiment:{experiment_data['id']}", experiment_data)

        # 3. 异步处理（模拟错误）
        def error_process(data):
            raise ValueError("处理失败")

        task_id = self.async_manager.submit_task(error_process, experiment_data)

        # 4. 处理错误
        with self.assertRaises(ValueError):
            self.async_manager.wait_for_task(task_id, timeout=5)

        # 5. 错误恢复 - 重试处理
        def retry_process(data):
            return f"retry_processed_{data['id']}"

        retry_task_id = self.async_manager.submit_task(retry_process, experiment_data)
        result = self.async_manager.wait_for_task(retry_task_id, timeout=5)

        # 6. 验证恢复结果
        self.assertEqual(result, "retry_processed_exp_002")

        # 验证缓存仍然存在
        cached_data = self.cache.get(f"experiment:{experiment_data['id']}")
        self.assertEqual(cached_data, experiment_data)


if __name__ == "__main__":
    unittest.main()
