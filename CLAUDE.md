# CLAUDE.md

## 项目概述

吉客云开放平台销售订单导出工具。调用 `oms.trade.fullinfoget` 接口获取销售订单数据，自动处理分页和时间拆分，将订单与商品明细拍平为大宽表 CSV。

## 技术栈

- Python 3.12
- requests（HTTP 请求）
- pandas（数据处理 + CSV 输出）
- 虚拟环境：`.venv/`

## 运行

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install requests pandas

# 运行
python sales_order_wide_table.py
```

## 关键文件

- `sales_order_wide_table.py` — 主脚本（唯一源码文件）
- `sales_order_wide_table.csv` — 输出文件（运行后生成）

## 配置

脚本顶部配置区修改：
- `APP_KEY` / `APP_SECRET` — 吉客云应用凭证
- `START_TRADE_TIME` / `END_TRADE_TIME` — 查询时间范围
- `PAGE_SIZE` — 每页条数（最大 200）
- `FIELDS` — 请求返回的字段列表

## API 签名规则（踩坑记录）

**签名算法**：拼接所有参数 → 整个字符串 `.lower()` 转小写 → MD5

```
签名原文 = secret + key1value1key2value2... + secret
签名 = MD5(签名原文.lower())
```

**关键坑点**：
1. 签名时整个字符串必须转小写（文档未说明，从官方签名工具反推得出）
2. `pageSize` 在 bizcontent 中是数字类型，不是字符串
3. 参数名全小写：`appkey`、`contenttype`、`bizcontent`、`method`、`timestamp`、`version`
4. API 成功返回 `code: 200`，失败返回 `code: 0` + `subCode`
5. 数据结构：`result.data.trades[]`、`result.data.scrollId`
6. 频率限制：1 次/秒，脚本已设置 1.2 秒间隔

## 时间范围限制

API 要求起止时间不超过 7 天。脚本自动拆分：
- 输入任意时间范围 → 自动切分为多个 ≤7 天的窗口
- 逐窗口分页获取 → 合并结果

## 数据拍平逻辑

一个订单包含 N 个商品（`goodsDetail` 数组）→ 输出 N 行：
- 每行重复订单级字段
- 货品字段自动加 `货品_` 前缀
- 嵌套对象/数组自动转 JSON 字符串
