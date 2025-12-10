"""
许可证生成工具

用于生成和管理VirtualChemLab的许可证
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.crypto_payment import (  # noqa: E402
    CryptoCurrency,
    CryptoPaymentManager,
    ManualPaymentVerifier,
    PaymentAddress,
)
from src.core.license_manager import (  # noqa: E402
    CryptoPayment,
    LicenseManager,
    LicenseType,
    get_machine_id,
)


def _resolve_license_secret() -> str:
    """从环境变量读取许可证密钥，避免硬编码"""
    secret = os.getenv("LICENSE_SECRET_KEY", "").strip()
    if not secret:
        raise ValueError("未设置 LICENSE_SECRET_KEY，禁止使用默认/硬编码密钥")
    if secret.startswith("YOUR_") or len(secret) < 32:
        raise ValueError("LICENSE_SECRET_KEY 长度不足或仍为占位值，请提供>=32位的生产密钥")
    return secret


def create_license_manager() -> LicenseManager:
    """创建许可证管理器"""
    secret_key = _resolve_license_secret()
    license_file = PROJECT_ROOT / "data" / "license.json"

    return LicenseManager(secret_key, license_file)


def create_payment_manager() -> CryptoPaymentManager:
    """创建支付管理器"""
    manager = CryptoPaymentManager()

    # 添加支持的收款地址 (示例,需要替换为真实地址)
    payment_addresses = [
        PaymentAddress(currency=CryptoCurrency.BTC, address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", min_confirmations=3),
        PaymentAddress(
            currency=CryptoCurrency.ETH, address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", min_confirmations=12
        ),
        PaymentAddress(
            currency=CryptoCurrency.USDT, address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", min_confirmations=12
        ),
        PaymentAddress(currency=CryptoCurrency.TRX, address="TYASr5UV6HEcXatwdFQfmLVUqQQQMUxHLS", min_confirmations=19),
    ]

    for addr in payment_addresses:
        manager.add_payment_address(addr)

    # 添加验证器 (默认使用手动验证器,可切换为API验证器)
    for currency in [CryptoCurrency.BTC, CryptoCurrency.ETH, CryptoCurrency.USDT, CryptoCurrency.TRX]:
        # 使用手动验证器 (离线模式)
        verifier = ManualPaymentVerifier()
        manager.add_verifier(currency, verifier)

        # 如果需要在线验证,使用以下代码:
        # verifier = BlockchainAPIVerifier(currency, api_key="YOUR_API_KEY")
        # manager.add_verifier(currency, verifier)

    return manager


def generate_license_interactive():
    """交互式生成许可证"""
    print("=" * 60)
    print("VirtualChemLab 许可证生成器")
    print("=" * 60)
    print()

    # 获取用户信息
    user_id = input("用户ID: ").strip()
    email = input("邮箱: ").strip()

    # 获取机器ID
    print("\n当前机器ID:", get_machine_id())
    use_current = input("使用当前机器ID? (y/n): ").strip().lower()
    machine_id = get_machine_id() if use_current == "y" else input("机器ID: ").strip()

    # 选择许可证类型
    print("\n许可证类型:")
    for i, lt in enumerate(LicenseType, 1):
        print(f"  {i}. {lt.value}")

    type_choice = int(input("选择 (1-5): ")) - 1
    license_type = list(LicenseType)[type_choice]

    # 获取支付信息
    print("\n支付信息:")
    print("支持的货币: BTC, ETH, USDT, TRX, USDC, BNB, SOL, ADA, DOGE, LTC")
    currency = input("货币类型: ").strip().upper()
    tx_hash = input("交易哈希: ").strip()
    amount = float(input("支付金额: "))
    recipient_address = input("收款地址: ").strip()

    # 创建支付对象
    payment = CryptoPayment(
        currency=currency, tx_hash=tx_hash, amount=amount, recipient_address=recipient_address, timestamp=datetime.now()
    )

    # 有效期
    validity_days = int(input("\n有效期(天数, 默认365): ") or "365")

    # 生成许可证
    license_manager = create_license_manager()
    license_obj = license_manager.generate_license(
        user_id=user_id,
        email=email,
        machine_id=machine_id,
        license_type=license_type,
        payment=payment,
        validity_days=validity_days,
    )

    # 保存许可证
    if license_manager.save_license(license_obj):
        print("\n✅ 许可证生成成功!")
        print(f"许可证密钥: {license_obj.license_key}")
        print(f"保存位置: {license_manager.license_file}")

        # 显示详细信息
        info = license_manager.get_license_info(license_obj)
        print("\n许可证信息:")
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        print("\n❌ 许可证保存失败")


def generate_license_batch(config_file: Path):
    """批量生成许可证

    Args:
        config_file: 配置文件路径 (JSON格式)
    """
    with open(config_file, encoding="utf-8") as f:
        config = json.load(f)

    license_manager = create_license_manager()

    for item in config.get("licenses", []):
        # 创建支付对象
        payment_data = item["payment"]
        payment = CryptoPayment(
            currency=payment_data["currency"],
            tx_hash=payment_data["tx_hash"],
            amount=payment_data["amount"],
            recipient_address=payment_data["recipient_address"],
            timestamp=datetime.fromisoformat(payment_data.get("timestamp", datetime.now().isoformat())),
        )

        # 生成许可证
        license_obj = license_manager.generate_license(
            user_id=item["user_id"],
            email=item["email"],
            machine_id=item["machine_id"],
            license_type=LicenseType(item["license_type"]),
            payment=payment,
            validity_days=item.get("validity_days", 365),
        )

        # 保存到指定位置
        output_file = PROJECT_ROOT / "data" / "licenses" / f"{item['user_id']}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        license_manager.license_file = output_file
        if license_manager.save_license(license_obj):
            print(f"✅ 生成许可证: {item['email']} -> {output_file}")
        else:
            print(f"❌ 生成失败: {item['email']}")


def verify_payment(tx_hash: str, currency: str, expected_amount: float):
    """验证支付

    Args:
        tx_hash: 交易哈希
        currency: 货币类型
        expected_amount: 期望金额
    """
    print(f"\n验证支付: {tx_hash}")
    print(f"货币: {currency}, 金额: {expected_amount}")

    payment_manager = create_payment_manager()

    # 执行验证
    verification = payment_manager.verify_payment(
        currency=currency.lower(), tx_hash=tx_hash, expected_amount=expected_amount
    )

    if verification.is_valid:
        print("\n✅ 支付验证通过")
        print(f"交易金额: {verification.amount} {verification.currency}")
        print(f"确认数: {verification.confirmations}")
        print(f"时间: {verification.timestamp}")
    else:
        print("\n❌ 支付验证失败")
        print(f"原因: {verification.error_message}")


def activate_license(license_file: Path):
    """激活许可证

    Args:
        license_file: 许可证文件路径
    """
    license_manager = create_license_manager()
    license_manager.license_file = license_file

    # 加载许可证
    license_obj = license_manager.load_license()

    if not license_obj:
        print("❌ 无法加载许可证")
        return

    # 获取当前机器ID
    machine_id = get_machine_id()
    print(f"当前机器ID: {machine_id}")
    print(f"许可证绑定ID: {license_obj.machine_id}")

    # 激活
    success, error_msg = license_manager.activate_license(license_obj, machine_id)

    if success:
        # 保存
        if license_manager.save_license(license_obj):
            print("\n✅ 许可证激活成功!")
        else:
            print("\n❌ 许可证保存失败")
    else:
        print(f"\n❌ 激活失败: {error_msg}")


def check_license():
    """检查当前许可证"""
    license_manager = create_license_manager()
    license_obj = license_manager.load_license()

    if not license_obj:
        print("❌ 未找到许可证")
        return

    # 验证
    machine_id = get_machine_id()
    status, error_msg = license_manager.validate_license(license_obj, machine_id)

    print("=" * 60)
    print("许可证状态")
    print("=" * 60)

    info = license_manager.get_license_info(license_obj)
    print(json.dumps(info, indent=2, ensure_ascii=False))

    print(f"\n状态: {status.value}")
    if error_msg:
        print(f"消息: {error_msg}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="VirtualChemLab 许可证管理工具")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 生成许可证
    generate_parser = subparsers.add_parser("generate", help="生成许可证")
    generate_parser.add_argument("--batch", type=str, help="批量生成配置文件")

    # 验证支付
    verify_parser = subparsers.add_parser("verify", help="验证支付")
    verify_parser.add_argument("tx_hash", help="交易哈希")
    verify_parser.add_argument("currency", help="货币类型")
    verify_parser.add_argument("amount", type=float, help="金额")

    # 激活许可证
    activate_parser = subparsers.add_parser("activate", help="激活许可证")
    activate_parser.add_argument("license_file", type=str, help="许可证文件路径")

    # 检查许可证
    subparsers.add_parser("check", help="检查许可证")

    # 获取机器ID
    subparsers.add_parser("machine-id", help="获取机器ID")

    args = parser.parse_args()

    if args.command == "generate":
        if args.batch:
            generate_license_batch(Path(args.batch))
        else:
            generate_license_interactive()

    elif args.command == "verify":
        verify_payment(args.tx_hash, args.currency, args.amount)

    elif args.command == "activate":
        activate_license(Path(args.license_file))

    elif args.command == "check":
        check_license()

    elif args.command == "machine-id":
        print(f"机器ID: {get_machine_id()}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
