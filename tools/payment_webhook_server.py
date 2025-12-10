"""
支付回调服务器

用于接收和处理加密货币支付的webhook回调
"""

import json
import logging
import os
import secrets
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.license_manager import CryptoPayment, LicenseManager, LicenseType  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _resolve_license_secret() -> str:
    """从环境变量读取许可证密钥，避免硬编码"""
    secret = os.getenv("LICENSE_SECRET_KEY", "").strip()
    if not secret:
        raise ValueError("未设置 LICENSE_SECRET_KEY，禁止使用默认/硬编码密钥")
    if secret.startswith("YOUR_") or len(secret) < 32:
        raise ValueError("LICENSE_SECRET_KEY 长度不足或仍为占位值，请提供>=32位的生产密钥")
    return secret


class PaymentWebhookHandler(BaseHTTPRequestHandler):
    """支付Webhook处理器"""

    # 存储待处理的支付
    pending_payments: dict[str, dict[str, Any]] = {}

    def do_POST(self):
        """处理POST请求"""
        if not self._validate_webhook_secret():
            self.send_response(401)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8'))
            self._handle_payment_notification(data)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

        except Exception as e:
            logger.error(f"处理webhook失败: {e}")
            self.send_response(500)
            self.end_headers()

    def _handle_payment_notification(self, data: dict[str, Any]):
        """处理支付通知

        Args:
            data: 支付数据
        """
        tx_hash = data.get('tx_hash')
        currency = data.get('currency')
        amount = data.get('amount')
        confirmations = data.get('confirmations', 0)

        logger.info(f"收到支付通知: {currency} {amount} - {tx_hash}")

        # 保存到待处理列表
        self.pending_payments[tx_hash] = {
            'currency': currency,
            'amount': amount,
            'confirmations': confirmations,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }

        # 如果确认数足够,自动生成许可证
        if confirmations >= self._get_min_confirmations(currency):
            self._generate_license_for_payment(tx_hash, data)

    def _validate_webhook_secret(self) -> bool:
        """校验 webhook 密钥，避免未授权的许可证生成"""
        expected = os.getenv("WEBHOOK_SECRET", "").strip()
        provided = (self.headers.get("X-Webhook-Secret") or self.headers.get("X-Webhook-Signature") or "").strip()

        if not expected:
            logger.error("WEBHOOK_SECRET 未设置，拒绝处理回调请求")
            return False

        if not provided:
            logger.warning("缺少 webhook 密钥头，已拒绝请求")
            return False

        if not secrets.compare_digest(provided, expected):
            logger.warning("webhook 密钥不匹配，已拒绝请求")
            return False

        return True

    def _generate_license_for_payment(self, tx_hash: str, payment_data: dict[str, Any]):
        """为支付生成许可证"""
        try:
            # 获取订单信息 (实际应从数据库查询)
            order = self._get_order_by_tx(tx_hash)

            if not order:
                logger.warning(f"未找到交易对应的订单: {tx_hash}")
                return

            # 创建支付对象
            payment = CryptoPayment(
                currency=payment_data['currency'],
                tx_hash=tx_hash,
                amount=payment_data['amount'],
                recipient_address=payment_data.get('recipient_address', ''),
                timestamp=datetime.now(),
                confirmations=payment_data.get('confirmations', 0)
            )

            # 生成许可证
            secret_key = _resolve_license_secret()
            license_file = PROJECT_ROOT / "data" / "licenses" / f"{order['user_id']}.json"

            license_manager = LicenseManager(secret_key, license_file)
            license_obj = license_manager.generate_license(
                user_id=order['user_id'],
                email=order['email'],
                machine_id=order['machine_id'],
                license_type=LicenseType(order['license_type']),
                payment=payment,
                validity_days=order.get('validity_days', 365)
            )

            # 保存许可证
            if license_manager.save_license(license_obj):
                logger.info(f"✅ 自动生成许可证: {order['email']}")

                # 发送邮件通知 (TODO)
                self._send_license_email(order['email'], license_obj)

                # 更新状态
                self.pending_payments[tx_hash]['status'] = 'completed'

        except Exception as e:
            logger.error(f"生成许可证失败: {e}")

    def _get_order_by_tx(self, tx_hash: str) -> dict[str, Any]:
        """根据交易哈希获取订单

        这里使用简单的JSON文件存储,实际应使用数据库
        """
        orders_file = PROJECT_ROOT / "data" / "orders.json"

        if not orders_file.exists():
            return None

        with open(orders_file, encoding='utf-8') as f:
            orders = json.load(f)

        for order in orders:
            if order.get('tx_hash') == tx_hash:
                return order

        return None

    def _send_license_email(self, email: str, license_obj):
        """发送许可证邮件

        Args:
            email: 邮箱地址
            license_obj: 许可证对象
        """
        # TODO: 实现邮件发送
        logger.info(f"发送许可证邮件到: {email}")
        logger.info(f"许可证密钥: {license_obj.license_key}")

    def _get_min_confirmations(self, currency: str) -> int:
        """获取最小确认数"""
        confirmations_map = {
            'BTC': 3,
            'ETH': 12,
            'USDT': 12,
            'TRX': 19,
            'SOL': 32
        }
        return confirmations_map.get(currency.upper(), 6)


def start_webhook_server(host: str = '0.0.0.0', port: int = 8888):
    """启动webhook服务器

    Args:
        host: 监听地址
        port: 监听端口
    """
    server = HTTPServer((host, port), PaymentWebhookHandler)

    logger.info("=" * 60)
    logger.info("支付Webhook服务器已启动")
    logger.info(f"监听地址: http://{host}:{port}")
    logger.info("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="支付Webhook服务器")
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8888, help='监听端口')

    args = parser.parse_args()

    start_webhook_server(args.host, args.port)
