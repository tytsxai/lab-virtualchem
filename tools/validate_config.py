"""
VirtualChemLab 配置与运行前置校验工具。

本脚本用于解决两个常见维护风险：
1) 文档/口口相传的“配置要求”与真实实现脱节，导致上线或重构时误判风险；
2) 生产环境密钥/目录/配置项缺失，直到运行时报错才暴露问题。

它遵循当前实现的事实来源：
- 配置加载：`src/core/config_loader.py`
- 启动前安全闸：`src/core/startup_preflight.py`

用法示例：
    # 默认读取 .env（不覆盖已存在的环境变量）
    python tools/validate_config.py

    # 指定环境（等价于 ENVIRONMENT=production）
    python tools/validate_config.py --env production

    # 指定 env 文件（先加载，再交给 config_loader；同样不覆盖已有 env）
    python tools/validate_config.py --env-file env.example
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VirtualChemLab 配置校验工具")
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="运行环境 (development/staging/production)。会映射到 ENVIRONMENT。",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="要加载的 env 文件路径（默认: .env；不覆盖已存在的环境变量）",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="打印最终合并后的配置（JSON），用于排障；注意其中可能包含敏感信息。",
    )
    return parser.parse_args()


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    args = _parse_args()

    if args.env:
        os.environ["ENVIRONMENT"] = str(args.env).strip()

    from src.core import config_loader  # noqa: E402
    from src.core.startup_preflight import ensure_secure_startup  # noqa: E402

    env_file = Path(args.env_file).expanduser()
    if not env_file.is_absolute():
        env_file = (PROJECT_ROOT / env_file).resolve()
    if env_file.exists():
        config_loader.load_env_file(str(env_file))

    try:
        config = config_loader.Config.load(env=os.getenv("ENVIRONMENT"))
    except SystemExit as exc:
        # startup_preflight / Config.load 在严格模式可能触发 SystemExit
        return int(getattr(exc, "code", 1) or 1)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 配置加载失败: {exc}")
        return 1

    env_name = getattr(getattr(config, "app", None), "environment", "development")
    print("✅ 配置加载成功")
    print(f"   environment: {env_name}")

    # 配置文件事实来源（深度合并：base.json -> config.json -> {env}.json）
    base_path = PROJECT_ROOT / "config" / "base.json"
    legacy_path = PROJECT_ROOT / "config.json"
    env_path = PROJECT_ROOT / "config" / f"{env_name}.json"
    print("📄 配置文件加载顺序（存在则参与合并）:")
    for path in (base_path, legacy_path, env_path):
        marker = "✅" if path.exists() else "➖"
        print(f"   {marker} {path.relative_to(PROJECT_ROOT)}")

    # 启动前安全闸（生产环境为 fail-fast）
    try:
        ensure_secure_startup(config=config)
        print("🔐 启动前安全闸: ✅ 通过")
    except SystemExit:
        print("🔐 启动前安全闸: ❌ 未通过（生产环境 fail-fast）")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"🔐 启动前安全闸: ⚠️  {exc}")

    # 关键目录存在性（Config.load 已负责创建；这里做显式展示）
    paths_cfg = getattr(config, "paths", None)
    if paths_cfg is not None:
        for key in ("templates", "knowledge", "i18n", "user_data", "reports", "logs"):
            raw = getattr(paths_cfg, key, None)
            if not raw:
                continue
            p = Path(str(raw))
            abs_path = p if p.is_absolute() else (PROJECT_ROOT / p)
            exists = abs_path.exists()
            print(f"📁 {key}: {abs_path} ({'exists' if exists else 'missing'})")

    # config.json 语法健康（用于解释“格式错误导致无法启动”）
    if legacy_path.exists():
        try:
            _read_json(legacy_path)
            print("🧾 config.json: ✅ JSON 格式有效")
        except Exception as exc:  # noqa: BLE001
            print(f"🧾 config.json: ❌ JSON 格式错误: {exc}")
            return 1

    if args.print_config:
        # 注意：可能包含 jwt/session 等敏感信息，仅用于本机排障
        if hasattr(config, "model_dump"):
            data = config.model_dump()
        elif hasattr(config, "dict"):
            data = config.dict()
        else:
            data = {}
        print(json.dumps(data, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

