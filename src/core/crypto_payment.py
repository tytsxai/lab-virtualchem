"""
加密货币支付验证模块

支持多种数字货币的支付验证
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import requests

logger = logging.getLogger(__name__)


class CryptoCurrency(Enum):
    """支持的加密货币"""

    BTC = "bitcoin"  # 比特币
    ETH = "ethereum"  # 以太坊
    USDT = "tether"  # 泰达币
    USDC = "usd-coin"  # USD Coin
    BNB = "binance-coin"  # 币安币
    TRX = "tron"  # 波场
    SOL = "solana"  # Solana
    ADA = "cardano"  # Cardano
    DOGE = "dogecoin"  # 狗狗币
    LTC = "litecoin"  # 莱特币


@dataclass
class PaymentAddress:
    """收款地址配置"""

    currency: CryptoCurrency
    address: str
    network: str = "mainnet"  # 网络类型
    min_confirmations: int = 3  # 最小确认数


@dataclass
class PaymentVerification:
    """支付验证结果"""

    is_valid: bool
    tx_hash: str
    amount: float
    currency: str
    confirmations: int
    timestamp: datetime
    block_number: int | None = None
    error_message: str | None = None


class IPaymentVerifier(ABC):
    """支付验证器接口"""

    @abstractmethod
    def verify_payment(
        self, tx_hash: str, expected_amount: float, recipient_address: str
    ) -> PaymentVerification:  # noqa: ARG002
        """验证支付"""
        pass

    @abstractmethod
    def get_transaction_info(self, tx_hash: str) -> dict[str, Any] | None:
        """获取交易信息"""
        pass


class BlockchainAPIVerifier(IPaymentVerifier):
    """使用区块链API验证支付"""

    def __init__(self, currency: CryptoCurrency, api_key: str | None = None):
        """初始化

        Args:
            currency: 货币类型
            api_key: API密钥 (可选)
        """
        self.currency = currency
        self.api_key = api_key
        self.api_endpoints = self._get_api_endpoints()

    def verify_payment(
        self, tx_hash: str, expected_amount: float, recipient_address: str
    ) -> PaymentVerification:  # noqa: ARG002
        """验证支付

        Args:
            tx_hash: 交易哈希
            expected_amount: 期望金额
            recipient_address: 收款地址

        Returns:
            支付验证结果
        """
        try:
            # 获取交易信息
            tx_info = self.get_transaction_info(tx_hash)

            if not tx_info:
                return PaymentVerification(
                    is_valid=False,
                    tx_hash=tx_hash,
                    amount=0,
                    currency=self.currency.value,
                    confirmations=0,
                    timestamp=datetime.now(),
                    error_message="无法获取交易信息",
                )

            # 验证金额
            actual_amount = tx_info.get("amount", 0)
            if actual_amount < expected_amount * 0.99:  # 允许1%误差
                return PaymentVerification(
                    is_valid=False,
                    tx_hash=tx_hash,
                    amount=actual_amount,
                    currency=self.currency.value,
                    confirmations=tx_info.get("confirmations", 0),
                    timestamp=datetime.fromtimestamp(tx_info.get("timestamp", 0)),
                    error_message=f"金额不足: 期望 {expected_amount}, 实际 {actual_amount}",
                )

            # 验证收款地址
            to_address = tx_info.get("to_address", "")
            if to_address.lower() != recipient_address.lower():
                return PaymentVerification(
                    is_valid=False,
                    tx_hash=tx_hash,
                    amount=actual_amount,
                    currency=self.currency.value,
                    confirmations=tx_info.get("confirmations", 0),
                    timestamp=datetime.fromtimestamp(tx_info.get("timestamp", 0)),
                    error_message="收款地址不匹配",
                )

            # 验证确认数
            confirmations = tx_info.get("confirmations", 0)
            min_confirmations = self._get_min_confirmations()

            if confirmations < min_confirmations:
                return PaymentVerification(
                    is_valid=False,
                    tx_hash=tx_hash,
                    amount=actual_amount,
                    currency=self.currency.value,
                    confirmations=confirmations,
                    timestamp=datetime.fromtimestamp(tx_info.get("timestamp", 0)),
                    error_message=f"确认数不足: {confirmations}/{min_confirmations}",
                )

            # 验证通过
            return PaymentVerification(
                is_valid=True,
                tx_hash=tx_hash,
                amount=actual_amount,
                currency=self.currency.value,
                confirmations=confirmations,
                timestamp=datetime.fromtimestamp(tx_info.get("timestamp", 0)),
                block_number=tx_info.get("block_number"),
            )

        except Exception as e:
            logger.error(f"支付验证失败: {e}")
            return PaymentVerification(
                is_valid=False,
                tx_hash=tx_hash,
                amount=0,
                currency=self.currency.value,
                confirmations=0,
                timestamp=datetime.now(),
                error_message=f"验证过程出错: {str(e)}",
            )

    def get_transaction_info(self, tx_hash: str) -> dict[str, Any] | None:
        """获取交易信息

        Args:
            tx_hash: 交易哈希

        Returns:
            交易信息字典
        """
        try:
            endpoint = self.api_endpoints.get("transaction")
            if not endpoint:
                logger.error(f"未配置 {self.currency.value} 的API端点")
                return None

            url = endpoint.format(tx_hash=tx_hash)
            headers = {}

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.error(f"API请求失败: {response.status_code}")
                return None

            data = response.json()
            return self._parse_transaction_data(data)

        except Exception as e:
            logger.error(f"获取交易信息失败: {e}")
            return None

    def _get_api_endpoints(self) -> dict[str, str]:
        """获取API端点配置"""
        endpoints = {
            CryptoCurrency.BTC: {
                "transaction": "https://blockchain.info/rawtx/{tx_hash}",
                "address": "https://blockchain.info/address/{address}",
            },
            CryptoCurrency.ETH: {
                "transaction": "https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}",
                "address": "https://api.etherscan.io/api?module=account&action=balance&address={address}",
            },
            CryptoCurrency.USDT: {
                "transaction": "https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}",
                "address": "https://api.etherscan.io/api?module=account&action=tokenbalance&address={address}",
            },
            CryptoCurrency.TRX: {
                "transaction": "https://api.trongrid.io/wallet/gettransactionbyid?value={tx_hash}",
                "address": "https://api.trongrid.io/v1/accounts/{address}",
            },
            CryptoCurrency.SOL: {
                "transaction": "https://api.mainnet-beta.solana.com",
                "address": "https://api.mainnet-beta.solana.com",
            },
        }
        return endpoints.get(self.currency, {})

    def _parse_transaction_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """解析交易数据"""
        # 根据不同货币解析数据格式
        if self.currency == CryptoCurrency.BTC:
            return self._parse_btc_transaction(data)
        elif self.currency == CryptoCurrency.ETH:
            return self._parse_eth_transaction(data)
        elif self.currency == CryptoCurrency.TRX:
            return self._parse_trx_transaction(data)
        else:
            return {}

    def _parse_btc_transaction(self, data: dict[str, Any]) -> dict[str, Any]:
        """解析BTC交易"""
        outputs = data.get("out", [])
        total_amount = sum(out.get("value", 0) for out in outputs) / 1e8  # BTC精度

        return {
            "amount": total_amount,
            "to_address": outputs[0].get("addr", "") if outputs else "",
            "confirmations": data.get("block_height", 0),
            "timestamp": data.get("time", 0),
            "block_number": data.get("block_height"),
        }

    def _parse_eth_transaction(self, data: dict[str, Any]) -> dict[str, Any]:
        """解析ETH交易"""
        result = data.get("result", {})
        value = int(result.get("value", "0x0"), 16) / 1e18  # ETH精度

        return {
            "amount": value,
            "to_address": result.get("to", ""),
            "confirmations": int(result.get("blockNumber", "0x0"), 16),
            "timestamp": int(result.get("timestamp", "0x0"), 16),
            "block_number": int(result.get("blockNumber", "0x0"), 16),
        }

    def _parse_trx_transaction(self, data: dict[str, Any]) -> dict[str, Any]:
        """解析TRX交易"""
        raw_data = data.get("raw_data", {})
        contract = raw_data.get("contract", [{}])[0]
        value = contract.get("parameter", {}).get("value", {})
        amount = value.get("amount", 0) / 1e6  # TRX精度

        return {
            "amount": amount,
            "to_address": value.get("to_address", ""),
            "confirmations": data.get("confirmations", 0),
            "timestamp": data.get("timestamp", 0) // 1000,
            "block_number": data.get("blockNumber"),
        }

    def _get_min_confirmations(self) -> int:
        """获取最小确认数"""
        confirmations_map = {
            CryptoCurrency.BTC: 3,
            CryptoCurrency.ETH: 12,
            CryptoCurrency.USDT: 12,
            CryptoCurrency.USDC: 12,
            CryptoCurrency.BNB: 15,
            CryptoCurrency.TRX: 19,
            CryptoCurrency.SOL: 32,
            CryptoCurrency.ADA: 15,
            CryptoCurrency.DOGE: 6,
            CryptoCurrency.LTC: 6,
        }
        return confirmations_map.get(self.currency, 6)


class ManualPaymentVerifier(IPaymentVerifier):
    """手动验证支付 (用于离线场景)"""

    def __init__(self):
        self.verified_transactions: dict[str, PaymentVerification] = {}

    def verify_payment(
        self, tx_hash: str, expected_amount: float, recipient_address: str
    ) -> PaymentVerification:  # noqa: ARG002
        """验证支付 (从已验证列表中查找)"""
        if tx_hash in self.verified_transactions:
            return self.verified_transactions[tx_hash]

        return PaymentVerification(
            is_valid=False,
            tx_hash=tx_hash,
            amount=0,
            currency="UNKNOWN",
            confirmations=0,
            timestamp=datetime.now(),
            error_message="交易未在已验证列表中",
        )

    def get_transaction_info(self, tx_hash: str) -> dict[str, Any] | None:
        """获取交易信息"""
        if tx_hash in self.verified_transactions:
            verification = self.verified_transactions[tx_hash]
            return {
                "amount": verification.amount,
                "confirmations": verification.confirmations,
                "timestamp": verification.timestamp.timestamp(),
            }
        return None

    def add_verified_transaction(self, verification: PaymentVerification):
        """添加已验证的交易"""
        self.verified_transactions[verification.tx_hash] = verification
        logger.info(f"添加已验证交易: {verification.tx_hash}")


class CryptoPaymentManager:
    """加密货币支付管理器"""

    def __init__(self):
        self.payment_addresses: dict[str, PaymentAddress] = {}
        self.verifiers: dict[str, IPaymentVerifier] = {}

    def add_payment_address(self, payment_address: PaymentAddress):
        """添加收款地址"""
        key = payment_address.currency.value
        self.payment_addresses[key] = payment_address
        logger.info(f"添加收款地址: {key} - {payment_address.address}")

    def add_verifier(self, currency: CryptoCurrency, verifier: IPaymentVerifier):
        """添加支付验证器"""
        self.verifiers[currency.value] = verifier
        logger.info(f"添加验证器: {currency.value}")

    def verify_payment(
        self, currency: str, tx_hash: str, expected_amount: float
    ) -> PaymentVerification:
        """验证支付

        Args:
            currency: 货币类型
            tx_hash: 交易哈希
            expected_amount: 期望金额

        Returns:
            支付验证结果
        """
        # 获取收款地址
        payment_address = self.payment_addresses.get(currency)
        if not payment_address:
            return PaymentVerification(
                is_valid=False,
                tx_hash=tx_hash,
                amount=0,
                currency=currency,
                confirmations=0,
                timestamp=datetime.now(),
                error_message=f"未配置 {currency} 收款地址",
            )

        # 获取验证器
        verifier = self.verifiers.get(currency)
        if not verifier:
            return PaymentVerification(
                is_valid=False,
                tx_hash=tx_hash,
                amount=0,
                currency=currency,
                confirmations=0,
                timestamp=datetime.now(),
                error_message=f"未配置 {currency} 验证器",
            )

        # 执行验证
        return verifier.verify_payment(
            tx_hash=tx_hash,
            expected_amount=expected_amount,
            recipient_address=payment_address.address,
        )

    def get_supported_currencies(self) -> list[str]:
        """获取支持的货币列表"""
        return list(self.payment_addresses.keys())

    def get_payment_address(self, currency: str) -> str | None:
        """获取收款地址"""
        payment_address = self.payment_addresses.get(currency)
        return payment_address.address if payment_address else None


class CryptoPaymentProcessor:
    """加密货币支付处理器 - 主入口类"""

    def __init__(self):
        self.payment_manager = CryptoPaymentManager()

    def initialize(
        self, addresses: dict[str, str], networks: dict[str, str] | None = None
    ) -> None:
        """初始化支付处理器

        Args:
            addresses: 货币到地址的映射
            networks: 货币到网络的映射
        """
        networks = networks or {}

        for currency_str, address in addresses.items():
            try:
                currency = CryptoCurrency(currency_str.lower())
                network = networks.get(currency_str, "mainnet")

                payment_address = PaymentAddress(
                    currency=currency, address=address, network=network
                )

                self.payment_manager.add_payment_address(payment_address)

            except ValueError:
                logger.warning(f"不支持的货币类型: {currency_str}")

    def process_payment(
        self, currency: str, tx_hash: str, expected_amount: float
    ) -> PaymentVerification:
        """处理支付验证

        Args:
            currency: 货币类型
            tx_hash: 交易哈希
            expected_amount: 期望金额

        Returns:
            支付验证结果
        """
        return self.payment_manager.verify_payment(currency, tx_hash, expected_amount)

    def get_supported_currencies(self) -> list[str]:
        """获取支持的货币列表"""
        return self.payment_manager.get_supported_currencies()

    def get_payment_address(self, currency: str) -> str | None:
        """获取收款地址"""
        return self.payment_manager.get_payment_address(currency)
