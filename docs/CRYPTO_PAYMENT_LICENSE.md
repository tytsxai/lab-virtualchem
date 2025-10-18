# 🔐 加密货币支付与许可证系统

## 📋 目录

- [概述](#概述)
- [系统架构](#系统架构)
- [支持的加密货币](#支持的加密货币)
- [快速开始](#快速开始)
- [用户购买流程](#用户购买流程)
- [管理员操作指南](#管理员操作指南)
- [API参考](#api参考)
- [安全性](#安全性)
- [常见问题](#常见问题)

---

## 概述

VirtualChemLab 采用**加密货币支付 + 离线许可证**的授权方式:

- ✅ **纯加密货币支付** - 仅支持数字货币购买
- ✅ **离线验证** - 无需联网即可验证许可证
- ✅ **设备绑定** - 基于硬件ID的设备授权
- ✅ **多币种支持** - BTC、ETH、USDT、TRX等主流币种
- ✅ **自动化流程** - 可选的自动许可证生成
- ✅ **安全可靠** - 数字签名防篡改

### 核心特性

| 特性 | 说明 |
|------|------|
| **支付方式** | 仅限加密货币 (BTC/ETH/USDT/TRX等) |
| **验证模式** | 离线验证,无需联网 |
| **设备绑定** | 基于机器ID,防止盗版 |
| **许可证类型** | 试用/个人/教育/商业/企业 |
| **有效期** | 可配置 (默认365天) |
| **设备数量** | 根据许可证类型限制 |

---

## 系统架构

```
┌─────────────────────────────────────────────┐
│           用户购买流程                       │
│                                             │
│  1. 选择许可证类型                          │
│  2. 获取收款地址                            │
│  3. 发送加密货币                            │
│  4. 提交交易哈希                            │
│  5. 管理员验证支付                          │
│  6. 生成并发送许可证                        │
│  7. 用户激活许可证                          │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│           离线许可证验证                     │
│                                             │
│  • 加载许可证文件                           │
│  • 验证数字签名                             │
│  • 检查设备绑定                             │
│  • 检查过期时间                             │
│  • 检查功能权限                             │
└─────────────────────────────────────────────┘
```

### 核心模块

1. **license_manager.py** - 许可证管理核心
   - 许可证生成
   - 签名验证
   - 设备绑定
   - 过期检查

2. **crypto_payment.py** - 支付验证
   - 多币种支持
   - 区块链API验证
   - 手动验证模式
   - 交易确认检查

3. **license_middleware.py** - 中间件集成
   - 启动时验证
   - 功能权限检查
   - UI辅助工具

4. **license_generator.py** - 管理工具
   - 交互式生成许可证
   - 批量生成
   - 支付验证
   - 许可证激活

---

## 支持的加密货币

| 币种 | 名称 | 网络 | 最小确认数 | 状态 |
|------|------|------|------------|------|
| **BTC** | 比特币 | Bitcoin Mainnet | 3 | ✅ 已支持 |
| **ETH** | 以太坊 | Ethereum Mainnet | 12 | ✅ 已支持 |
| **USDT** | 泰达币 | Ethereum (ERC20) | 12 | ✅ 已支持 |
| **USDC** | USD Coin | Ethereum (ERC20) | 12 | 🔧 可配置 |
| **TRX** | 波场 | Tron Mainnet | 19 | ✅ 已支持 |
| **BNB** | 币安币 | BSC | 15 | 🔧 可配置 |
| **SOL** | Solana | Solana Mainnet | 32 | 🔧 可配置 |
| **ADA** | Cardano | Cardano Mainnet | 15 | 🔧 可配置 |
| **DOGE** | 狗狗币 | Dogecoin Mainnet | 6 | 🔧 可配置 |
| **LTC** | 莱特币 | Litecoin Mainnet | 6 | 🔧 可配置 |

### 价格体系

| 许可证类型 | USD | BTC | ETH | USDT | 有效期 |
|-----------|-----|-----|-----|------|--------|
| **试用版** | $0 | - | - | - | 7天 |
| **个人版** | $99 | 0.0025 | 0.04 | 99 | 365天 |
| **教育版** | $299 | 0.0075 | 0.12 | 299 | 365天 |
| **商业版** | $999 | 0.025 | 0.40 | 999 | 365天 |
| **企业版** | $2,999 | 0.075 | 1.20 | 2999 | 365天 |

---

## 快速开始

### 1. 配置收款地址

编辑 `config/crypto_payment_config.json`:

```json
{
  "payment": {
    "supported_currencies": [
      {
        "code": "BTC",
        "address": "您的BTC收款地址",
        "enabled": true
      },
      {
        "code": "ETH",
        "address": "您的ETH收款地址",
        "enabled": true
      }
    ]
  }
}
```

### 2. 配置密钥

修改配置文件中的密钥 (⚠️ 生产环境必须修改):

```json
{
  "license": {
    "secret_key": "您的安全密钥_至少32位_随机字符串"
  }
}
```

### 3. 获取机器ID

```bash
# 用户在其设备上运行
python tools/license_generator.py machine-id
```

输出示例:

```
机器ID: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### 4. 生成许可证

```bash
# 交互式生成
python tools/license_generator.py generate

# 或批量生成
python tools/license_generator.py generate --batch config/licenses.json
```

### 5. 激活许可证

```bash
# 用户激活许可证
python tools/license_generator.py activate data/license.json
```

### 6. 检查许可证状态

```bash
python tools/license_generator.py check
```

---

## 用户购买流程

### 步骤 1: 选择许可证类型

用户访问您的销售页面,选择合适的许可证:

- 个人版 - 适合个人学习
- 教育版 - 适合学校使用
- 商业版 - 适合企业使用
- 企业版 - 无限制企业部署

### 步骤 2: 获取设备ID

用户下载并运行工具获取其机器ID:

```bash
python tools/license_generator.py machine-id
```

### 步骤 3: 填写订单信息

用户提供:

- 邮箱地址
- 机器ID
- 选择的许可证类型
- 支付币种

### 步骤 4: 支付加密货币

系统显示收款地址和金额,用户发送加密货币到指定地址。

### 步骤 5: 提交交易哈希

支付完成后,用户提交交易哈希 (TX Hash)。

### 步骤 6: 等待验证

管理员验证支付后生成许可证 (可自动化)。

### 步骤 7: 激活许可证

用户收到许可证文件,放置到 `data/license.json` 并激活。

---

## 管理员操作指南

### 验证支付

```bash
# 验证单笔支付
python tools/license_generator.py verify \
  <交易哈希> \
  <币种> \
  <金额>

# 示例
python tools/license_generator.py verify \
  0x1234abcd... \
  ETH \
  0.04
```

### 生成许可证

#### 方式1: 交互式生成

```bash
python tools/license_generator.py generate
```

按提示输入:

- 用户ID
- 邮箱
- 机器ID
- 许可证类型
- 支付信息
- 有效期

#### 方式2: 批量生成

创建 `licenses.json`:

```json
{
  "licenses": [
    {
      "user_id": "user001",
      "email": "user@example.com",
      "machine_id": "a1b2c3d4...",
      "license_type": "personal",
      "validity_days": 365,
      "payment": {
        "currency": "BTC",
        "tx_hash": "0x1234...",
        "amount": 0.0025,
        "recipient_address": "1A1zP1eP...",
        "timestamp": "2025-10-06T10:00:00"
      }
    }
  ]
}
```

然后运行:

```bash
python tools/license_generator.py generate --batch licenses.json
```

### 启动Webhook服务器 (可选)

自动接收和处理支付通知:

```bash
python tools/payment_webhook_server.py --host 0.0.0.0 --port 8888
```

### 撤销许可证

在代码中调用:

```python
from src.core.license_manager import LicenseManager
from pathlib import Path

license_manager = LicenseManager(
    secret_key="YOUR_SECRET",
    license_file=Path("data/license.json")
)

# 撤销许可证
license_manager.revoke_license("许可证密钥")
```

---

## API参考

### 许可证管理器

```python
from src.core.license_manager import (
    LicenseManager,
    License,
    LicenseType,
    CryptoPayment,
    get_machine_id
)

# 创建管理器
manager = LicenseManager(
    secret_key="YOUR_SECRET_KEY",
    license_file=Path("data/license.json")
)

# 生成许可证
payment = CryptoPayment(
    currency="BTC",
    tx_hash="0x1234...",
    amount=0.0025,
    recipient_address="1A1zP1eP...",
    timestamp=datetime.now()
)

license = manager.generate_license(
    user_id="user001",
    email="user@example.com",
    machine_id=get_machine_id(),
    license_type=LicenseType.PERSONAL,
    payment=payment,
    validity_days=365
)

# 保存许可证
manager.save_license(license)

# 加载许可证
license = manager.load_license()

# 验证许可证
status, error = manager.validate_license(license, get_machine_id())

# 激活许可证
success, error = manager.activate_license(license, get_machine_id())
```

### 支付验证

```python
from src.core.crypto_payment import (
    CryptoPaymentManager,
    BlockchainAPIVerifier,
    CryptoCurrency,
    PaymentAddress
)

# 创建支付管理器
manager = CryptoPaymentManager()

# 添加收款地址
manager.add_payment_address(PaymentAddress(
    currency=CryptoCurrency.BTC,
    address="1A1zP1eP...",
    min_confirmations=3
))

# 添加验证器
verifier = BlockchainAPIVerifier(CryptoCurrency.BTC, api_key="...")
manager.add_verifier(CryptoCurrency.BTC, verifier)

# 验证支付
verification = manager.verify_payment(
    currency="bitcoin",
    tx_hash="0x1234...",
    expected_amount=0.0025
)

if verification.is_valid:
    print("支付验证通过")
else:
    print(f"验证失败: {verification.error_message}")
```

### 许可证中间件

```python
from src.core.license_middleware import LicenseMiddleware, LicenseGuard
from src.core.license_manager import LicenseManager
from pathlib import Path

# 创建中间件
license_manager = LicenseManager(
    secret_key="YOUR_SECRET",
    license_file=Path("data/license.json")
)

middleware = LicenseMiddleware(
    license_manager=license_manager,
    strict_mode=True,
    trial_days=7
)

# 使用装饰器检查功能
guard = LicenseGuard(license_manager)

@guard.require_feature("api_access")
def advanced_feature():
    print("此功能需要商业版或企业版许可证")

# 检查是否有某功能
if middleware.has_feature("data_export"):
    print("可使用数据导出功能")
```

---

## 安全性

### 密钥管理

⚠️ **重要**: 生产环境必须修改默认密钥

```bash
# 生成随机密钥
python -c "import secrets; print(secrets.token_hex(32))"
```

将生成的密钥更新到配置文件:

```json
{
  "license": {
    "secret_key": "生成的随机密钥"
  }
}
```

### 收款地址安全

- ✅ 使用独立的收款地址
- ✅ 定期更换收款地址
- ✅ 使用硬件钱包保护私钥
- ✅ 启用多签验证 (企业级)

### 许可证文件保护

- ✅ 许可证文件包含数字签名
- ✅ 设备绑定防止复制
- ✅ 支持许可证撤销
- ✅ 定期检查许可证状态

### 通信安全

- ✅ Webhook使用HTTPS
- ✅ 验证webhook签名
- ✅ IP白名单限制
- ✅ 请求频率限制

---

## 常见问题

### Q1: 支持哪些加密货币?

**A**: 目前支持 BTC、ETH、USDT、TRX 等主流币种,可通过配置文件启用更多币种。

### Q2: 许可证可以转移到其他设备吗?

**A**: 许可证绑定到特定设备的机器ID。如需转移,请联系管理员重新生成许可证。

### Q3: 许可证过期后会怎样?

**A**:

- 严格模式: 应用拒绝启动
- 非严格模式: 显示警告但允许使用
- 可配置宽限期 (默认7天)

### Q4: 如何验证支付?

**A**:

- **在线验证**: 使用区块链API自动验证
- **离线验证**: 管理员手动验证后添加到已验证列表

### Q5: 是否支持退款?

**A**: 加密货币交易不可逆,建议提供试用版让用户测试。

### Q6: 如何处理价格波动?

**A**:

- 使用稳定币 (USDT/USDC)
- 或在接受支付时实时计算当前价格
- 允许1-2%的价格容差

### Q7: 许可证文件丢失怎么办?

**A**: 管理员保留所有已生成的许可证备份,可重新发送。

### Q8: 是否支持自动续费?

**A**: 当前版本需要手动续费。自动续费功能计划在未来版本实现。

---

## 配置示例

### 完整配置文件

参考 `config/crypto_payment_config.json`:

```json
{
  "payment": {
    "enabled": true,
    "mode": "offline",
    "supported_currencies": [...],
    "pricing": {...}
  },
  "license": {
    "secret_key": "YOUR_SECRET_KEY",
    "strict_mode": true,
    "trial_days": 7
  },
  "blockchain_api": {
    "eth": {
      "api_key": "YOUR_ETHERSCAN_API_KEY"
    }
  },
  "webhook": {
    "enabled": false,
    "port": 8888
  }
}
```

### 环境变量

```bash
# .env 文件
LICENSE_SECRET_KEY=your_secret_key_here
ETHERSCAN_API_KEY=your_etherscan_api_key
BTC_RECEIVE_ADDRESS=your_btc_address
ETH_RECEIVE_ADDRESS=your_eth_address
```

---

## 最佳实践

### 1. 安全配置

- 更改默认密钥
- 使用环境变量存储敏感信息
- 启用HTTPS (webhook)
- 定期轮换密钥

### 2. 用户体验

- 提供详细的购买指南
- 及时发送许可证
- 提供技术支持联系方式
- 考虑提供试用版

### 3. 运营管理

- 保留支付记录
- 备份许可证文件
- 监控支付状态
- 定期审计

### 4. 自动化

- 使用webhook自动处理支付
- 自动生成和发送许可证
- 自动提醒即将过期的许可证

---

## 技术支持

如有问题,请联系:

- 📧 邮箱: <support@virtualchemlab.com>
- 💬 Telegram: @VirtualChemLabSupport
- 📝 文档: <https://docs.virtualchemlab.com>

---

**最后更新**: 2025年10月6日
**版本**: v1.0.0
