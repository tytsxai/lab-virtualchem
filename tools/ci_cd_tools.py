"""
CI/CD集成工具

提供持续集成和持续部署的自动化工具
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    duration: float
    output: str
    errors: list[str]
    warnings: list[str]


@dataclass
class DeploymentConfig:
    """部署配置"""
    name: str
    environment: str  # dev, staging, production
    target_path: Path
    backup_enabled: bool = True
    pre_deploy_hooks: list[str] = None
    post_deploy_hooks: list[str] = None


class GitHubActionsGenerator:
    """GitHub Actions工作流生成器"""

    @staticmethod
    def generate_ci_workflow(output_path: Path):
        """生成CI工作流"""
        workflow = {
            'name': 'CI',
            'on': {
                'push': {
                    'branches': ['main', 'develop']
                },
                'pull_request': {
                    'branches': ['main', 'develop']
                }
            },
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'strategy': {
                        'matrix': {
                            'python-version': ['3.9', '3.10', '3.11']
                        }
                    },
                    'steps': [
                        {
                            'name': 'Checkout code',
                            'uses': 'actions/checkout@v3'
                        },
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {
                                'python-version': '${{ matrix.python-version }}'
                            }
                        },
                        {
                            'name': 'Install dependencies',
                            'run': '\n'.join([
                                'python -m pip install --upgrade pip',
                                'pip install -r requirements.txt',
                                'pip install -r requirements-dev.txt'
                            ])
                        },
                        {
                            'name': 'Lint with ruff',
                            'run': 'ruff check src/'
                        },
                        {
                            'name': 'Type check with mypy',
                            'run': 'mypy src/ --ignore-missing-imports'
                        },
                        {
                            'name': 'Run tests',
                            'run': 'pytest tests/ -v --cov=src --cov-report=xml'
                        },
                        {
                            'name': 'Upload coverage',
                            'uses': 'codecov/codecov-action@v3',
                            'with': {
                                'file': './coverage.xml',
                                'fail_ci_if_error': True
                            }
                        }
                    ]
                },
                'build': {
                    'runs-on': 'windows-latest',
                    'needs': 'test',
                    'steps': [
                        {
                            'name': 'Checkout code',
                            'uses': 'actions/checkout@v3'
                        },
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {
                                'python-version': '3.11'
                            }
                        },
                        {
                            'name': 'Install dependencies',
                            'run': '\n'.join([
                                'python -m pip install --upgrade pip',
                                'pip install -r requirements.txt',
                                'pip install pyinstaller'
                            ])
                        },
                        {
                            'name': 'Build executable',
                            'run': 'pyinstaller VirtualChemLab.spec'
                        },
                        {
                            'name': 'Upload artifact',
                            'uses': 'actions/upload-artifact@v3',
                            'with': {
                                'name': 'VirtualChemLab-Windows',
                                'path': 'dist/VirtualChemLab/'
                            }
                        }
                    ]
                }
            }
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml.dump(workflow, sort_keys=False), encoding='utf-8')
        print(f"已生成CI工作流: {output_path}")

    @staticmethod
    def generate_release_workflow(output_path: Path):
        """生成发布工作流"""
        workflow = {
            'name': 'Release',
            'on': {
                'push': {
                    'tags': ['v*']
                }
            },
            'jobs': {
                'release': {
                    'runs-on': 'windows-latest',
                    'steps': [
                        {
                            'name': 'Checkout code',
                            'uses': 'actions/checkout@v3'
                        },
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {
                                'python-version': '3.11'
                            }
                        },
                        {
                            'name': 'Install dependencies',
                            'run': '\n'.join([
                                'python -m pip install --upgrade pip',
                                'pip install -r requirements.txt',
                                'pip install pyinstaller'
                            ])
                        },
                        {
                            'name': 'Build executable',
                            'run': 'pyinstaller VirtualChemLab.spec'
                        },
                        {
                            'name': 'Create ZIP package',
                            'run': 'Compress-Archive -Path dist/VirtualChemLab/* -DestinationPath VirtualChemLab-${{ github.ref_name }}.zip',
                            'shell': 'pwsh'
                        },
                        {
                            'name': 'Create Release',
                            'uses': 'softprops/action-gh-release@v1',
                            'with': {
                                'files': 'VirtualChemLab-${{ github.ref_name }}.zip',
                                'draft': False,
                                'prerelease': False
                            },
                            'env': {
                                'GITHUB_TOKEN': '${{ secrets.GITHUB_TOKEN }}'
                            }
                        }
                    ]
                }
            }
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml.dump(workflow, sort_keys=False), encoding='utf-8')
        print(f"已生成Release工作流: {output_path}")


class BuildAutomation:
    """构建自动化"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run_linters(self) -> BuildResult:
        """运行代码检查"""
        start_time = datetime.now()
        errors = []
        warnings = []
        output = []

        # 运行ruff
        try:
            result = subprocess.run(
                ['ruff', 'check', 'src/'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            output.append("=== Ruff ===")
            output.append(result.stdout)

            if result.returncode != 0:
                errors.append(f"Ruff检查失败: {result.stderr}")
        except Exception as e:
            errors.append(f"运行Ruff失败: {e}")

        # 运行mypy
        try:
            result = subprocess.run(
                ['mypy', 'src/', '--ignore-missing-imports'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            output.append("\n=== Mypy ===")
            output.append(result.stdout)

            if result.returncode != 0:
                warnings.append("Mypy发现类型问题")
        except Exception as e:
            warnings.append(f"运行Mypy失败: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return BuildResult(
            success=len(errors) == 0,
            duration=duration,
            output='\n'.join(output),
            errors=errors,
            warnings=warnings
        )

    def run_tests(self) -> BuildResult:
        """运行测试"""
        start_time = datetime.now()
        errors = []
        warnings = []
        output = []

        try:
            result = subprocess.run(
                ['pytest', 'tests/', '-v', '--cov=src', '--cov-report=term'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            output.append(result.stdout)

            if result.returncode != 0:
                errors.append("测试失败")
        except Exception as e:
            errors.append(f"运行测试失败: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return BuildResult(
            success=len(errors) == 0,
            duration=duration,
            output='\n'.join(output),
            errors=errors,
            warnings=warnings
        )

    def build_executable(self) -> BuildResult:
        """构建可执行文件"""
        start_time = datetime.now()
        errors = []
        warnings = []
        output = []

        try:
            # 检查spec文件
            spec_file = self.project_root / 'VirtualChemLab.spec'
            if not spec_file.exists():
                errors.append("VirtualChemLab.spec文件不存在")
                return BuildResult(
                    success=False,
                    duration=0,
                    output='',
                    errors=errors,
                    warnings=warnings
                )

            # 运行PyInstaller
            result = subprocess.run(
                ['pyinstaller', 'VirtualChemLab.spec'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            output.append(result.stdout)

            if result.returncode != 0:
                errors.append(f"构建失败: {result.stderr}")
            else:
                # 检查输出文件
                dist_dir = self.project_root / 'dist' / 'VirtualChemLab'
                if not dist_dir.exists():
                    errors.append("构建输出目录不存在")
                else:
                    exe_file = dist_dir / 'VirtualChemLab.exe'
                    if exe_file.exists():
                        size_mb = exe_file.stat().st_size / 1024 / 1024
                        output.append(f"\n构建成功! 可执行文件大小: {size_mb:.2f}MB")
                    else:
                        errors.append("可执行文件未生成")

        except Exception as e:
            errors.append(f"构建过程出错: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return BuildResult(
            success=len(errors) == 0,
            duration=duration,
            output='\n'.join(output),
            errors=errors,
            warnings=warnings
        )


class DeploymentManager:
    """部署管理器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_dir = project_root / 'backups' / 'deployments'
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def deploy(self, config: DeploymentConfig) -> bool:
        """执行部署"""
        print(f"\n{'='*60}")
        print(f"开始部署: {config.name} ({config.environment})")
        print(f"{'='*60}\n")

        try:
            # 1. 备份
            if config.backup_enabled:
                print("1. 创建备份...")
                self._create_backup(config)

            # 2. 预部署钩子
            if config.pre_deploy_hooks:
                print("2. 执行预部署脚本...")
                for hook in config.pre_deploy_hooks:
                    self._run_hook(hook)

            # 3. 复制文件
            print("3. 复制文件...")
            self._copy_files(config.target_path)

            # 4. 后部署钩子
            if config.post_deploy_hooks:
                print("4. 执行后部署脚本...")
                for hook in config.post_deploy_hooks:
                    self._run_hook(hook)

            print(f"\n{'='*60}")
            print(f"✅ 部署成功: {config.name}")
            print(f"{'='*60}\n")

            return True

        except Exception as e:
            print(f"\n❌ 部署失败: {e}")

            # 回滚
            if config.backup_enabled:
                print("正在回滚...")
                self._rollback(config)

            return False

    def _create_backup(self, config: DeploymentConfig):
        """创建备份"""
        if config.target_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{config.name}_{config.environment}_{timestamp}"
            backup_path = self.backup_dir / backup_name

            import shutil
            shutil.copytree(config.target_path, backup_path)
            print(f"  备份已保存: {backup_path}")

    def _run_hook(self, hook: str):
        """运行钩子脚本"""
        result = subprocess.run(
            hook,
            shell=True,
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"钩子脚本失败: {hook}\n{result.stderr}")

        print(f"  执行成功: {hook}")

    def _copy_files(self, target_path: Path):
        """复制文件"""
        import shutil

        source = self.project_root / 'dist' / 'VirtualChemLab'

        if not source.exists():
            raise Exception(f"源目录不存在: {source}")

        # 确保目标目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 删除旧文件
        if target_path.exists():
            shutil.rmtree(target_path)

        # 复制新文件
        shutil.copytree(source, target_path)
        print(f"  文件已复制到: {target_path}")

    def _rollback(self, config: DeploymentConfig):
        """回滚部署"""
        # 查找最新备份
        backups = sorted(
            [b for b in self.backup_dir.iterdir() if b.name.startswith(f"{config.name}_{config.environment}")],
            reverse=True
        )

        if backups:
            latest_backup = backups[0]

            import shutil
            if config.target_path.exists():
                shutil.rmtree(config.target_path)

            shutil.copytree(latest_backup, config.target_path)
            print(f"  已回滚到备份: {latest_backup}")


class PipelineRunner:
    """Pipeline运行器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.build_automation = BuildAutomation(project_root)

    def run_full_pipeline(self) -> dict[str, Any]:
        """运行完整pipeline"""
        print("\n" + "="*60)
        print("🚀 开始CI/CD Pipeline")
        print("="*60 + "\n")

        results = {}

        # 1. 代码检查
        print("📝 步骤 1/3: 代码检查")
        lint_result = self.build_automation.run_linters()
        results['lint'] = asdict(lint_result)

        if not lint_result.success:
            print("❌ 代码检查失败，停止pipeline")
            return results

        print("✅ 代码检查通过\n")

        # 2. 测试
        print("🧪 步骤 2/3: 运行测试")
        test_result = self.build_automation.run_tests()
        results['test'] = asdict(test_result)

        if not test_result.success:
            print("❌ 测试失败，停止pipeline")
            return results

        print("✅ 测试通过\n")

        # 3. 构建
        print("🔨 步骤 3/3: 构建可执行文件")
        build_result = self.build_automation.build_executable()
        results['build'] = asdict(build_result)

        if not build_result.success:
            print("❌ 构建失败")
            return results

        print("✅ 构建成功\n")

        print("="*60)
        print("🎉 Pipeline完成!")
        print("="*60 + "\n")

        # 保存结果
        results_file = self.project_root / 'pipeline_results.json'
        results_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')

        return results


# 使用示例
if __name__ == '__main__':
    project_root = Path('.')

    # 1. 生成GitHub Actions工作流
    print("=== 生成GitHub Actions工作流 ===")
    GitHubActionsGenerator.generate_ci_workflow(project_root / '.github' / 'workflows' / 'ci.yml')
    GitHubActionsGenerator.generate_release_workflow(project_root / '.github' / 'workflows' / 'release.yml')

    # 2. 运行Pipeline
    print("\n=== 运行CI/CD Pipeline ===")
    pipeline = PipelineRunner(project_root)
    results = pipeline.run_full_pipeline()

    # 3. 打印摘要
    print("\n=== Pipeline摘要 ===")
    for stage, result in results.items():
        status = "✅" if result['success'] else "❌"
        print(f"{status} {stage}: {result['duration']:.2f}秒")

        if result['errors']:
            print(f"  错误: {len(result['errors'])}")
            for error in result['errors']:
                print(f"    - {error}")

        if result['warnings']:
            print(f"  警告: {len(result['warnings'])}")
