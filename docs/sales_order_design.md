# 销售单明细宽表设计文档

> **关联脚本**：`scripts/sales_order.py`（API 数据获取 + CSV 导出 + MySQL 入库）
> **分仓库存脚本**：`scripts/warehouse_stock.py`（独立脚本，见 CLAUDE.md）

**表名**：`dwd_sales_order_detail`
**粒度**：一行 = 一个销售单下的一个货品明细
**主键**：`trade_no` + `sub_trade_id`
**数据库**：MySQL 本地数据库

---

## 零、数据库连接配置

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "091633",
    "database": "dw_ods",       # 待创建
    "charset":  "utf8mb4",
}
```

依赖安装：

```bash
pip install pymysql
```

---

## 一、字段设计表

### 1.1 订单维度字段

| # | 英文字段名 | 中文字段名 | 数据类型 | 来源 API 字段 | 计算逻辑 | 备注 |
|---|-----------|-----------|---------|-------------|---------|------|
| 1 | `trade_no` | 订单编号 | VARCHAR(64) | `tradeNo` | 直取 | 主键之一，API 必返 |
| 2 | `trade_id` | 订单ID | VARCHAR(64) | `tradeId` | 直取 | API 内部 ID |
| 3 | `online_order_no` | 网店订单号 | VARCHAR(128) | 优先 `goodsDetail.sourceTradeNo`，回退 `onlineTradeNo` | COALESCE 逻辑 | 详见"歧义字段处理" |
| 4 | `source_trade_no` | 来源订单号(订单级) | VARCHAR(128) | `sourceTradeNo` | 直取 | 订单级来源单号，保留对照 |
| 5 | `online_trade_no` | 网店订单号(订单级) | VARCHAR(128) | `onlineTradeNo` | 直取 | 订单级网店单号，保留对照 |
| 6 | `shop_name` | 渠道/店铺名称 | VARCHAR(128) | `shopName` | 直取 | 销售渠道 |
| 7 | `shop_id` | 渠道ID | VARCHAR(64) | `shopId` | 直取 | |
| 8 | `shop_code` | 渠道编码 | VARCHAR(64) | `shopCode` | 直取 | 注意：API 字段名实际为 `shopcode`（全小写），需在代码中适配 |
| 9 | `logistics_name` | 物流公司 | VARCHAR(128) | `logisticName` | 直取 | |
| 10 | `logistics_no` | 物流单号 | VARCHAR(128) | `mainPostid` | 直取 | |
| 11 | `warehouse_name` | 发货仓库(订单级) | VARCHAR(128) | `warehouseName` | 直取 | 订单级仓库，保留对照 |
| 12 | `display_warehouse_name` | 展示用发货仓库 | VARCHAR(128) | 优先 `goodsDetail.inventoryWarehouseName`，回退 `warehouseName` | COALESCE 逻辑 | 详见"歧义字段处理" |
| 13 | `customer_code` | 客户编号 | VARCHAR(64) | `customerCode` | 直取 | |
| 14 | `customer_name` | 客户名称 | VARCHAR(128) | `customerName` | 直取 | |
| 15 | `trade_status` | 订单状态 | INT | `tradeStatus` | 直取 | 数值型，含义待确认 |
| 16 | `trade_status_explain` | 订单状态描述 | VARCHAR(64) | `tradeStatusExplain` | 直取 | |
| 17 | `trade_type` | 订单类型 | VARCHAR(32) | `tradeType` | 直取 | |
| 18 | `order_time` | 下单时间 | DATETIME | `tradeTime` | 直取 | |
| 19 | `pay_time` | 付款时间 | DATETIME | `payTime` | 直取 | |
| 20 | `consign_time` | 发货时间(订单级) | DATETIME | `consignTime` | 直取 | 第一版作为货品级发货时间使用 |
| 21 | `last_ship_time` | 承诺发货时间 | DATETIME | `lastShipTime` | 直取 | |
| 22 | `gmt_create` | 创建时间 | DATETIME | `gmtCreate` | 直取 | 系统创建时间 |
| 23 | `gmt_modified` | 最后修改时间 | DATETIME | `gmtModified` | 直取 | |

### 1.2 货品明细字段

| # | 英文字段名 | 中文字段名 | 数据类型 | 来源 API 字段 | 计算逻辑 | 备注 |
|---|-----------|-----------|---------|-------------|---------|------|
| 24 | `sub_trade_id` | 子订单ID | VARCHAR(64) | `goodsDetail.subTradeId` | 直取 | 主键之一 |
| 25 | `goods_no` | 货品编号 | VARCHAR(64) | `goodsDetail.goodsNo` | 直取 | |
| 26 | `goods_name` | 货品名称 | VARCHAR(256) | `goodsDetail.goodsName` | 直取 | |
| 27 | `sku_no` | 规格编号 | VARCHAR(64) | `goodsDetail.skuNo` | 直取 | |
| 28 | `spec_name` | 规格名称 | VARCHAR(128) | `goodsDetail.specName` | 直取 | |
| 29 | `barcode` | 货品条码 | VARCHAR(64) | `goodsDetail.barcode` | 直取 | |
| 30 | `brand_name` | 品牌名称 | VARCHAR(128) | `goodsDetail.brandName` | 直取 | |
| 31 | `brand_id` | 品牌ID | VARCHAR(64) | `goodsDetail.brandId` | 直取 | |
| 32 | `trade_goods_name` | 交易名称(网店商品名) | VARCHAR(256) | `goodsDetail.tradeGoodsName` | 直取 | 平台侧商品名称 |
| 33 | `plat_goods_id` | 商品链接ID | VARCHAR(128) | `goodsDetail.platGoodsId` | 直取 | 第一版使用，后续可补 URL |
| 34 | `inventory_warehouse_name` | 货品仓库名称 | VARCHAR(128) | `goodsDetail.inventoryWarehouseName` | 直取 | 货品级仓库，优先用于展示 |
| 35 | `refund_status` | 退款状态 | VARCHAR(32) | `goodsDetail.refundStatus` | 直取 | 保留字段，不自动冲减金额 |
| 36 | `is_gift` | 是否赠品 | VARCHAR(8) | `goodsDetail.isGift` | 直取 | 保留字段，待确认口径 |
| 37 | `is_fit` | 是否组合装 | VARCHAR(8) | `goodsDetail.isFit` | 直取 | 保留字段，待确认口径 |
| 38 | `source_sub_trade_no` | 来源子订单号 | VARCHAR(128) | `goodsDetail.sourceSubtradeNo` | 直取 | |
| 39 | `actual_send_count` | 实际发货数量 | DECIMAL(18,4) | `goodsDetail.actualSendCount` | 直取 | 备选发货口径数量 |

### 1.3 金额字段

| # | 英文字段名 | 中文字段名 | 数据类型 | 来源 API 字段 | 计算逻辑 | 备注 |
|---|-----------|-----------|---------|-------------|---------|------|
| 40 | `sales_qty` | 销售数量 | DECIMAL(18,4) | `goodsDetail.sellCount` | 直取 | 主口径：下单数量 |
| 41 | `sales_price` | 单价 | DECIMAL(18,4) | `goodsDetail.sellPrice` | 直取 | |
| 42 | `discount_fee` | 优惠/折扣 | DECIMAL(18,4) | `goodsDetail.discountFee` | 直取 | 货品级优惠 |
| 43 | `sales_amount` | 金额(销售金额) | DECIMAL(18,4) | `goodsDetail.sellTotal` | 直取 | 第一版主口径 |
| 44 | `cost_amount` | 货品成本 | DECIMAL(18,4) | `goodsDetail.cost` | 直取 | 口径待与成本负责人确认 |
| 45 | `share_favourable_fee` | 分摊金额 | DECIMAL(18,4) | `goodsDetail.shareFavourableFee` | 直取 | 优惠分摊金额 |
| 46 | `share_favourable_after_fee` | 分摊后金额 | DECIMAL(18,4) | 优先 `goodsDetail.shareFavourableAfterFee`，回退 `goodsDetail.divideSellTotal`，再回退 `goodsDetail.sellTotal` | COALESCE 三级回退 | 详见"歧义字段处理" |
| 47 | `divide_sell_total` | 货品分摊销售总额 | DECIMAL(18,4) | `goodsDetail.divideSellTotal` | 直取 | 保留原始值对照 |
| 48 | `share_order_discount_fee` | 货品分摊订单优惠 | DECIMAL(18,4) | `goodsDetail.shareOrderDiscountFee` | 直取 | 保留原始值对照 |
| 49 | `allocated_unit_price` | 分摊后单价 | DECIMAL(18,4) | 自算 | `share_favourable_after_fee / NULLIF(sales_qty, 0)` | 数量为 0 或空时置 NULL |
| 50 | `cost_note` | 成本口径说明 | VARCHAR(64) | — | 固定写入 | 标注成本类型，如"待确认" |

### 1.4 自算指标字段

| # | 英文字段名 | 中文字段名 | 数据类型 | 来源 API 字段 | 计算逻辑 | 备注 |
|---|-----------|-----------|---------|-------------|---------|------|
| 51 | `gross_profit_amount` | 毛利额 | DECIMAL(18,4) | 自算 | `share_favourable_after_fee - cost_amount` | 负值表示亏损 |
| 52 | `gross_profit_rate` | 毛利率 | DECIMAL(10,6) | 自算 | `gross_profit_amount / NULLIF(share_favourable_after_fee, 0)` | 分母为 0 或空时置 NULL；存储为小数，展示时 ×100% |
| 53 | `api_gross_profit` | API毛利 | DECIMAL(18,4) | `grossProfit`（订单级） | 直取 | 保留用于对照自算值 |

### 1.5 数据管理字段

| # | 英文字段名 | 中文字段名 | 数据类型 | 来源 API 字段 | 计算逻辑 | 备注 |
|---|-----------|-----------|---------|-------------|---------|------|
| 54 | `dw_insert_time` | 数据入库时间 | DATETIME | 系统 | `CURRENT_TIMESTAMP` | ETL 时间戳 |
| 55 | `data_date` | 数据日期 | DATE | 系统 | 取数日期分区 | 便于增量更新 |

---

## 二、API fields 最终清单

### 2.1 必须字段（当前已在脚本中）

```
# 订单级
tradeNo, tradeId, tradeStatus, tradeStatusExplain, tradeType,
tradeTime, payTime, consignTime, lastShipTime,
gmtCreate, gmtModified,
onlineTradeNo, sourceTradeNo,
shopId, shopCode, shopName,
logisticName, mainPostid, warehouseName,
customerCode, customerName, grossProfit, isDelete

# 货品明细级
goodsDetail.subTradeId, goodsDetail.sourceTradeNo, goodsDetail.sourceSubtradeNo,
goodsDetail.goodsNo, goodsDetail.goodsName, goodsDetail.specName, goodsDetail.skuNo,
goodsDetail.barcode,
goodsDetail.sellCount, goodsDetail.sellPrice, goodsDetail.sellTotal,
goodsDetail.cost,
goodsDetail.discountFee,
goodsDetail.shareFavourableFee, goodsDetail.shareFavourableAfterFee,
goodsDetail.divideSellTotal, goodsDetail.shareOrderDiscountFee,
goodsDetail.brandId, goodsDetail.brandName,
goodsDetail.tradeGoodsName, goodsDetail.platGoodsId,
goodsDetail.inventoryWarehouseName,
goodsDetail.refundStatus, goodsDetail.isGift, goodsDetail.isFit,
goodsDetail.actualSendCount
```

### 2.2 建议补充字段（当前脚本已有但设计表未使用，按需启用）

```
# 以下字段已在脚本 FIELDS 中，建议保留以备扩展
tradeOrderPayList          # 支付明细（如需多支付方式分析）
packageDetail              # 包裹明细（如需货品级发货时间）
goodsDetail.cateName       # 商品分类（如需品类分析）
goodsDetail.unit           # 单位
goodsDetail.tradeGoodsSpec # 交易规格
goodsDetail.isPresell      # 是否预售
goodsDetail.isPlatGift     # 平台赠品标识
```

---

## 三、指标口径说明

### 3.1 销售数量

| 口径 | 字段 | 说明 |
|------|------|------|
| **下单口径（默认）** | `goodsDetail.sellCount` | 客户下单数量，第一版使用 |
| **发货口径（备选）** | `goodsDetail.actualSendCount` | 实际发货数量，可用于发货分析 |

### 3.2 销售金额

| 口径 | 字段 | 说明 |
|------|------|------|
| **原始金额** | `goodsDetail.sellTotal` | 货品销售原价 × 数量，第一版主口径 |
| **分摊后金额（推荐）** | 优先 `shareFavourableAfterFee` → `divideSellTotal` → `sellTotal` | 扣除优惠分摊后金额，更贴近实收 |

### 3.3 成本

| 字段 | 说明 |
|------|------|
| `goodsDetail.cost` | 第一版使用。**口径待确认**：标准成本 / 移动加权成本 / 出库成本 / 考核成本 |

建议在宽表中增加 `cost_note` 字段，记录当前使用的成本口径，便于后续切换。

### 3.4 毛利额

```
毛利额 = 分摊后金额 - 货品成本
       = share_favourable_after_fee - cost_amount
```

- 当分摊后金额为空时，使用 `sellTotal` 作为兜底（已在 COALESCE 逻辑中处理）。
- 成本为空时，毛利也为空（不做补 0 处理，避免误导）。

### 3.5 毛利率

```
毛利率 = 毛利额 / 分摊后金额
```

- 分摊后金额为 0 或空时，毛利率置 NULL。
- 存储为小数（如 0.35 表示 35%），展示层 ×100 加 `%`。
- 负毛利率表示亏损，正常保留。

### 3.6 退款状态

- 字段 `refundStatus` 直接保留，**不自动冲减销售金额**。
- 退款分析建议单独建退款宽表或在 BI 层通过退款状态筛选。
- 如业务要求冲减，可在 BI 层按 `refundStatus` 条件调整。

### 3.7 赠品处理

- `isGift` 字段保留，第一版**不剔除赠品行**。
- 如需排除赠品：`WHERE is_gift != '1'`（具体值待确认）。
- 赠品通常无成本或成本为 0，可能拉高/拉低毛利率，展示时建议支持筛选。

### 3.8 组合装处理

- `isFit` 字段保留，第一版**不做拆分**。
- 组合装如需拆分为单品计算，需要后续对接商品主数据的组合关系。

---

## 四、建表 SQL（MySQL）

```sql
-- ============================================================
-- 创建数据库
-- ============================================================
CREATE DATABASE IF NOT EXISTS dw_ods
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE dw_ods;

-- ============================================================
-- 销售单明细宽表
-- 粒度：一行 = 一个销售单下的一个货品明细
-- 主键：trade_no + sub_trade_id
-- ============================================================
CREATE TABLE dwd_sales_order_detail (
    -- ========== 订单维度 ==========
    trade_no                    VARCHAR(64)     NOT NULL    COMMENT '订单编号（主键）',
    trade_id                    VARCHAR(64)                 COMMENT '订单ID',
    online_order_no             VARCHAR(128)                COMMENT '网店订单号（展示用，优先明细级 sourceTradeNo）',
    source_trade_no             VARCHAR(128)                COMMENT '来源订单号（订单级）',
    online_trade_no             VARCHAR(128)                COMMENT '网店订单号（订单级 onlineTradeNo）',
    shop_name                   VARCHAR(128)                COMMENT '渠道/店铺名称',
    shop_id                     VARCHAR(64)                 COMMENT '渠道ID',
    shop_code                   VARCHAR(64)                 COMMENT '渠道编码',
    logistics_name              VARCHAR(128)                COMMENT '物流公司',
    logistics_no                VARCHAR(128)                COMMENT '物流单号',
    warehouse_name              VARCHAR(128)                COMMENT '发货仓库（订单级）',
    display_warehouse_name      VARCHAR(128)                COMMENT '展示用发货仓库（优先货品级）',
    customer_code               VARCHAR(64)                 COMMENT '客户编号',
    customer_name               VARCHAR(128)                COMMENT '客户名称',
    trade_status                INT                         COMMENT '订单状态',
    trade_status_explain        VARCHAR(64)                 COMMENT '订单状态描述',
    trade_type                  VARCHAR(32)                 COMMENT '订单类型',
    order_time                  DATETIME                    COMMENT '下单时间',
    pay_time                    DATETIME                    COMMENT '付款时间',
    consign_time                DATETIME                    COMMENT '发货时间（订单级）',
    last_ship_time              DATETIME                    COMMENT '承诺发货时间',
    gmt_create                  DATETIME                    COMMENT '系统创建时间',
    gmt_modified                DATETIME                    COMMENT '最后修改时间',

    -- ========== 货品明细 ==========
    sub_trade_id                VARCHAR(64)     NOT NULL    COMMENT '子订单ID（主键）',
    goods_no                    VARCHAR(64)                 COMMENT '货品编号',
    goods_name                  VARCHAR(256)                COMMENT '货品名称',
    sku_no                      VARCHAR(64)                 COMMENT '规格编号',
    spec_name                   VARCHAR(128)                COMMENT '规格名称',
    barcode                     VARCHAR(64)                 COMMENT '货品条码',
    brand_name                  VARCHAR(128)                COMMENT '品牌名称',
    brand_id                    VARCHAR(64)                 COMMENT '品牌ID',
    trade_goods_name            VARCHAR(256)                COMMENT '交易名称（网店商品名）',
    plat_goods_id               VARCHAR(128)                COMMENT '商品链接ID',
    inventory_warehouse_name    VARCHAR(128)                COMMENT '货品仓库名称',
    refund_status               VARCHAR(32)                 COMMENT '退款状态',
    is_gift                     VARCHAR(8)                  COMMENT '是否赠品',
    is_fit                      VARCHAR(8)                  COMMENT '是否组合装',
    source_sub_trade_no         VARCHAR(128)                COMMENT '来源子订单号',
    actual_send_count           DECIMAL(18,4)               COMMENT '实际发货数量',

    -- ========== 金额字段 ==========
    sales_qty                   DECIMAL(18,4)               COMMENT '销售数量（下单口径）',
    sales_price                 DECIMAL(18,4)               COMMENT '单价',
    discount_fee                DECIMAL(18,4)               COMMENT '优惠/折扣',
    sales_amount                DECIMAL(18,4)               COMMENT '金额（销售金额 sellTotal）',
    cost_amount                 DECIMAL(18,4)               COMMENT '货品成本',
    share_favourable_fee        DECIMAL(18,4)               COMMENT '分摊金额',
    share_favourable_after_fee  DECIMAL(18,4)               COMMENT '分摊后金额（COALESCE 三级回退）',
    divide_sell_total           DECIMAL(18,4)               COMMENT '货品分摊销售总额（原始值）',
    share_order_discount_fee    DECIMAL(18,4)               COMMENT '货品分摊订单优惠（原始值）',
    allocated_unit_price        DECIMAL(18,4)               COMMENT '分摊后单价（自算）',
    cost_note                   VARCHAR(64)                 COMMENT '成本口径说明',

    -- ========== 自算指标 ==========
    gross_profit_amount         DECIMAL(18,4)               COMMENT '毛利额（分摊后金额 - 成本）',
    gross_profit_rate           DECIMAL(10,6)               COMMENT '毛利率（毛利额 / 分摊后金额，小数）',
    api_gross_profit            DECIMAL(18,4)               COMMENT 'API返回毛利（订单级，对照用）',

    -- ========== 数据管理 ==========
    dw_insert_time              DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间',
    data_date                   DATE                        COMMENT '数据日期（分区键）',

    -- ========== 主键 ==========
    PRIMARY KEY (trade_no, sub_trade_id),

    -- ========== 索引 ==========
    INDEX idx_order_time (order_time),
    INDEX idx_shop_name (shop_name),
    INDEX idx_goods_no (goods_no),
    INDEX idx_brand_name (brand_name),
    INDEX idx_data_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='销售单明细宽表';
```

---

## 五、数据清洗规则

### 5.1 删除订单

| 规则 | 说明 |
|------|------|
| 字段 | `isDelete` |
| 建议 | **排除 `isDelete = 1` 的订单**。已删除订单不应计入销售统计。 |
| 实现 | 在 ETL 入库时过滤：`WHERE isDelete != 1` 或 `WHERE isDelete = 0` |

### 5.2 有效销售订单状态

| 规则 | 说明 |
|------|------|
| 字段 | `tradeStatus`、`tradeStatusExplain` |
| 建议 | **第一版保留全量状态，不做过滤**。在宽表中保留 `trade_status` 和 `trade_status_explain` 字段，由 BI 层按业务需要筛选。 |
| 配置化 | 后续可在配置表中维护"有效销售状态映射表"，例如：已付款、已发货、已完成 等状态视为有效销售。 |
| 待确认 | 需与业务方确认哪些 `tradeStatus` 数值对应有效销售。 |

### 5.3 退款处理

| 规则 | 说明 |
|------|------|
| 字段 | `goodsDetail.refundStatus` |
| 建议 | **第一版保留字段，不自动冲减销售金额**。 |
| 原因 | 退款可能发生在不同时间段，冲减逻辑复杂，且可能与财务口径冲突。 |
| 实现 | BI 层根据 `refund_status` 值决定是否从销售金额中扣除。 |

### 5.4 赠品处理

| 规则 | 说明 |
|------|------|
| 字段 | `goodsDetail.isGift` |
| 建议 | **第一版保留字段，不剔除赠品行**。 |
| 影响 | 赠品行通常 `sellTotal = 0`、`cost = 0` 或有成本无收入，可能影响毛利率计算。 |
| 后续 | 待业务确认：赠品是否计入销售数量？赠品成本如何处理？ |

### 5.5 组合装处理

| 规则 | 说明 |
|------|------|
| 字段 | `goodsDetail.isFit` |
| 建议 | **第一版保留字段，不做拆分**。 |
| 影响 | 组合装作为一个整体行记录，数量和金额为组合装整体值。 |
| 后续 | 如需拆分为单品，需对接商品主数据中的组合装 BOM 关系。 |

### 5.6 汇总

```
ETL 清洗条件（第一版）：
  1. WHERE isDelete != 1                          -- 排除已删除订单
  2. trade_status、refund_status、is_gift、is_fit  -- 全部保留，不过滤
  3. 金额字段：NULL 保留为 NULL，不做补 0
  4. 自算字段（毛利、毛利率）：按 COALESCE + NULLIF 逻辑安全计算
```

---

## 六、歧义字段处理汇总

| 问题 | 方案 | 实现 |
|------|------|------|
| 网店订单号 | 展示字段优先明细级 `sourceTradeNo`，回退订单级 `onlineTradeNo` | `COALESCE(goodsDetail.sourceTradeNo, onlineTradeNo)` → `online_order_no` |
| 发货仓库 | 展示字段优先货品级 `inventoryWarehouseName`，回退订单级 `warehouseName` | `COALESCE(inventoryWarehouseName, warehouseName)` → `display_warehouse_name` |
| 分摊后金额 | 三级回退：`shareFavourableAfterFee` → `divideSellTotal` → `sellTotal` | `COALESCE(shareFavourableAfterFee, divideSellTotal, sellTotal)` → `share_favourable_after_fee` |
| 分摊后单价 | 自算：`分摊后金额 / 销售数量` | `share_favourable_after_fee / NULLIF(sales_qty, 0)` → `allocated_unit_price` |
| 费用分摊 | **暂缺字段**，当前 API fields 中无明确费用分摊字段 | 标记为待补充，后续确认是否需接入 `expense.expenseFee` 或财务分摊逻辑 |
| 货品级发货时间 | 第一版使用订单级 `consignTime` | 如需精确到货品级，后续启用 `packageDetail.consignTime`（注意一对多问题） |
| 商品链接ID | 第一版使用 `platGoodsId` | 如需真实 URL，后续补商品主数据映射 |
| 成本口径 | 第一版使用 `goodsDetail.cost`，字段值含义待确认 | 增加 `cost_note` 字段标注口径 |

---

## 七、实施计划

### 7.1 技术方案概述

改造现有 `sales_order_wide_table.py`，在获取 API 数据拍平为 DataFrame 后，新增**自算字段计算**和**MySQL 入库**逻辑。保持现有 CSV 导出功能不变，新增 MySQL 写入能力。

### 7.2 改造步骤

#### 步骤 1：新增依赖和数据库配置

在脚本顶部配置区新增：

```python
import pymysql

DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "091633",
    "database": "dw_ods",
    "charset":  "utf8mb4",
}
```

#### 步骤 2：新增建库建表函数

```python
def init_database():
    """创建数据库和表（幂等操作）"""
    # 连接 MySQL（不指定 database）
    # CREATE DATABASE IF NOT EXISTS dw_ods
    # USE dw_ods
    # 执行 CREATE TABLE IF NOT EXISTS dwd_sales_order_detail (...)
    # 关闭连接
```

#### 步骤 3：新增字段映射函数

在 `flatten_orders_to_wide_table` 之后，新增映射函数将 API 驼峰字段名转为表字段蛇形命名：

```python
def map_to_table_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    将拍平后的 DataFrame 字段映射为 dwd_sales_order_detail 表字段
    包含：
    1. 字段重命名（API 驼峰 → 表蛇形）
    2. 展示字段 COALESCE 合并
    3. 自算字段计算（毛利、毛利率、分摊后单价）
    4. 数据清洗（排除 isDelete=1）
    """
```

核心映射逻辑：

```python
# 网店订单号：优先明细级 sourceTradeNo，回退订单级 onlineTradeNo
df['online_order_no'] = df['货品_sourceTradeNo'].fillna(df['onlineTradeNo'])

# 展示用仓库：优先货品级，回退订单级
df['display_warehouse_name'] = df['货品_inventoryWarehouseName'].fillna(df['warehouseName'])

# 分摊后金额：三级回退
df['share_favourable_after_fee'] = (
    df['货品_shareFavourableAfterFee']
    .fillna(df['货品_divideSellTotal'])
    .fillna(df['货品_sellTotal'])
)

# 分摊后单价
df['allocated_unit_price'] = df['share_favourable_after_fee'] / df['sales_qty']
df.loc[df['sales_qty'].isna() | (df['sales_qty'] == 0), 'allocated_unit_price'] = None

# 毛利额
df['gross_profit_amount'] = df['share_favourable_after_fee'] - df['cost_amount']
df.loc[df['share_favourable_after_fee'].isna() | df['cost_amount'].isna(), 'gross_profit_amount'] = None

# 毛利率
df['gross_profit_rate'] = df['gross_profit_amount'] / df['share_favourable_after_fee']
df.loc[df['share_favourable_after_fee'].isna() | (df['share_favourable_after_fee'] == 0), 'gross_profit_rate'] = None

# 数据清洗：排除已删除订单
df = df[df['isDelete'] != 1].copy()
```

#### 步骤 4：新增 MySQL 入库函数

```python
def write_to_mysql(df: pd.DataFrame):
    """
    将 DataFrame 写入 MySQL
    策略：按 trade_no + sub_trade_id 做 REPLACE INTO（幂等写入）
    """
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 构造 REPLACE INTO 语句
    # 逐行写入或批量写入（推荐批量，每 500 行一批）
    # 提交事务
    # 关闭连接
```

批量写入方案：

```python
def write_to_mysql(df: pd.DataFrame, batch_size: int = 500):
    """批量写入 MySQL，每 batch_size 行一批提交"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    columns = df.columns.tolist()
    placeholders = ', '.join(['%s'] * len(columns))
    col_names = ', '.join([f'`{c}`' for c in columns])

    sql = f"REPLACE INTO dwd_sales_order_detail ({col_names}) VALUES ({placeholders})"

    rows = df.values.tolist()
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        cursor.executemany(sql, batch)
        conn.commit()
        print(f"  已写入 {min(i + batch_size, len(rows))}/{len(rows)} 行")

    cursor.close()
    conn.close()
```

#### 步骤 5：改造 main 函数

```python
def main():
    # 1. 初始化数据库（建库建表）
    init_database()

    # 2. 获取 API 数据（现有逻辑不变）
    orders = fetch_all_orders()
    if not orders:
        print("未获取到数据")
        return

    # 3. 拍平为宽表（现有逻辑不变）
    df_raw = flatten_orders_to_wide_table(orders)

    # 4. 字段映射 + 自算指标 + 数据清洗（新增）
    df_table = map_to_table_fields(df_raw)

    # 5. 导出 CSV（现有逻辑不变）
    df_table.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 6. 写入 MySQL（新增）
    write_to_mysql(df_table)
```

### 7.3 文件改造清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `sales_order_wide_table.py` | 修改 | 新增 DB_CONFIG、init_database()、map_to_table_fields()、write_to_mysql()，改造 main() |
| `requirements.txt` | 新增 | 添加 `pymysql` 依赖 |
| `agent.md` | 已有 | 设计文档（本文件） |

### 7.4 执行顺序

```
1. pip install pymysql          # 安装 MySQL 驱动
2. 确认 MySQL 服务已启动         # localhost:3306
3. python sales_order_wide_table.py  # 运行脚本
   → 自动建库建表（幂等）
   → 调用 API 获取数据
   → 拍平 + 字段映射 + 自算指标
   → 导出 CSV
   → 写入 MySQL
```

### 7.5 注意事项

1. **幂等设计**：使用 `REPLACE INTO`，重复运行不会产生重复数据
2. **字符集**：数据库和表均使用 `utf8mb4`，支持 emoji 和特殊字符
3. **NULL 处理**：自算字段在分母为 0 或依赖字段为 NULL 时置 NULL，不做补 0
4. **事务安全**：每 500 行一批提交，避免大事务锁表
5. **字段顺序**：DataFrame 列顺序必须与表字段顺序一致，建议在 map 函数中显式指定列顺序
6. **sub_trade_id 为空**：部分订单可能无 goodsDetail 或 subTradeId 为空，需做兜底处理（如使用 tradeNo + goodsNo + 行号生成唯一键）
