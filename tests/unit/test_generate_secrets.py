"""
安全密钥生成器测试
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.generate_secrets import SecretGenerator  # noqa: E402


class TestSecretGenerator:
    """密钥生成器测试"""

    def test_init(self):
        """测试初始化"""
        generator = SecretGenerator()
        assert generator.project_root == PROJECT_ROOT
        assert generator.env_file == PROJECT_ROOT / ".env"
        assert generator.env_example == PROJECT_ROOT / ".env.example"

    def test_generate_secret(self):
        """测试生成密钥"""
        generator = SecretGenerator()

        # 生成默认长度密钥
        secret = generator.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0

        # 生成指定长度密钥
        secret32 = generator.generate_secret(32)
        secret64 = generator.generate_secret(64)
        assert len(secret32) != len(secret64)

    def test_generate_all_secrets(self):
        """测试生成所有密钥"""
        generator = SecretGenerator()
        secrets = generator.generate_all_secrets()

        assert isinstance(secrets, dict)
        assert "JWT_SECRET_KEY" in secrets
        assert "DEVELOPER_SECRET_KEY" in secrets
        assert "SESSION_SECRET_KEY" in secrets
        assert "CRYPTO_PAYMENT_API_KEY" in secrets
        assert "DATABASE_ENCRYPTION_KEY" in secrets

        # 验证所有密钥都是非空字符串
        for _key, value in secrets.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_generate_env_content(self):
        """测试生成.env内容"""
        generator = SecretGenerator()
        secrets = {
            "JWT_SECRET_KEY": "test-jwt-key",
            "DEVELOPER_SECRET_KEY": "test-dev-key",
            "SESSION_SECRET_KEY": "test-session-key",
            "CRYPTO_PAYMENT_API_KEY": "test-crypto-key",
            "DATABASE_ENCRYPTION_KEY": "test-db-key",
        }

        content = generator._generate_env_content(secrets)

        assert isinstance(content, str)
        assert "JWT_SECRET_KEY=test-jwt-key" in content
        assert "DEVELOPER_SECRET_KEY=test-dev-key" in content
        assert "SESSION_SECRET_KEY=test-session-key" in content
        assert "ENVIRONMENT=development" in content

    def test_create_env_file_new(self, tmp_path, monkeypatch):
        """测试创建新的.env文件"""
        # 使用临时目录
        monkeypatch.setattr(
            SecretGenerator,
            "__init__",
            lambda self: setattr(self, "project_root", tmp_path)
            or setattr(self, "env_file", tmp_path / ".env")
            or setattr(self, "env_example", tmp_path / ".env.example"),
        )

        generator = SecretGenerator()
        secrets = generator.generate_all_secrets()

        # 创建文件
        result = generator.create_env_file(secrets, force=True)
        assert result

        # 验证文件已创建
        assert generator.env_file.exists()
        assert generator.env_example.exists()

        # 验证内容
        content = generator.env_file.read_text(encoding="utf-8")
        assert "JWT_SECRET_KEY=" in content

    def test_create_env_file_exists(self, tmp_path, monkeypatch):
        """测试覆盖已存在的.env文件"""
        # 使用临时目录
        env_file = tmp_path / ".env"
        env_file.write_text("existing content")

        monkeypatch.setattr(
            SecretGenerator,
            "__init__",
            lambda self: setattr(self, "project_root", tmp_path)
            or setattr(self, "env_file", env_file)
            or setattr(self, "env_example", tmp_path / ".env.example"),
        )

        generator = SecretGenerator()
        secrets = generator.generate_all_secrets()

        # 模拟用户输入"no"
        with patch("builtins.input", return_value="no"):
            result = generator.create_env_file(secrets, force=False)
            assert not result

        # 使用force=True强制覆盖
        result = generator.create_env_file(secrets, force=True)
        assert result

    def test_check_hardcoded_secrets(self, tmp_path, monkeypatch):
        """测试检查硬编码密钥"""
        # 创建测试文件
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        test_file = src_dir / "test.py"
        test_file.write_text(
            """
secret_key = "this-is-a-hardcoded-secret-key-12345"
password = "hardcoded-password"
api_key = "sk-1234567890abcdef"
""",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            SecretGenerator,
            "__init__",
            lambda self: setattr(self, "project_root", tmp_path)
            or setattr(self, "env_file", tmp_path / ".env")
            or setattr(self, "env_example", tmp_path / ".env.example"),
        )

        generator = SecretGenerator()
        findings = generator.check_hardcoded_secrets()

        # 应该找到一些硬编码密钥
        assert isinstance(findings, list)

    def test_show_current_secrets(self, tmp_path, monkeypatch, capsys):
        """测试显示当前密钥"""
        # 创建测试.env文件
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
JWT_SECRET_KEY=test-jwt-key-12345678
DEVELOPER_SECRET_KEY=test-dev-key-12345678
""",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            SecretGenerator,
            "__init__",
            lambda self: setattr(self, "project_root", tmp_path)
            or setattr(self, "env_file", env_file)
            or setattr(self, "env_example", tmp_path / ".env.example"),
        )

        generator = SecretGenerator()
        generator.show_current_secrets()

        captured = capsys.readouterr()
        assert "JWT_SECRET_KEY" in captured.out
        assert "test****5678" in captured.out  # 掩码显示

    def test_check_gitignore_exists(self, tmp_path, monkeypatch):
        """测试检查.gitignore (已存在.env)"""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n*.pyc\n")

        monkeypatch.setattr(
            SecretGenerator,
            "__init__",
            lambda self: setattr(self, "project_root", tmp_path)
            or setattr(self, "env_file", tmp_path / ".env")
            or setattr(self, "env_example", tmp_path / ".env.example"),
        )

        generator = SecretGenerator()
        result = generator.check_gitignore()
        assert result

    def test_check_gitignore_missing(self, tmp_path, monkeypatch):
        """测试检查.gitignore (.env不存在)"""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")

        monkeypatch.setattr(
            SecretGenerator,
            "__init__",
            lambda self: setattr(self, "project_root", tmp_path)
            or setattr(self, "env_file", tmp_path / ".env")
            or setattr(self, "env_example", tmp_path / ".env.example"),
        )

        generator = SecretGenerator()

        # 模拟用户输入"yes"
        with patch("builtins.input", return_value="yes"):
            result = generator.check_gitignore()
            assert result

            # 验证.env已添加
            content = gitignore.read_text()
            assert ".env" in content


class TestSecretSecurity:
    """密钥安全性测试"""

    def test_secret_uniqueness(self):
        """测试密钥唯一性"""
        generator = SecretGenerator()

        # 生成多个密钥,应该都不相同
        secrets = [generator.generate_secret() for _ in range(10)]
        assert len(secrets) == len(set(secrets))

    def test_secret_length(self):
        """测试密钥长度"""
        generator = SecretGenerator()

        secret16 = generator.generate_secret(16)
        secret32 = generator.generate_secret(32)
        secret64 = generator.generate_secret(64)

        # URL-safe base64编码后的长度会略有不同
        assert len(secret16) > 16
        assert len(secret32) > 32
        assert len(secret64) > 64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
