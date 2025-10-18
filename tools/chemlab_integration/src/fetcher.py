"""ChemLab 数据获取模块

负责从 GitHub 克隆/更新 chemlab 仓库并提取数据。
"""

import logging
import shutil
from pathlib import Path
from typing import Any

import yaml
from git import Repo

logger = logging.getLogger(__name__)


class ChemLabFetcher:
    """ChemLab 数据获取器"""

    def __init__(self, config_path: str | Path):
        """初始化获取器

        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.repo_url = self.config["source"]["repository"]
        self.branch = self.config["source"]["branch"]
        self.clone_path = Path(self.config["source"]["clone_path"])
        self.repo: Repo | None = None

    def _load_config(self, config_path: str | Path) -> dict[str, Any]:
        """加载配置文件"""
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def clone_or_update(self) -> Path:
        """克隆或更新 chemlab 仓库

        Returns:
            仓库本地路径
        """
        if self.clone_path.exists():
            if self.config["source"].get("auto_update", True):
                logger.info(f"更新现有仓库: {self.clone_path}")
                try:
                    self.repo = Repo(self.clone_path)
                    origin = self.repo.remotes.origin
                    origin.pull(self.branch)
                    logger.info("✅ 仓库更新成功")
                except Exception as e:
                    logger.error(f"更新失败: {e}")
                    logger.info("尝试重新克隆...")
                    shutil.rmtree(self.clone_path)
                    return self._clone_repo()
            else:
                logger.info(f"使用现有仓库: {self.clone_path}")
                self.repo = Repo(self.clone_path)
        else:
            return self._clone_repo()

        return self.clone_path

    def _clone_repo(self) -> Path:
        """克隆仓库"""
        logger.info(f"克隆仓库: {self.repo_url}")
        self.clone_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.repo = Repo.clone_from(
                self.repo_url, self.clone_path, branch=self.branch, depth=1  # 浅克隆
            )
            logger.info(f"✅ 仓库克隆成功: {self.clone_path}")
        except Exception as e:
            logger.error(f"❌ 克隆失败: {e}")
            raise

        return self.clone_path

    def get_repo_info(self) -> dict[str, str]:
        """获取仓库信息

        Returns:
            仓库信息字典
        """
        if not self.repo:
            raise RuntimeError("仓库未初始化,请先调用 clone_or_update()")

        return {
            "url": self.repo_url,
            "branch": self.branch,
            "commit": self.repo.head.commit.hexsha[:7],
            "commit_date": self.repo.head.commit.committed_datetime.isoformat(),
            "author": str(self.repo.head.commit.author),
        }

    def list_examples(self) -> list[Path]:
        """列出所有示例文件

        Returns:
            示例文件路径列表
        """
        examples_dir = self.clone_path / self.config["source"]["data_paths"]["experiments"]

        if not examples_dir.exists():
            logger.warning(f"示例目录不存在: {examples_dir}")
            return []

        # 查找 Python 脚本文件
        py_files = list(examples_dir.glob("**/*.py"))
        logger.info(f"找到 {len(py_files)} 个示例文件")

        return py_files

    def list_molecule_data(self) -> list[Path]:
        """列出分子数据文件

        Returns:
            分子数据文件路径列表
        """
        db_dir = self.clone_path / self.config["source"]["data_paths"]["molecules"]

        if not db_dir.exists():
            logger.warning(f"分子数据库目录不存在: {db_dir}")
            return []

        # 查找数据文件 (可能是 JSON, YAML, Python 等)
        data_files = []
        for ext in ["*.json", "*.yaml", "*.yml", "*.py"]:
            data_files.extend(db_dir.glob(f"**/{ext}"))

        logger.info(f"找到 {len(data_files)} 个分子数据文件")
        return data_files

    def extract_file_content(self, file_path: Path) -> str:
        """提取文件内容

        Args:
            file_path: 文件路径

        Returns:
            文件内容
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(file_path, encoding="latin-1") as f:
                return f.read()

    def cleanup(self):
        """清理临时文件"""
        if self.clone_path.exists():
            logger.info(f"清理临时目录: {self.clone_path}")
            shutil.rmtree(self.clone_path)


# 使用示例
if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src import CONFIG_PATH

    logging.basicConfig(level=logging.INFO)

    fetcher = ChemLabFetcher(CONFIG_PATH)
    repo_path = fetcher.clone_or_update()

    print("\n仓库信息:")
    for k, v in fetcher.get_repo_info().items():
        print(f"  {k}: {v}")

    print(f"\n示例文件: {len(fetcher.list_examples())} 个")
    print(f"分子数据: {len(fetcher.list_molecule_data())} 个")
