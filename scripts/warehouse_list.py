"""
吉客云开放平台 - 查询仓库编码
调用 erp.warehouse.get 接口获取所有仓库信息
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import api_request


def fetch_warehouses():
    biz = json.dumps({"pageIndex": 0, "pageSize": 200, "includeDeleteAndBlockup": 0})
    result = api_request("erp.warehouse.get", biz)
    if result is None:
        return []
    return result.get("result", {}).get("data", {}).get("warehouseInfo", [])


def main():
    print("查询仓库列表...\n")
    warehouses = fetch_warehouses()
    if not warehouses:
        print("未获取到仓库数据")
        return

    print(f"共 {len(warehouses)} 个仓库:\n")
    print(f"{'仓库编码':<15} {'仓库名称':<30} {'仓库ID'}")
    print("-" * 80)
    for wh in warehouses:
        print(f"{wh.get('warehouseCode', ''):<15} {wh.get('warehouseName', ''):<30} {wh.get('warehouseId', '')}")

    codes = [wh.get("warehouseCode", "") for wh in warehouses if wh.get("warehouseCode")]
    print(f"\n# 可直接复制到 warehouse_stock.py 的配置:")
    print(f"WAREHOUSE_CODES = {codes}")


if __name__ == "__main__":
    main()
