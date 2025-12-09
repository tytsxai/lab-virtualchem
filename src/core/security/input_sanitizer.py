"""输入清理和安全验证模块"""

import html
import re
from pathlib import Path
from typing import Any


class InputSanitizer:
    """输入清理器"""

    # 危险模式
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # JavaScript
        r'javascript:',  # JavaScript协议
        r'vbscript:',   # VBScript协议
        r'on\w+\s*=',   # 事件处理器
        r'<iframe[^>]*>',  # iframe
        r'<object[^>]*>',  # object
        r'<embed[^>]*>',   # embed
        r'<link[^>]*>',    # link
        r'<meta[^>]*>',    # meta
        r'<style[^>]*>',   # style
        r'expression\s*\(',  # CSS表达式
        r'url\s*\(',       # CSS URL
        r'@import',        # CSS导入
    ]

    # SQL注入模式
    SQL_INJECTION_PATTERNS = [
        r"('|(\\')|(;)|(\\;)|(--)|(\\--)|(/\*)|(\\/\*)|(\*/)|(\\\*/))",
        r"(union|select|insert|update|delete|drop|create|alter|exec|execute)",
        r"(or|and)\s+\d+\s*=\s*\d+",
        r"'\s*or\s*'\d+'\s*=\s*'\d+",
        r"'\s*and\s*'\d+'\s*=\s*'\d+",
    ]

    # 路径遍历模式
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',  # 相对路径
        r'\.\.\\',  # Windows相对路径
        r'%2e%2e%2f',  # URL编码
        r'%2e%2e%5c',  # URL编码
    ]

    def __init__(self):
        """初始化清理器"""
        self.dangerous_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]
        self.sql_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_INJECTION_PATTERNS]
        self.path_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.PATH_TRAVERSAL_PATTERNS]

    def sanitize_html(self, text: str) -> str:
        """清理HTML内容"""
        if not isinstance(text, str):
            return str(text)

        # HTML转义
        text = html.escape(text)

        # 移除危险模式
        for regex in self.dangerous_regex:
            text = regex.sub('', text)

        return text

    def sanitize_sql(self, text: str) -> str:
        """清理SQL输入"""
        if not isinstance(text, str):
            return str(text)

        # 检查SQL注入模式
        for regex in self.sql_regex:
            if regex.search(text):
                raise ValueError(f"检测到SQL注入模式: {text}")

        # 转义单引号
        text = text.replace("'", "''")

        return text

    def sanitize_path(self, path: str) -> str:
        """清理文件路径"""
        if not isinstance(path, str):
            raise ValueError("路径必须是字符串")

        # 检查路径遍历
        for regex in self.path_regex:
            if regex.search(path):
                raise ValueError(f"检测到路径遍历: {path}")

        # 规范化路径
        path_obj = Path(path)
        return str(path_obj.resolve())

    def sanitize_json(self, data: Any) -> Any:
        """清理JSON数据"""
        if isinstance(data, str):
            return self.sanitize_html(data)
        elif isinstance(data, dict):
            return {key: self.sanitize_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_json(item) for item in data]
        else:
            return data

    def validate_length(self, text: str, max_length: int = 1000) -> str:
        """验证长度"""
        if not isinstance(text, str):
            text = str(text)

        if len(text) > max_length:
            raise ValueError(f"文本长度超过限制: {len(text)} > {max_length}")

        return text

    def validate_email(self, email: str) -> str:
        """验证邮箱格式"""
        if not isinstance(email, str):
            raise ValueError("邮箱必须是字符串")

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError(f"无效的邮箱格式: {email}")

        return email.lower()

    def validate_phone(self, phone: str) -> str:
        """验证电话号码格式"""
        if not isinstance(phone, str):
            raise ValueError("电话号码必须是字符串")

        # 移除所有非数字字符
        phone = re.sub(r'[^\d]', '', phone)

        # 检查长度
        if len(phone) < 10 or len(phone) > 15:
            raise ValueError(f"无效的电话号码长度: {len(phone)}")

        return phone

    def validate_url(self, url: str) -> str:
        """验证URL格式"""
        if not isinstance(url, str):
            raise ValueError("URL必须是字符串")

        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(pattern, url):
            raise ValueError(f"无效的URL格式: {url}")

        return url

    def sanitize_user_input(self, input_data: Any, input_type: str = "text") -> Any:
        """清理用户输入"""
        if input_type == "html":
            return self.sanitize_html(str(input_data))
        elif input_type == "sql":
            return self.sanitize_sql(str(input_data))
        elif input_type == "path":
            return self.sanitize_path(str(input_data))
        elif input_type == "email":
            return self.validate_email(str(input_data))
        elif input_type == "phone":
            return self.validate_phone(str(input_data))
        elif input_type == "url":
            return self.validate_url(str(input_data))
        elif input_type == "json":
            return self.sanitize_json(input_data)
        else:
            # 默认文本清理
            text = str(input_data)
            text = self.validate_length(text)
            return self.sanitize_html(text)
