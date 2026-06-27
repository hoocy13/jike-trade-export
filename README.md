# 吉客云数据导出工具集

调用吉客云开放平台 API，自动获取业务数据并写入本地 MySQL 数据库。

## 包含脚本

| 脚本 | API 方法 | 说明 |
|------|----------|------|
| `scripts/sales_order.py` | `oms.trade.fullinfoget` | 销售订单 + 货品明细宽表 |
| `scripts/warehouse_stock.py` | `erp-stock.stock.skulist` | 分仓库存数据 |
| `scripts/warehouse_list.py` | `erp.warehouse.get` | 仓库编码查询（辅助工具） |

## 快速开始

```bash
# 1. 安装依赖
pip install requests pandas pymysql numpy

# 2. 修改配置（config.py 中的 APP_KEY、DB_CONFIG）

# 3. 查询仓库编码
python scripts/warehouse_list.py

# 4. 销售单导出
python scripts/sales_order.py

# 5. 分仓库存导出
python scripts/warehouse_stock.py
```

## 项目结构

```
├── config.py              # 公共配置（APP_KEY、DB_CONFIG）
├── common.py              # 公共工具（签名、请求、MySQL写入）
├── scripts/               # 数据导出脚本
├── docs/                  # 设计文档
├── data/                  # CSV 输出目录
├── CLAUDE.md              # 项目说明
└── README.md              # 本文件
```

## 运行模式

脚本顶部 `RUN_MODE` 参数：

- `"full"` — API → CSV → MySQL（完整流程）
- `"import"` — CSV → MySQL（仅导入，跳过 API）

## 数据库

- MySQL 本地数据库：`dw_ods`
- 销售单表：`dwd_sales_order_detail`（54 列，中文字段名）
- 分仓库存表：`fencangkuchaxun`（32 列，中文字段名）

## API 签名规则

```
签名原文 = secret + key1value1key2value2... + secret
签名 = MD5(签名原文.lower())
```

> 整个字符串必须转小写再 MD5（官方文档未说明，从签名工具反推）

## 限制说明

- 时间范围：单次查询不超过 7 天（脚本自动拆分并行）
- 频率限制：1 次/秒（脚本设置 0.5 秒间隔）
- 库存 API：每仓库最多返回 300 条（API 层面限制）
