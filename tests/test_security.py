"""安全性测试"""

import os
import tempfile
import unittest

from src.core.security import (
    DataEncryption,
    DataSanitizer,
    InputValidator,
    PasswordManager,
    Permission,
    RBACManager,
    Role,
    SecureToken,
)


class TestInputValidator(unittest.TestCase):
    """输入验证器测试"""

    def setUp(self):
        self.validator = InputValidator()

    def test_sanitize_string(self):
        """测试字符串清理"""
        # 测试危险字符清理
        dangerous_input = "<script>alert('xss')</script>"
        sanitized = self.validator.sanitize_string(dangerous_input)
        self.assertNotIn("<", sanitized)
        self.assertNotIn(">", sanitized)

        # 测试长度限制
        long_input = "a" * 2000
        sanitized = self.validator.sanitize_string(long_input)
        self.assertEqual(len(sanitized), 1000)

    def test_validate_experiment_name(self):
        """测试实验名称验证"""
        # 有效名称
        is_valid, error = self.validator.validate_experiment_name("pH滴定实验")
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

        # 空名称
        is_valid, error = self.validator.validate_experiment_name("")
        self.assertFalse(is_valid)
        self.assertIn("不能为空", error)

        # 过短名称
        is_valid, error = self.validator.validate_experiment_name("ab")
        self.assertFalse(is_valid)
        self.assertIn("至少需要3个字符", error)

        # 过长名称
        is_valid, error = self.validator.validate_experiment_name("a" * 101)
        self.assertFalse(is_valid)
        self.assertIn("不能超过100个字符", error)

    def test_validate_numeric_input(self):
        """测试数值输入验证"""
        # 有效数值
        is_valid, error = self.validator.validate_numeric_input(25.5, 0, 100)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

        # 超出范围
        is_valid, error = self.validator.validate_numeric_input(150, 0, 100)
        self.assertFalse(is_valid)
        self.assertIn("不能大于", error)

        # 无效输入
        is_valid, error = self.validator.validate_numeric_input("abc")
        self.assertFalse(is_valid)
        self.assertIn("必须是数字", error)

    def test_validate_file_upload(self):
        """测试文件上传验证"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            # 有效文件
            is_valid, error = self.validator.validate_file_upload(temp_path)
            self.assertTrue(is_valid)
            self.assertEqual(error, "")

            # 不存在的文件
            is_valid, error = self.validator.validate_file_upload("nonexistent.txt")
            self.assertFalse(is_valid)
            self.assertIn("文件不存在", error)

        finally:
            os.unlink(temp_path)

    def test_validate_experiment_data(self):
        """测试实验数据验证"""
        # 有效数据
        valid_data = {
            "name": "测试实验",
            "description": "测试描述",
            "steps": [{"id": "step1", "text": "步骤1"}, {"id": "step2", "text": "步骤2"}],
        }

        is_valid, errors = self.validator.validate_experiment_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # 无效数据
        invalid_data = {
            "name": "ab",  # 过短
            "description": "import os",  # 包含危险关键字
            "steps": [{"id": "step1"}] * 60,  # 步骤过多
        }

        is_valid, errors = self.validator.validate_experiment_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class TestRBACManager(unittest.TestCase):
    """RBAC管理器测试"""

    def setUp(self):
        self.rbac = RBACManager()
        self.user = self.rbac.create_user(user_id="test_user", username="testuser", role=Role.STUDENT)

    def test_create_user(self):
        """测试用户创建"""
        user = self.rbac.create_user(user_id="new_user", username="newuser", role=Role.ADMIN)

        self.assertEqual(user.user_id, "new_user")
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.role, Role.ADMIN)
        self.assertIn(Permission.VIEW_EXPERIMENT, user.permissions)

    def test_has_permission(self):
        """测试权限检查"""
        # 学生有查看实验权限
        self.assertTrue(self.rbac.has_permission(self.user, Permission.VIEW_EXPERIMENT))

        # 学生没有删除实验权限
        self.assertFalse(self.rbac.has_permission(self.user, Permission.DELETE_EXPERIMENT))

    def test_add_permission(self):
        """测试添加权限"""
        # 添加权限
        result = self.rbac.add_permission(self.user, Permission.DELETE_EXPERIMENT)
        self.assertTrue(result)

        # 检查权限是否存在
        self.assertTrue(self.rbac.has_permission(self.user, Permission.DELETE_EXPERIMENT))

    def test_change_user_role(self):
        """测试更改用户角色"""
        # 更改为管理员角色
        result = self.rbac.change_user_role(self.user, Role.ADMIN)
        self.assertTrue(result)
        self.assertEqual(self.user.role, Role.ADMIN)

        # 检查权限是否更新
        self.assertTrue(self.rbac.has_permission(self.user, Permission.DELETE_EXPERIMENT))

    def test_session_management(self):
        """测试会话管理"""
        # 创建会话
        session_id = "test_session"
        result = self.rbac.create_session(self.user, session_id)
        self.assertTrue(result)

        # 获取用户
        retrieved_user = self.rbac.get_user_from_session(session_id)
        self.assertEqual(retrieved_user.user_id, self.user.user_id)

        # 移除会话
        result = self.rbac.remove_session(session_id)
        self.assertTrue(result)

        # 会话应该不存在
        retrieved_user = self.rbac.get_user_from_session(session_id)
        self.assertIsNone(retrieved_user)


class TestDataEncryption(unittest.TestCase):
    """数据加密测试"""

    def setUp(self):
        self.encryption = DataEncryption()

    def test_encrypt_decrypt_string(self):
        """测试字符串加密解密"""
        original = "敏感信息"

        # 加密
        encrypted = self.encryption.encrypt_string(original)
        self.assertNotEqual(encrypted, original)

        # 解密
        decrypted = self.encryption.decrypt_string(encrypted)
        self.assertEqual(decrypted, original)

    def test_encrypt_decrypt_dict(self):
        """测试字典加密解密"""
        original = {"key": "value", "number": 123}

        # 加密
        encrypted = self.encryption.encrypt_dict(original)
        self.assertNotEqual(encrypted, str(original))

        # 解密
        decrypted = self.encryption.decrypt_dict(encrypted)
        self.assertEqual(decrypted, original)


class TestPasswordManager(unittest.TestCase):
    """密码管理器测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password"

        # 哈希密码
        hashed, salt = PasswordManager.hash_password(password)
        self.assertNotEqual(hashed, password)
        self.assertIsNotNone(salt)

        # 验证密码
        is_valid = PasswordManager.verify_password(password, hashed, salt)
        self.assertTrue(is_valid)

        # 错误密码
        is_valid = PasswordManager.verify_password("wrong_password", hashed, salt)
        self.assertFalse(is_valid)

    def test_generate_secure_password(self):
        """测试生成安全密码"""
        password = PasswordManager.generate_secure_password(12)

        self.assertEqual(len(password), 12)
        self.assertTrue(any(c.isupper() for c in password))
        self.assertTrue(any(c.islower() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
        self.assertTrue(any(c in "!@#$%^&*" for c in password))


class TestSecureToken(unittest.TestCase):
    """安全令牌测试"""

    def setUp(self):
        self.token_manager = SecureToken()

    def test_generate_validate_token(self):
        """测试令牌生成和验证"""
        user_id = "test_user"

        # 生成令牌
        token = self.token_manager.generate_token(user_id)
        self.assertIsNotNone(token)

        # 验证令牌
        is_valid, retrieved_user_id = self.token_manager.validate_token(token)
        self.assertTrue(is_valid)
        self.assertEqual(retrieved_user_id, user_id)

    def test_revoke_token(self):
        """测试令牌撤销"""
        user_id = "test_user"
        token = self.token_manager.generate_token(user_id)

        # 撤销令牌
        result = self.token_manager.revoke_token(token)
        self.assertTrue(result)

        # 令牌应该无效
        is_valid, _ = self.token_manager.validate_token(token)
        self.assertFalse(is_valid)


class TestDataSanitizer(unittest.TestCase):
    """数据清理器测试"""

    def test_sanitize_filename(self):
        """测试文件名清理"""
        dangerous_filename = 'file<>:"|?*.txt'
        sanitized = DataSanitizer.sanitize_filename(dangerous_filename)

        self.assertNotIn("<", sanitized)
        self.assertNotIn(">", sanitized)
        self.assertNotIn(":", sanitized)
        self.assertNotIn('"', sanitized)
        self.assertNotIn("|", sanitized)
        self.assertNotIn("?", sanitized)
        self.assertNotIn("*", sanitized)

    def test_sanitize_path(self):
        """测试路径清理"""
        dangerous_path = "../../etc/passwd"
        sanitized = DataSanitizer.sanitize_path(dangerous_path)

        self.assertNotIn("..", sanitized)
        self.assertNotIn(".", sanitized)

    def test_sanitize_json(self):
        """测试JSON数据清理"""
        data = {"text": "Hello\x00World", "nested": {"value": "Test\x01Data"}}

        sanitized = DataSanitizer.sanitize_json(data)

        self.assertNotIn("\x00", sanitized["text"])
        self.assertNotIn("\x01", sanitized["nested"]["value"])


if __name__ == "__main__":
    unittest.main()
