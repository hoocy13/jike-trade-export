# 吉客云 Web 导出同步脚本

通过吉客云网页版导出任务获取数据，下载 xlsx 后写入 MySQL。当前脚本以 DolphinScheduler 部署为目标，同时保留 PyCharm 右键运行方式。

## 目录结构

```text
config.py
common.py
requirements.txt
scripts/
  销售单查询_web.py
  销售单明细账_web.py
  分仓库查询_web.py
  总库存查询_web.py
  渠道列表_web.py
  warehouse_list.py
data/
  .gitkeep
CLAUDE.md
agent.md
README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 销售单同步

脚本：

```bash
python scripts/销售单查询_web.py
```

目标表：

```text
ods.销售单查询
```

本地调试时，把 DevTools 复制的销售单查询 `queryList` 或 `startExcelExport` 完整 cURL 粘到脚本顶部 `START_EXPORT_CURL_TEXT`。

## 分仓库存同步

脚本：

```bash
python scripts/分仓库查询_web.py
```

目标表：

```text
ods.分仓库查询
```

本地调试时，把 DevTools 复制的分仓库存查询 `stockSkuList` 或 `startExcelExport` 完整 cURL 粘到脚本顶部 `START_EXPORT_CURL_TEXT`。

库存表写入是全量快照替换：先写临时表，再用 `RENAME TABLE` 原子切换。

## 数据类型约定

库存数量类字段使用 `DECIMAL(18,0)`；金额/价格类字段使用 `DECIMAL(18,2)`。

`含税价`、`不含税价`、`当前成本价`、`库存金额` 保留 2 位小数。

## 销售单明细账同步

脚本：

```bash
python scripts/销售单明细账_web.py
```

目标表：

```text
ods.销售单明细账
```

本地调试时，把 DevTools 复制的销售单明细账 `tradeOrderDetialList` 或导出 `startExcelExport` 完整 cURL 粘到脚本顶部 `START_EXPORT_CURL_TEXT`。

不传 `--start/--end` 时，默认同步当月 1 日 `00:00:00` 到今天 `23:59:59`。

如果导出触发安全验证，需要重新复制带 `commonVerify` 的 cURL，或设置环境变量 `JKY_SALES_ORDER_DETAIL_COMMON_VERIFY`。

## 渠道列表同步

脚本：

```bash
python scripts/渠道列表_web.py
```

目标表：

```text
ods.渠道列表
```

本地调试时，把 DevTools 复制的 `getsaleschannelinfoforcols` 完整 cURL 粘到脚本顶部 `START_LIST_CURL_TEXT`。

渠道列表是主数据，脚本会直接分页拉接口，并用全量快照替换写入 MySQL。

## 总库存查询同步

脚本：

```bash
python scripts/总库存查询_web.py
```

目标表：

```text
ods.总库存查询
```

本地调试时，把 DevTools 复制的 `allStockSkuList` 完整 cURL 粘到脚本顶部 `START_LIST_CURL_TEXT`。

脚本会直接分页拉接口，并用全量快照替换写入 MySQL。数量类字段使用 `DECIMAL(18,0)`，价格类字段使用 `DECIMAL(18,2)`。

## 清理约定

`data/**/*.csv`、`data/**/*.xlsx`、`__pycache__/`、`.idea/`、`*.jar` 都不进入项目版本。
