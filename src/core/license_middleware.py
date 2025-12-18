"""
许可证验证中间件

集成到应用启动流程中的许可证检查
"""

import logging
from collections.abc import Callable
from typing import Any

from src.core.license_manager import (
    License,
    LicenseManager,
    LicenseStatus,
    get_machine_id,
)
from src.core.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


class LicenseException(Exception):
    """许可证异常"""

    pass


class LicenseExpiredException(LicenseException):
    """许可证过期异常"""

    pass


class LicenseInvalidException(LicenseException):
    """许可证无效异常"""

    pass


class LicenseNotActivatedException(LicenseException):
    """许可证未激活异常"""

    pass


class LicenseMiddleware(Middleware):
    """许可证验证中间件"""

    def __init__(
        self,
        license_manager: LicenseManager,
        strict_mode: bool = True,
        trial_days: int = 7,
    ):
        """初始化

        Args:
            license_manager: 许可证管理器
            strict_mode: 严格模式 (如果为False,许可证无效时仅警告)
            trial_days: 试用天数 (无许可证时)
        """
        self.license_manager = license_manager
        self.strict_mode = strict_mode
        self.trial_days = trial_days
        self._current_license: License | None = None
        self._license_checked = False

    async def invoke(
        self, context: MiddlewareContext, next_middleware: Callable
    ) -> Any:
        """调用中间件

        Args:
            context: 中间件上下文
            next_middleware: 下一个中间件

        Returns:
            处理结果
        """
        # 只在第一次调用时检查许可证
        if not self._license_checked:
            self._check_license()
            self._license_checked = True

            # 将许可证信息存入上下文
            if self._current_license:
                context.set("license", self._current_license)
                context.set("license_valid", True)
            else:
                context.set("license_valid", False)

        # 继续执行下一个中间件
        return await next_middleware()

    async def process(self, _context: Any, next_middleware: Callable) -> Any:
        """兼容旧版本的process方法 (已废弃,请使用invoke)

        Args:
            context: 上下文对象
            next_middleware: 下一个中间件

        Returns:
            处理结果
        """
        # 只在第一次调用时检查许可证
        if not self._license_checked:
            self._check_license()
            self._license_checked = True

        # 继续执行下一个中间件
        return await next_middleware()

    def _check_license(self):
        """检查许可证"""
        try:
            # 加载许可证
            license_obj = self.license_manager.load_license()

            if not license_obj:
                logger.warning("未找到许可证文件")
                self._handle_no_license()
                return

            # 验证许可证
            machine_id = get_machine_id()
            status, error_msg = self.license_manager.validate_license(
                license_obj, machine_id
            )

            if status == LicenseStatus.VALID:
                self._current_license = license_obj
                self._log_license_info(license_obj)
                logger.info("✅ 许可证验证通过")

            elif status == LicenseStatus.EXPIRED:
                logger.error(f"❌ 许可证已过期: {error_msg}")
                if self.strict_mode:
                    raise LicenseExpiredException(error_msg)

            elif status == LicenseStatus.NOT_ACTIVATED:
                logger.warning(f"⚠️ 许可证未激活: {error_msg}")
                if self.strict_mode:
                    raise LicenseNotActivatedException(error_msg)

            elif status == LicenseStatus.INVALID:
                logger.error(f"❌ 许可证无效: {error_msg}")
                if self.strict_mode:
                    raise LicenseInvalidException(error_msg)

            elif status == LicenseStatus.REVOKED:
                logger.error(f"❌ 许可证已被撤销: {error_msg}")
                if self.strict_mode:
                    raise LicenseInvalidException(error_msg)

        except LicenseException:
            raise
        except Exception as e:
            logger.error(f"许可证检查失败: {e}")
            if self.strict_mode:
                raise LicenseException(f"许可证检查失败: {e}") from e

    def _handle_no_license(self):
        """处理无许可证情况"""
        if self.strict_mode:
            logger.error("❌ 未找到有效许可证")
            logger.info(f"💡 提示: 您可以使用 {self.trial_days} 天试用期")
            raise LicenseException(
                f"未找到有效许可证。请购买许可证或激活试用版。\n试用天数: {self.trial_days} 天"
            )
        else:
            logger.warning(f"⚠️ 未找到许可证,使用试用模式 ({self.trial_days} 天)")

    def _log_license_info(self, license_obj: License):
        """记录许可证信息"""
        info = self.license_manager.get_license_info(license_obj)

        logger.info("=" * 60)
        logger.info("许可证信息:")
        logger.info(f"  类型: {info['license_type']}")
        logger.info(f"  用户: {info['email']}")
        logger.info(f"  签发日期: {info['issue_date']}")
        logger.info(f"  过期日期: {info['expiry_date']}")
        logger.info(f"  剩余天数: {info['days_remaining']} 天")
        logger.info(f"  激活状态: {'已激活' if info['is_activated'] else '未激活'}")
        logger.info(f"  功能列表: {', '.join(info['features'])}")
        logger.info(
            f"  支付信息: {info['payment']['currency']} - {info['payment']['amount']}"
        )
        logger.info("=" * 60)

    def get_current_license(self) -> License | None:
        """获取当前许可证"""
        return self._current_license

    def has_feature(self, feature: str) -> bool:
        """检查是否有某个功能

        Args:
            feature: 功能名称

        Returns:
            是否有该功能
        """
        if not self._current_license:
            return False
        return feature in self._current_license.features


class LicenseGuard:
    """许可证守护 (用于装饰器)"""

    def __init__(self, license_manager: LicenseManager):
        self.license_manager = license_manager
        self._current_license: License | None = None

    def require_license(self, func: Callable) -> Callable:
        """要求有效许可证的装饰器"""

        def wrapper(*args, **kwargs):
            if not self._validate_license():
                raise LicenseException("需要有效的许可证才能使用此功能")
            return func(*args, **kwargs)

        return wrapper

    def require_feature(self, feature: str) -> Callable:
        """要求特定功能的装饰器"""

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                if not self._validate_license():
                    raise LicenseException("需要有效的许可证")

                if feature not in self._current_license.features:
                    raise LicenseException(
                        f"当前许可证不包含 '{feature}' 功能,请升级许可证"
                    )

                return func(*args, **kwargs)

            return wrapper

        return decorator

    def _validate_license(self) -> bool:
        """验证许可证"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return False

        machine_id = get_machine_id()
        status, _ = self.license_manager.validate_license(license_obj, machine_id)

        if status == LicenseStatus.VALID:
            self._current_license = license_obj
            return True

        return False


class LicenseUIHelper:
    """许可证UI辅助类"""

    def __init__(self, license_manager: LicenseManager):
        self.license_manager = license_manager

    def get_license_status_message(self) -> str:
        """获取许可证状态消息"""
        license_obj = self.license_manager.load_license()

        if not license_obj:
            return "❌ 未找到许可证\n\n请购买许可证或激活试用版"

        machine_id = get_machine_id()
        status, error_msg = self.license_manager.validate_license(
            license_obj, machine_id
        )

        if status == LicenseStatus.VALID:
            info = self.license_manager.get_license_info(license_obj)
            days = info["days_remaining"]

            if days < 30:
                icon = "⚠️"
                warning = f"\n\n警告: 许可证将在 {days} 天后过期"
            else:
                icon = "✅"
                warning = ""

            return (
                f"{icon} 许可证有效\n\n"
                f"类型: {info['license_type']}\n"
                f"用户: {info['email']}\n"
                f"剩余天数: {days} 天"
                f"{warning}"
            )

        elif status == LicenseStatus.EXPIRED:
            return f"❌ 许可证已过期\n\n{error_msg}\n\n请续费许可证"

        elif status == LicenseStatus.NOT_ACTIVATED:
            return f"⚠️ 许可证未激活\n\n{error_msg}\n\n请激活许可证"

        elif status == LicenseStatus.INVALID:
            return f"❌ 许可证无效\n\n{error_msg}\n\n请检查许可证文件"

        elif status == LicenseStatus.REVOKED:
            return f"❌ 许可证已被撤销\n\n{error_msg}\n\n请联系客服"

        return "❓ 未知状态"

    def show_activation_dialog(self) -> bool:
        """显示激活对话框

        当前实现为“离线激活”：
        - 仅对本机已存在的许可证文件执行激活（写入 activated_at/is_activated 并重新签名）
        - 不包含联网拉取/兑换许可证的逻辑
        - 若本机不存在许可证文件，或输入密钥与本机许可证不匹配，则激活失败

        Returns:
            是否激活成功
        """
        try:
            from PySide6.QtWidgets import (
                QDialog,
                QLabel,
                QLineEdit,
                QMessageBox,  # noqa: F401
                QPushButton,
                QVBoxLayout,
            )

            class ActivationDialog(QDialog):
                def __init__(self):
                    super().__init__()
                    self.setWindowTitle("激活许可证")
                    self.setup_ui()

                def setup_ui(self):
                    layout = QVBoxLayout()

                    # 标题
                    title = QLabel("请输入许可证密钥")
                    layout.addWidget(title)

                    # 输入框
                    self.key_input = QLineEdit()
                    self.key_input.setPlaceholderText(
                        "XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
                    )
                    layout.addWidget(self.key_input)

                    # 按钮
                    btn_activate = QPushButton("激活")
                    btn_activate.clicked.connect(self.accept)
                    layout.addWidget(btn_activate)

                    btn_cancel = QPushButton("取消")
                    btn_cancel.clicked.connect(self.reject)
                    layout.addWidget(btn_cancel)

                    self.setLayout(layout)

                def get_key(self) -> str:
                    return self.key_input.text()

            dialog = ActivationDialog()
            if dialog.exec() == QDialog.Accepted:
                license_key = dialog.get_key()

                # 验证输入
                if not license_key or not license_key.strip():
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(None, "错误", "请输入有效的许可证密钥")
                    return False

                try:
                    license_obj = self.license_manager.load_license()
                    if not license_obj:
                        from PySide6.QtWidgets import QMessageBox

                        QMessageBox.warning(
                            None,
                            "缺少许可证文件",
                            "未找到许可证文件。请先导入/安装许可证文件后再执行激活。",
                        )
                        return False

                    key = license_key.strip()
                    if key != license_obj.license_key:
                        from PySide6.QtWidgets import QMessageBox

                        QMessageBox.warning(
                            None,
                            "密钥不匹配",
                            "输入的许可证密钥与本机许可证文件不匹配，请检查是否选择了正确的许可证文件。",
                        )
                        return False

                    machine_id = get_machine_id()
                    success, error_msg = self.license_manager.activate_license(
                        license_obj, machine_id
                    )

                    if success:
                        self.license_manager.save_license(license_obj)
                        from PySide6.QtWidgets import QMessageBox

                        QMessageBox.information(None, "成功", "许可证激活成功！")
                        logger.info("许可证激活成功")
                        return True
                    else:
                        from PySide6.QtWidgets import QMessageBox

                        QMessageBox.warning(
                            None,
                            "失败",
                            f"许可证激活失败：{error_msg or '请检查许可证状态与设备绑定信息'}",
                        )
                        logger.warning("许可证激活失败")
                        return False

                except Exception as e:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.critical(None, "错误", f"激活过程出错: {str(e)}")
                    logger.error(f"许可证激活异常: {e}", exc_info=True)
                    return False

            return False

        except ImportError:
            logger.warning("PySide6未安装,无法显示UI对话框")
            return False

    def get_purchase_info(self) -> dict[str, Any]:
        """获取购买信息"""

        return {
            "supported_currencies": [
                {
                    "code": "BTC",
                    "name": "比特币",
                    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                },
                {
                    "code": "ETH",
                    "name": "以太坊",
                    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                },
                {
                    "code": "USDT",
                    "name": "泰达币",
                    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                },
                {
                    "code": "TRX",
                    "name": "波场",
                    "address": "TYASr5UV6HEcXatwdFQfmLVUqQQQMUxHLS",
                },
            ],
            "prices": {
                "personal": {"usd": 99, "btc": 0.0025, "eth": 0.04},
                "education": {"usd": 299, "btc": 0.0075, "eth": 0.12},
                "commercial": {"usd": 999, "btc": 0.025, "eth": 0.40},
                "enterprise": {"usd": 2999, "btc": 0.075, "eth": 1.20},
            },
            "contact": {
                "email": "sales@virtualchemlab.com",
                "telegram": "@VirtualChemLabSupport",
            },
        }
