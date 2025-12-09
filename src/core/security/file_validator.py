"""文件验证和安全检查模块"""

import hashlib
from pathlib import Path
from typing import Any, Dict, List

import magic


class FileValidator:
    """文件验证器"""

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        # 文档
        '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
        # 图片
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        # 音频
        '.mp3', '.wav', '.ogg', '.flac', '.aac',
        # 视频
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        # 压缩文件
        '.zip', '.rar', '.7z', '.tar', '.gz',
        # 数据文件
        '.json', '.xml', '.csv', '.xlsx', '.xls',
        # 代码文件
        '.py', '.js', '.html', '.css', '.yaml', '.yml',
    }

    # 危险文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm',
        '.msi', '.dmg', '.pkg', '.run', '.sh',
    }

    # 允许的MIME类型
    ALLOWED_MIME_TYPES = {
        # 文档
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'application/rtf',
        'application/vnd.oasis.opendocument.text',

        # 图片
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/svg+xml',
        'image/webp',

        # 音频
        'audio/mpeg',
        'audio/wav',
        'audio/ogg',
        'audio/flac',
        'audio/aac',

        # 视频
        'video/mp4',
        'video/avi',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-flv',
        'video/webm',

        # 压缩文件
        'application/zip',
        'application/x-rar-compressed',
        'application/x-7z-compressed',
        'application/x-tar',
        'application/gzip',

        # 数据文件
        'application/json',
        'application/xml',
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',

        # 代码文件
        'text/x-python',
        'application/javascript',
        'text/html',
        'text/css',
        'application/x-yaml',
    }

    # 最大文件大小 (字节)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    def __init__(self):
        """初始化文件验证器"""
        self.magic = magic.Magic(mime=True)

    def validate_file_extension(self, file_path: str) -> bool:
        """验证文件扩展名"""
        path = Path(file_path)
        extension = path.suffix.lower()

        # 检查是否在危险扩展名列表中
        if extension in self.DANGEROUS_EXTENSIONS:
            return False

        # 检查是否在允许的扩展名列表中
        return extension in self.ALLOWED_EXTENSIONS

    def validate_file_size(self, file_path: str) -> bool:
        """验证文件大小"""
        path = Path(file_path)

        if not path.exists():
            return False

        file_size = path.stat().st_size
        return file_size <= self.MAX_FILE_SIZE

    def validate_mime_type(self, file_path: str) -> bool:
        """验证MIME类型"""
        try:
            mime_type = self.magic.from_file(file_path)
            return mime_type in self.ALLOWED_MIME_TYPES
        except Exception:
            return False

    def validate_file_content(self, file_path: str) -> bool:
        """验证文件内容"""
        try:
            path = Path(file_path)

            # 检查文件是否存在
            if not path.exists():
                return False

            # 检查文件大小
            if not self.validate_file_size(file_path):
                return False

            # 检查文件扩展名
            if not self.validate_file_extension(file_path):
                return False

            # 检查MIME类型
            if not self.validate_mime_type(file_path):
                return False

            return True

        except Exception:
            return False

    def scan_file_for_malware(self, file_path: str) -> Dict[str, Any]:
        """扫描文件恶意软件"""
        result = {
            'safe': True,
            'threats': [],
            'scan_time': None,
            'file_hash': None
        }

        try:
            # 计算文件哈希
            file_hash = self.calculate_file_hash(file_path)
            result['file_hash'] = file_hash

            # 检查文件头
            if not self.check_file_header(file_path):
                result['safe'] = False
                result['threats'].append('可疑的文件头')

            # 检查文件内容
            content_threats = self.check_file_content(file_path)
            if content_threats:
                result['safe'] = False
                result['threats'].extend(content_threats)

            return result

        except Exception as e:
            result['safe'] = False
            result['threats'].append(f'扫描错误: {str(e)}')
            return result

    def calculate_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """计算文件哈希值"""
        hash_func = hashlib.new(algorithm)

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    def check_file_header(self, file_path: str) -> bool:
        """检查文件头"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # 读取前1KB

            # 检查常见的恶意文件头
            malicious_headers = [
                b'MZ',  # PE文件
                b'\x7fELF',  # ELF文件
                b'\xca\xfe\xba\xbe',  # Java类文件
                b'PK\x03\x04',  # ZIP文件（可能是JAR）
            ]

            for malicious_header in malicious_headers:
                if header.startswith(malicious_header):
                    return False

            return True

        except Exception:
            return False

    def check_file_content(self, file_path: str) -> List[str]:
        """检查文件内容"""
        threats = []

        try:
            with open(file_path, 'rb') as f:
                content = f.read(8192)  # 读取前8KB

            # 检查可疑字符串
            suspicious_strings = [
                b'eval(',
                b'exec(',
                b'system(',
                b'shell_exec',
                b'passthru(',
                b'file_get_contents',
                b'fopen(',
                b'fwrite(',
                b'curl_exec',
                b'wget',
                b'nc -l',
                b'netcat',
                b'powershell',
                b'cmd.exe',
                b'/bin/bash',
                b'/bin/sh',
            ]

            for suspicious_string in suspicious_strings:
                if suspicious_string in content:
                    threats.append(f'发现可疑字符串: {suspicious_string.decode("utf-8", errors="ignore")}')

            return threats

        except Exception as e:
            threats.append(f'内容检查错误: {str(e)}')
            return threats

    def validate_upload(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """验证文件上传"""
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }

        try:
            path = Path(file_path)

            # 检查文件是否存在
            if not path.exists():
                result['errors'].append('文件不存在')
                return result

            # 检查文件大小
            if not self.validate_file_size(file_path):
                result['errors'].append(f'文件大小超过限制: {path.stat().st_size} > {self.MAX_FILE_SIZE}')

            # 检查文件扩展名
            if not self.validate_file_extension(original_filename):
                result['errors'].append(f'不允许的文件类型: {Path(original_filename).suffix}')

            # 检查MIME类型
            if not self.validate_mime_type(file_path):
                result['errors'].append('文件MIME类型不匹配')

            # 扫描恶意软件
            scan_result = self.scan_file_for_malware(file_path)
            if not scan_result['safe']:
                result['errors'].extend(scan_result['threats'])

            # 收集文件信息
            result['file_info'] = {
                'size': path.stat().st_size,
                'extension': path.suffix.lower(),
                'mime_type': self.magic.from_file(file_path) if path.exists() else None,
                'hash': self.calculate_file_hash(file_path),
                'name': original_filename,
            }

            # 如果没有错误，则验证通过
            if not result['errors']:
                result['valid'] = True

            return result

        except Exception as e:
            result['errors'].append(f'验证错误: {str(e)}')
            return result

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            path = Path(file_path)

            if not path.exists():
                return {'error': '文件不存在'}

            return {
                'name': path.name,
                'size': path.stat().st_size,
                'extension': path.suffix.lower(),
                'mime_type': self.magic.from_file(file_path),
                'hash': self.calculate_file_hash(file_path),
                'created': path.stat().st_ctime,
                'modified': path.stat().st_mtime,
                'is_file': path.is_file(),
                'is_dir': path.is_dir(),
            }

        except Exception as e:
            return {'error': str(e)}
