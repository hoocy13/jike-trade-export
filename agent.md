# agent.md — 项目上下文速查

## 项目是什么

吉客云开放平台数据导出工具集。通过 API 拉取业务数据，拍平为宽表，导出 CSV 并写入本地 MySQL。

## 目录结构

```
├── config.py              # 公共配置（APP_KEY、DB_CONFIG）
├── common.py              # 公共工具（签名、API请求、MySQL写入）
├── scripts/
│   ├── sales_order.py     # 销售单（oms.trade.fullinfoget）
│   ├── warehouse_stock.py # 分仓库存（erp-stock.stock.skulist）
│   └── warehouse_list.py  # 仓库编码查询（erp.warehouse.get）
├── docs/
│   └── sales_order_design.md  # 销售单宽表设计文档
├── data/                  # CSV 输出（gitignore）
├── CLAUDE.md              # 项目说明
└── README.md              # 使用文档
```

## 核心设计

- **签名算法**：参数排序 → 拼接 → 整体 `.lower()` → MD5
- **分页**：销售单用 scrollId 游标，库存用 pageIndex 页码
- **时间拆分**：超过 7 天自动切窗口，多线程并行拉取
- **MySQL 写入**：LOAD DATA LOCAL INFILE（快 10x+）
- **字段名**：CSV 和 MySQL 表统一使用中文列名
- **运行模式**：`full`（API→CSV→MySQL）/ `import`（CSV→MySQL）

## 数据库

- MySQL 本地：`dw_ods`
- 销售单表：`dwd_sales_order_detail`（54 列，主键：订单编号 + 子订单ID）
- 分仓库存表：`fencangkuchaxun`（32 列）

## 新增数据源步骤

1. 在 `scripts/` 新建脚本
2. 从 `common` 导入 `api_request`、`init_database`、`write_to_mysql`
3. 从 `config` 导入 `DB_CONFIG`
4. 定义业务配置（METHOD、TABLE_NAME、字段映射）
5. 编写建表 SQL（中文字段名）
6. 实现数据获取 + 转换 + 写入

## 注意事项

- API 签名时整个字符串必须转小写
- 库存 API 有 300 条/仓库硬限制
- 销售单 subCode 非空不代表错误（code=200 即成功）
- CSV 输出到 `data/` 目录
