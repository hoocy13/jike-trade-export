# 吉客云销售订单大宽表导出工具

调用吉客云开放平台 `oms.trade.fullinfoget` 接口，自动获取销售订单数据并拍平为大宽表 CSV。

## 功能特性

- **自动时间拆分** — 时间跨度超过 7 天时自动拆分为多个窗口分别查询
- **游标分页** — 使用 scrollId 游标分页，自动循环获取全部订单
- **全量字段** — 请求 API 支持的所有字段（订单级 + 货品明细级）
- **自动拍平** — 一个订单多个商品 → 多行输出，货品字段自动加前缀
- **CSV 输出** — utf-8-sig 编码，Excel 直接打开不乱码

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+
python -m venv .venv
.venv\Scripts\activate
pip install requests pandas
```

### 2. 配置

打开 `sales_order_wide_table.py`，修改顶部配置区：

```python
APP_KEY = "你的appkey"
APP_SECRET = "你的appsecret"

START_TRADE_TIME = "2026-05-29 00:00:00"   # 查询开始时间
END_TRADE_TIME = "2026-06-04 23:59:59"     # 查询结束时间
```

### 3. 运行

```bash
python sales_order_wide_table.py
```

输出文件：`sales_order_wide_table.csv`

## 输出字段说明

大宽表包含 **156 列**，分为两部分：

### 订单级字段（约 90 列）

| 分类 | 示例字段 |
|------|----------|
| 订单基础 | tradeNo, tradeId, tradeStatus, tradeStatusExplain, tradeType |
| 时间 | tradeTime, payTime, consignTime, completeTime, gmtCreate |
| 店铺/仓库 | shopName, shopId, warehouseName, warehouseId |
| 物流 | logisticName, logisticCode, mainPostid |
| 收货人 | receiverName, mobile, state, city, district, address |
| 金额 | totalFee, discountFee, payment, postFee, taxFee, couponFee |
| 备注 | buyerMemo, sellerMemo, appendMemo |
| 客户 | customerName, customerCode, customerTypeName, customerGradeName |
| 其他 | payType, payNo, invoiceType, tradeFrom, flagNames |

### 货品明细字段（前缀 `货品_`，约 60 列）

| 分类 | 示例字段 |
|------|----------|
| 商品基础 | 货品_goodsNo, 货品_goodsName, 货品_specName, 货品_barcode |
| 销售 | 货品_sellCount, 货品_sellPrice, 货品_sellTotal, 货品_unit |
| 优惠 | 货品_discountFee, 货品_shareOrderDiscountFee, 货品_goodsPlatDiscountFee |
| 其他 | 货品_isGift, 货品_isFit, 货品_cateName, 货品_brandName |

## API 签名规则

吉客云 API 签名算法（MD5）：

```
1. 将所有请求参数按 key 的 ASCII 码升序排列
2. 拼接：secret + key1value1key2value2... + secret
3. 整个字符串转小写
4. MD5 加密，结果作为 sign 参数
```

> **注意**：签名时必须将整个拼接字符串转小写再 MD5。这是官方文档未说明的规则，从官方签名工具反推得出。

## 限制说明

- **时间范围**：单次查询起止时间不超过 7 天（脚本自动拆分）
- **频率限制**：1 次/秒（脚本已设置 1.2 秒间隔）
- **分页方式**：游标分页（scrollId），不支持页码跳转
- **认证方式**：自研应用使用 AppKey + AppSecret 签名，无需 token

## 参考文档

- [吉客云开放平台](https://open.jackyun.com)
- [oms.trade.fullinfoget 接口文档](https://s.jkyun.biz/2jWhg8v)
