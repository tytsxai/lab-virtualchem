"""
许可证备份和恢复工具

用于备份、导出、导入许可证
"""

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.license_manager import LicenseManager, get_machine_id  # noqa: E402


def _resolve_license_secret() -> str:
    """从环境变量读取许可证密钥，避免硬编码"""
    secret = os.getenv("LICENSE_SECRET_KEY", "").strip()
    if not secret:
        raise ValueError("未设置 LICENSE_SECRET_KEY，禁止使用默认/硬编码密钥")
    if secret.startswith("YOUR_") or len(secret) < 32:
        raise ValueError("LICENSE_SECRET_KEY 长度不足或仍为占位值，请提供>=32位的生产密钥")
    return secret


class LicenseBackupTool:
    """许可证备份工具"""

    def __init__(self, license_manager: LicenseManager):
        self.license_manager = license_manager

    def backup_license(self, output_file: Path, include_machine_info: bool = True):
        """备份许可证

        Args:
            output_file: 输出文件路径
            include_machine_info: 是否包含机器信息
        """
        license_obj = self.license_manager.load_license()

        if not license_obj:
            print("❌ 未找到许可证")
            return False

        # 创建备份数据
        backup_data = {
            'version': '1.0',
            'backup_time': datetime.now().isoformat(),
            'license': license_obj.to_dict()
        }

        if include_machine_info:
            backup_data['machine_id'] = get_machine_id()

        # 保存备份
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 许可证已备份到: {output_file}")
            return True

        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return False

    def restore_license(self, backup_file: Path, verify_machine: bool = True):
        """恢复许可证

        Args:
            backup_file: 备份文件路径
            verify_machine: 是否验证机器ID
        """
        try:
            with open(backup_file, encoding='utf-8') as f:
                backup_data = json.load(f)

            # 验证备份格式
            if 'version' not in backup_data or 'license' not in backup_data:
                print("❌ 无效的备份文件格式")
                return False

            # 验证机器ID
            if verify_machine and 'machine_id' in backup_data:
                current_machine_id = get_machine_id()
                backup_machine_id = backup_data['machine_id']

                if current_machine_id != backup_machine_id:
                    print("⚠️ 警告: 机器ID不匹配")
                    print(f"  当前: {current_machine_id}")
                    print(f"  备份: {backup_machine_id}")

                    confirm = input("是否继续恢复? (y/n): ").strip().lower()
                    if confirm != 'y':
                        print("❌ 恢复已取消")
                        return False

            # 恢复许可证
            from src.core.license_manager import License
            license_obj = License.from_dict(backup_data['license'])

            if self.license_manager.save_license(license_obj):
                print("✅ 许可证已恢复")
                print(f"备份时间: {backup_data['backup_time']}")
                return True
            else:
                print("❌ 恢复失败")
                return False

        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            return False

    def export_license_package(self, output_zip: Path):
        """导出许可证包 (包含所有相关文件)

        Args:
            output_zip: 输出ZIP文件路径
        """
        license_obj = self.license_manager.load_license()

        if not license_obj:
            print("❌ 未找到许可证")
            return False

        try:
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 添加许可证文件
                if self.license_manager.license_file.exists():
                    zf.write(
                        self.license_manager.license_file,
                        arcname='license.json'
                    )

                # 添加机器信息
                machine_info = {
                    'machine_id': get_machine_id(),
                    'export_time': datetime.now().isoformat()
                }
                zf.writestr('machine_info.json', json.dumps(machine_info, indent=2))

                # 添加许可证信息摘要
                info = self.license_manager.get_license_info(license_obj)
                zf.writestr('license_info.json', json.dumps(info, indent=2, ensure_ascii=False))

            print(f"✅ 许可证包已导出到: {output_zip}")
            return True

        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False

    def import_license_package(self, input_zip: Path):
        """导入许可证包

        Args:
            input_zip: 输入ZIP文件路径
        """
        try:
            with zipfile.ZipFile(input_zip, 'r') as zf:
                # 读取机器信息
                if 'machine_info.json' in zf.namelist():
                    machine_info = json.loads(zf.read('machine_info.json'))
                    print(f"导出机器ID: {machine_info['machine_id']}")
                    print(f"导出时间: {machine_info['export_time']}")

                # 读取许可证
                if 'license.json' in zf.namelist():
                    license_data = json.loads(zf.read('license.json'))

                    from src.core.license_manager import License
                    license_obj = License.from_dict(license_data)

                    # 验证机器ID
                    current_machine_id = get_machine_id()
                    if license_obj.machine_id != current_machine_id:
                        print("⚠️ 警告: 许可证绑定到不同的机器")
                        print(f"  当前: {current_machine_id}")
                        print(f"  许可证: {license_obj.machine_id}")

                        confirm = input("是否继续导入? (y/n): ").strip().lower()
                        if confirm != 'y':
                            print("❌ 导入已取消")
                            return False

                    # 保存许可证
                    if self.license_manager.save_license(license_obj):
                        print("✅ 许可证已导入")
                        return True
                    else:
                        print("❌ 导入失败")
                        return False
                else:
                    print("❌ 包中未找到许可证文件")
                    return False

        except Exception as e:
            print(f"❌ 导入失败: {e}")
            return False

    def list_backups(self, backup_dir: Path):
        """列出所有备份

        Args:
            backup_dir: 备份目录
        """
        if not backup_dir.exists():
            print("❌ 备份目录不存在")
            return

        backups = []

        # 查找JSON备份
        for file in backup_dir.glob('*.json'):
            try:
                with open(file, encoding='utf-8') as f:
                    data = json.load(f)
                    if 'version' in data and 'license' in data:
                        backups.append({
                            'file': file,
                            'type': 'JSON',
                            'time': data.get('backup_time', 'Unknown')
                        })
            except Exception:
                pass

        # 查找ZIP包
        for file in backup_dir.glob('*.zip'):
            try:
                with zipfile.ZipFile(file, 'r') as zf:
                    if 'machine_info.json' in zf.namelist():
                        machine_info = json.loads(zf.read('machine_info.json'))
                        backups.append({
                            'file': file,
                            'type': 'ZIP',
                            'time': machine_info.get('export_time', 'Unknown')
                        })
            except Exception:
                pass

        if not backups:
            print("未找到备份")
            return

        print(f"\n找到 {len(backups)} 个备份:")
        print("=" * 80)
        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup['file'].name}")
            print(f"   类型: {backup['type']}")
            print(f"   时间: {backup['time']}")
            print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="VirtualChemLab 许可证备份工具")

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # 备份许可证
    backup_parser = subparsers.add_parser('backup', help='备份许可证')
    backup_parser.add_argument('output', type=str, help='输出文件路径')
    backup_parser.add_argument('--no-machine-info', action='store_true',
                               help='不包含机器信息')

    # 恢复许可证
    restore_parser = subparsers.add_parser('restore', help='恢复许可证')
    restore_parser.add_argument('backup_file', type=str, help='备份文件路径')
    restore_parser.add_argument('--no-verify', action='store_true',
                                help='不验证机器ID')

    # 导出许可证包
    export_parser = subparsers.add_parser('export', help='导出许可证包')
    export_parser.add_argument('output', type=str, help='输出ZIP文件路径')

    # 导入许可证包
    import_parser = subparsers.add_parser('import', help='导入许可证包')
    import_parser.add_argument('input', type=str, help='输入ZIP文件路径')

    # 列出备份
    list_parser = subparsers.add_parser('list', help='列出备份')
    list_parser.add_argument('--dir', type=str, default='data/backups',
                             help='备份目录 (默认: data/backups)')

    args = parser.parse_args()

    # 创建许可证管理器
    secret_key = _resolve_license_secret()
    license_file = PROJECT_ROOT / "data" / "license.json"
    license_manager = LicenseManager(secret_key, license_file)

    # 创建备份工具
    tool = LicenseBackupTool(license_manager)

    if args.command == 'backup':
        tool.backup_license(
            Path(args.output),
            include_machine_info=not args.no_machine_info
        )

    elif args.command == 'restore':
        tool.restore_license(
            Path(args.backup_file),
            verify_machine=not args.no_verify
        )

    elif args.command == 'export':
        tool.export_license_package(Path(args.output))

    elif args.command == 'import':
        tool.import_license_package(Path(args.input))

    elif args.command == 'list':
        tool.list_backups(PROJECT_ROOT / args.dir)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
