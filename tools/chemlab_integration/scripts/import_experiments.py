#!/usr/bin/env python3
"""仅导入实验数据"""

import sys
from pathlib import Path

# 复用主脚本
TOOL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(TOOL_ROOT))

from scripts.import_all import main  # noqa: E402

if __name__ == "__main__":
    # 添加 --experiments-only 参数
    sys.argv.append("--experiments-only")
    sys.exit(main())
