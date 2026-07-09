"""
吉客云开放平台 - 分仓库存查询脚本（规格模式）
调用 erp-stock.stock.skulist 接口，按仓库逐个查询，导出 CSV + 写入 MySQL
"""
import json
import sys
import os
import time
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, REQUEST_INTERVAL, DATA_DIR
from common import api_request, sleep_between_requests, init_database, write_to_mysql

# ============================================================
# 业务配置
# ============================================================
METHOD = "erp-stock.stock.skulist"
TABLE_NAME = "fencangkuchaxun"
RUN_MODE = "import"
OUTPUT_CSV = os.path.join(DATA_DIR, "warehouse_stock.xlsx")
PAGE_SIZE = 200

# 仓库编码列表（从 scripts/warehouse_list.py 获取）
WAREHOUSE_CODES = ['1005', '0027', '0023', '1004', '0025', '0022', '0024', '1003', '1001', '0054', '0046', '0041',
                   '0040', '0033', '0026', '1006', 'W0064', '1002']

# API 字段 → 中文列名映射
FIELD_MAP = {
    "warehouseName": "仓库",
    "brandName": "品牌",
    "goodsNo": "货品编号",
    "goodsName": "货品名称",
    "skuName": "规格",
    "canUseQuantity": "可用库存",
    "costPrice": "当前成本价",
    "costValue": "库存金额",
    "currentQuantity": "库存数量",
    "unitName": "单位",
    "distrubuteQuantity": "渠道预留",
    "purchasingQuantity": "采购在途",
    "allocateQuantity": "调拨在途",
    "salesReturnQuantity": "退货在途",
    "weekQuantity": "近7天销量",
    "threedayQuantity": "近30天销量",
    "field5": "近90天销量(库存公式)",
    "lastStockInTime": "最近入库时间",
    "skuBarcode": "条码",
    "price6": "含税价",
    "price7": "不含税价",
    "totalSaleQuantity": "总销量",
    "orderingQuantity": "订购数量",
    "stockOutQuantity": "出库数量",
    "stockInQuantity": "入库数量",
    "lockingQuantity": "锁定数量",
}

# ============================================================
# 建表 SQL
# ============================================================
CREATE_TABLE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    `仓库` VARCHAR(128),
    `品牌` VARCHAR(128),
    `货品编号` VARCHAR(64),
    `货品名称` TEXT,
    `规格` VARCHAR(128),
    `可用库存` DECIMAL(18,4),
    `当前成本价` DECIMAL(18,4),
    `库存金额` DECIMAL(18,4),
    `库存数量` DECIMAL(18,4),
    `单位` VARCHAR(32),
    `渠道预留` DECIMAL(18,4),
    `采购在途` DECIMAL(18,4),
    `调拨在途` DECIMAL(18,4),
    `退货在途` DECIMAL(18,4),
    `近7天销量` DECIMAL(18,4),
    `近30天销量` DECIMAL(18,4),
    `近90天销量(库存公式)` DECIMAL(18,4),
    `最近入库时间` VARCHAR(64),
    `条码` VARCHAR(64),
    `含税价` DECIMAL(18,4),
    `不含税价` DECIMAL(18,4),
    `数据日期` DATE,
    INDEX idx_仓库 (`仓库`), INDEX idx_货品编号 (`货品编号`),
    INDEX idx_品牌 (`品牌`), INDEX idx_条码 (`条码`), INDEX idx_数据日期 (`数据日期`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='分仓库存表'
"""

# ============================================================
# 数据获取
# ============================================================
COLS = "warehouseName,brandName,goodsNo,goodsName,skuName,canUseQuantity,costPrice,costValue,currentQuantity,unitName,distrubuteQuantity,purchasingQuantity,allocateQuantity,salesReturnQuantity,weekQuantity,threedayQuantity,field5,lastStockInTime,skuBarcode,price6,price7,totalSaleQuantity,orderingQuantity,stockOutQuantity,stockInQuantity,lockingQuantity"


def fetch_stock_page(warehouse_code: str, page_index: int = 0) -> list[dict] | None:
    biz = json.dumps({"pageIndex": page_index, "pageSize": PAGE_SIZE, "warehouseCode": warehouse_code, "cols": COLS})
    result = api_request(METHOD, biz)
    if result is None:
        return None
    return result.get("result", {}).get("data", [])


def fetch_warehouse_stock(warehouse_code: str) -> list[dict]:
    all_data, page_index = [], 0
    while True:
        data = fetch_stock_page(warehouse_code, page_index)
        if data is None:
            print(f"    [警告] 请求失败")
            break
        if not data:
            if page_index == 0:
                print(f"    无库存数据")
            break
        all_data.extend(data)
        print(f"    第 {page_index} 页: {len(data)} 条，累计 {len(all_data)} 条")
        if len(data) < PAGE_SIZE:
            break
        page_index += 1
        sleep_between_requests()
    return all_data


def fetch_all_stock() -> list[dict]:
    if not WAREHOUSE_CODES:
        print("未配置仓库编码，请先运行 scripts/warehouse_list.py 获取")
        return []
    print(f"共 {len(WAREHOUSE_CODES)} 个仓库\n")
    all_data = []
    for i, wh in enumerate(WAREHOUSE_CODES, 1):
        print(f"[{i}/{len(WAREHOUSE_CODES)}] 仓库 {wh}")
        data = fetch_warehouse_stock(wh)
        all_data.extend(data)
        time.sleep(0.3)
    print(f"\n全部完成，共获取 {len(all_data)} 条库存记录")
    return all_data


# ============================================================
# 数据转换
# ============================================================
def convert_to_dataframe(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    for api_field in FIELD_MAP:
        if api_field not in df.columns:
            df[api_field] = None
    df = df.rename(columns={k: v for k, v in FIELD_MAP.items() if k in df.columns})
    df["数据日期"] = date.today()

    # 按业务需求排列列顺序（与网页导出一致）
    final_columns = [
        "仓库", "品牌", "货品编号", "货品名称", "规格",
        "可用库存", "当前成本价", "库存金额", "库存数量", "单位",
        "渠道预留", "采购在途", "调拨在途", "退货在途",
        "近7天销量", "近30天销量", "近90天销量(库存公式)",
        "最近入库时间", "条码", "含税价", "不含税价",
        "数据日期",
    ]
    df = df[final_columns]
    return df


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print(f"吉客云分仓库存查询工具  [模式: {RUN_MODE}]")
    print("=" * 60 + "\n")

    if RUN_MODE == "import":
        print("[步骤 1/3] 初始化数据库...")
        init_database(TABLE_NAME, CREATE_TABLE_SQL)

        print(f"\n[步骤 2/3] 读取文件: {OUTPUT_CSV}")
        if OUTPUT_CSV.endswith('.xlsx'):
            df = pd.read_excel(OUTPUT_CSV)
        else:
            df = pd.read_csv(OUTPUT_CSV, low_memory=False)
        print(f"  读取完成：{len(df)} 行, {len(df.columns)} 列")
        print(f"  列名：{list(df.columns)}")
        # 添加数据日期
        df["数据日期"] = date.today()

        print(f"\n[步骤 3/3] 写入 MySQL（影子表原子切换）...")
        write_to_mysql(df, TABLE_NAME, CREATE_TABLE_SQL)
    else:
        print(f"\n[步骤 1/3] 获取库存数据...")
        records = fetch_all_stock()
        if not records:
            print("未获取到数据")
            return

        print(f"\n[步骤 2/3] 数据转换...")
        df = convert_to_dataframe(records)
        print(f"  转换完成：{len(df)} 行, {len(df.columns)} 列")
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"  CSV 已保存: {OUTPUT_CSV}")

        print(f"\n[步骤 3/3] 写入 MySQL（影子表原子切换）...")
        write_to_mysql(df, TABLE_NAME, CREATE_TABLE_SQL)

    print(f"\n{'=' * 60}")
    print(f"全部完成！MySQL: {DB_CONFIG['database']}.{TABLE_NAME}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
