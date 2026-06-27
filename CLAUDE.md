# CLAUDE.md

## 项目概述

吉客云开放平台数据导出工具集。调用吉客云 API 获取业务数据，自动处理分页和时间拆分，拍平为大宽表 CSV，并写入本地 MySQL 数据库。

## 项目结构

```
jike-trade-export/
├── config.py              # 公共配置（APP_KEY、DB_CONFIG）
├── common.py              # 公共工具（签名、API请求、MySQL写入）
├── scripts/
│   ├── sales_order.py     # 销售单查询（oms.trade.fullinfoget）
│   ├── warehouse_stock.py # 分仓库存查询（erp-stock.stock.skulist）
│   └── warehouse_list.py  # 仓库编码查询（erp.warehouse.get）
├── docs/
│   └── sales_order_design.md  # 销售单宽表设计文档
├── data/                  # CSV 输出目录（gitignore）
├── CLAUDE.md              # 本文件
└── README.md              # 使用文档
```

## 技术栈

- Python 3.12
- requests（HTTP 请求）
- pandas（数据处理 + CSV 输出）
- pymysql（MySQL 写入）
- numpy（数值处理）

## 运行

```bash
# 安装依赖
pip install requests pandas pymysql numpy

# 查询仓库编码
python scripts/warehouse_list.py

# 销售单查询（完整流程：API → CSV → MySQL）
python scripts/sales_order.py

# 分仓库存查询
python scripts/warehouse_stock.py
```

## 运行模式

脚本顶部 `RUN_MODE` 参数：

- `"full"` — 完整流程：调用 API → 拍平 → CSV → MySQL
- `"import"` — 仅从已有 CSV 导入 MySQL

## 配置

- `config.py` — 公共配置（APP_KEY、DB_CONFIG 等），修改全局生效
- 各脚本顶部 — 业务配置（时间范围、仓库编码、表名等）

## 数据库

- MySQL：`dw_ods`
- 销售单表：`dwd_sales_order_detail`（中文字段名，主键：订单编号 + 子订单ID）
- 分仓库存表：`fencangkuchaxun`（中文字段名）

## API 签名规则

```
签名原文 = secret + key1value1key2value2... + secret
签名 = MD5(签名原文.lower())
```

关键：整个字符串必须转小写再 MD5。

## 性能优化

- 多线程并行拉取（时间窗口拆分后并行）
- 请求间隔 0.5 秒
- MySQL 使用 LOAD DATA LOCAL INFILE（比逐行 INSERT 快 10x+）
