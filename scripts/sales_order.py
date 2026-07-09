"""
吉客云开放平台 - 销售订单大宽表导出脚本
调用 oms.trade.fullinfoget 接口，多线程并行拉取，拍平为宽表，导出 CSV + 写入 MySQL
"""
import json
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, date

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, REQUEST_INTERVAL, DATA_DIR
from common import generate_sign, build_params, init_database, write_to_mysql

# ============================================================
# 业务配置
# ============================================================
METHOD = "oms.trade.fullinfoget"
TABLE_NAME = "xiaoshoudanchaxun"
RUN_MODE = "full"         # import or full
OUTPUT_CSV = os.path.join(DATA_DIR, "sales_order.csv")
PAGE_SIZE = 200

# 近1个月（动态计算，每次执行自动取最近30天）
END_TRADE_TIME = datetime.now().strftime("%Y-%m-%d 23:59:59")
START_TRADE_TIME = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")

# fields 参数：全量字段
FIELDS = ",".join([
    "tradeNo", "tradeId", "tradeStatus", "tradeStatusExplain", "tradeType",
    "tradeTime", "payTime", "consignTime", "completeTime", "confirmTime",
    "auditTime", "reviewTime", "signingTime", "notifyPickTime",
    "gmtCreate", "gmtModified", "lastShipTime", "platConsignTime",
    "shopName", "shopId", "shopcode", "shopTypeCode", "companyName",
    "warehouseName", "warehouseId", "warehouseCode",
    "logisticName", "logisticCode", "logisticType", "mainPostid",
    "receiverName", "mobile", "email",
    "state", "city", "district", "town", "address", "zip",
    "country", "countryCode", "cityCode",
    "totalFee", "discountFee", "payment", "postFee", "receivedPostFee",
    "taxFee", "couponFee", "otherFee", "realFee",
    "receivedTotal", "localPayment", "localExchangeRate",
    "buyerMemo", "sellerMemo", "appendMemo", "buyerOpenUid",
    "orderNo", "stockoutNo", "tradeFrom", "tradeCount", "goodsTypeCount",
    "estimateWeight", "packageWeight", "estimateVolume",
    "seller", "register", "auditor", "reviewer",
    "payType", "payNo", "payStatus", "invoiceType", "invoiceNo", "invoiceCode",
    "sourceTradeNo", "onlineTradeNo", "sourceAfterNo",
    "customerName", "customerCode", "customerTypeName", "customerGradeName",
    "customerTags", "customerAccount", "customerDiscount",
    "flagIds", "flagNames", "sysFlagIds",
    "isDelete", "isTableSwitch",
    "freezeReason", "abnormalDescription", "specialReminding",
    "departName", "agentShopName", "platFlags", "scrollId",
    "goodsDetail.goodsNo", "goodsDetail.goodsName", "goodsDetail.specName",
    "goodsDetail.barcode", "goodsDetail.outerId",
    "goodsDetail.sellCount", "goodsDetail.sellPrice", "goodsDetail.sellTotal",
    "goodsDetail.unit", "goodsDetail.cost", "goodsDetail.taxFee", "goodsDetail.taxRate",
    "goodsDetail.discountFee", "goodsDetail.discountTotal", "goodsDetail.discountPoint",
    "goodsDetail.shareFavourableFee", "goodsDetail.shareFavourableAfterFee",
    "goodsDetail.shareOrderDiscountFee", "goodsDetail.shareOrderPlatDiscountFee",
    "goodsDetail.goodsPlatDiscountFee", "goodsDetail.divideSellTotal",
    "goodsDetail.estimateWeight", "goodsDetail.estimateGoodsVolume",
    "goodsDetail.isFit", "goodsDetail.isGift", "goodsDetail.isPresell",
    "goodsDetail.goodsMemo", "goodsDetail.cateName", "goodsDetail.brandName",
    "goodsDetail.goodsTags", "goodsDetail.customerPrice", "goodsDetail.customerTotal",
    "goodsDetail.tradeGoodsNo", "goodsDetail.tradeGoodsName",
    "goodsDetail.tradeGoodsSpec", "goodsDetail.tradeGoodsUnit",
    "goodsDetail.sourceSubtradeNo", "goodsDetail.sourceTradeNo",
    "goodsDetail.platCode", "goodsDetail.platGoodsId", "goodsDetail.platSkuId",
    "goodsDetail.subTradeId", "goodsDetail.tradeId",
    "goodsDetail.specId", "goodsDetail.goodsId",
    "goodsDetail.skuImgUrl", "goodsDetail.apiType",
    "goodsDetail.actualSendCount", "goodsDetail.needProcessCount",
    "goodsDetail.goodsFlagIds", "goodsDetail.goodsFlagNames",
    "goodsDetail.customerTradeNo", "goodsDetail.customerSubtradeNo",
    "goodsDetail.platAuthorId", "goodsDetail.platAuthorName",
    "goodsDetail.isPlatGift",
    "goodsDetail.goodsSeller", "goodsDetail.goodsCompassSourceContentType",
    "goodsDetail.inventoryWarehouseId", "goodsDetail.inventoryWarehouseName",
    "goodsDetail.auxiliaryInventoryCount", "goodsDetail.auxiliaryInventoryUnit",
    "goodsDetail.assessmentCostLocal",
    "goodsDetail.assessmentGrossProfitLocal", "goodsDetail.assessmentGrossProfitPercent",
    "goodsDetail.baseUnitSellCount", "goodsDetail.refundStatus",
])

# ============================================================
# 建表 SQL
# ============================================================
CREATE_TABLE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    `订单编号` VARCHAR(64) NOT NULL, `订单ID` VARCHAR(64),
    `网店订单号` TEXT, `来源订单号` TEXT, `网店订单号_订单级` TEXT,
    `渠道名称` VARCHAR(128), `渠道ID` VARCHAR(64), `渠道编码` VARCHAR(64),
    `物流公司` VARCHAR(128), `物流单号` VARCHAR(128),
    `发货仓库_订单级` VARCHAR(128), `发货仓库` VARCHAR(128),
    `客户编号` VARCHAR(64), `客户名称` VARCHAR(128),
    `订单状态` INT, `订单状态描述` VARCHAR(64), `订单类型` VARCHAR(32),
    `下单时间` DATETIME, `付款时间` DATETIME, `发货时间` DATETIME,
    `承诺发货时间` DATETIME, `创建时间` DATETIME, `最后修改时间` DATETIME,
    `子订单ID` VARCHAR(64) NOT NULL,
    `货品编号` VARCHAR(64), `货品名称` TEXT, `规格编号` VARCHAR(64),
    `规格名称` VARCHAR(128), `货品条码` VARCHAR(64),
    `品牌名称` VARCHAR(128), `品牌ID` VARCHAR(64),
    `交易名称` TEXT, `商品链接ID` VARCHAR(256), `货品仓库` VARCHAR(128),
    `退款状态` VARCHAR(32), `是否赠品` VARCHAR(8), `是否组合装` VARCHAR(8),
    `来源子订单号` VARCHAR(256), `实际发货数量` DECIMAL(18,4),
    `销售数量` DECIMAL(18,4), `单价` DECIMAL(18,4), `优惠折扣` DECIMAL(18,4),
    `销售金额` DECIMAL(18,4), `货品成本` DECIMAL(18,4),
    `分摊金额` DECIMAL(18,4), `分摊后金额` DECIMAL(18,4),
    `分摊销售总额` DECIMAL(18,4), `分摊订单优惠` DECIMAL(18,4),
    `分摊后单价` DECIMAL(18,4), `成本口径` VARCHAR(64),
    `毛利额` DECIMAL(18,4), `毛利率` DECIMAL(10,6), `API毛利` DECIMAL(18,4),
    `数据日期` DATE,
    PRIMARY KEY (`订单编号`, `子订单ID`),
    INDEX idx_下单时间 (`下单时间`), INDEX idx_渠道名称 (`渠道名称`),
    INDEX idx_货品编号 (`货品编号`), INDEX idx_品牌名称 (`品牌名称`),
    INDEX idx_数据日期 (`数据日期`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='销售单明细宽表'
"""


# ============================================================
# API 请求（销售单特殊：scrollId 分页 + subCode 检查）
# ============================================================
def fetch_orders(start_time: str, end_time: str, scroll_id: str = "") -> tuple:
    """返回 (订单列表, 下一页scrollId)，失败返回 (None, None)"""
    from config import APP_KEY, APP_SECRET, API_URL, VERSION, CONTENT_TYPE, MAX_RETRIES, REQUEST_TIMEOUT
    import requests

    biz = json.dumps({
        "startTradeTime": start_time, "endTradeTime": end_time,
        "fields": FIELDS, "pageSize": PAGE_SIZE, "scrollId": scroll_id,
    }, ensure_ascii=False, separators=(",", ":"))

    for attempt in range(1, MAX_RETRIES + 1):
        params = build_params(METHOD, biz)
        try:
            resp = requests.post(API_URL, data=params, timeout=REQUEST_TIMEOUT)
            result = resp.json()
        except Exception as e:
            print(f"  [重试 {attempt}/{MAX_RETRIES}] 请求异常: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 3)
                continue
            return None, None

        code = result.get("code")
        sub_code = result.get("subCode", "")
        if code != 200 or sub_code:
            print(f"  [重试 {attempt}/{MAX_RETRIES}] code={code}, subCode={sub_code}")
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 3)
                continue
            return None, None

        data = result.get("result", {}).get("data", {})
        return data.get("trades", []), data.get("scrollId", "")

    return None, None


# ============================================================
# 分页 + 时间窗口拆分 + 并行拉取
# ============================================================
def fetch_orders_with_pagination(start_time: str, end_time: str) -> list[dict]:
    all_orders, scroll_id, page = [], "", 0
    while True:
        page += 1
        print(f"  第 {page} 页, scrollId={scroll_id or '(首次)'}")
        orders, next_scroll_id = fetch_orders(start_time, end_time, scroll_id)
        if orders is None:
            print(f"  [警告] 请求失败，已获取数据将保留")
            break
        if not orders:
            break
        all_orders.extend(orders)
        print(f"  本页 {len(orders)} 条，累计 {len(all_orders)} 条")
        if not next_scroll_id:
            break
        scroll_id = next_scroll_id
        time.sleep(REQUEST_INTERVAL)
    return all_orders


def split_time_range(start_time: str, end_time: str, max_days: int = 7) -> list:
    fmt = "%Y-%m-%d %H:%M:%S"
    start_dt, end_dt = datetime.strptime(start_time, fmt), datetime.strptime(end_time, fmt)
    if (end_dt - start_dt).days < max_days:
        return [(start_time, end_time)]
    windows, current = [], start_dt
    while current < end_dt:
        win_end = min(current + timedelta(days=max_days), end_dt)
        windows.append((current.strftime(fmt), win_end.strftime(fmt)))
        current = win_end
    return windows


def _fetch_one_window(args):
    i, ws, we = args
    print(f"[窗口 {i}] {ws} ~ {we} 开始")
    orders = fetch_orders_with_pagination(ws, we)
    print(f"[窗口 {i}] 完成，获取 {len(orders)} 条")
    return orders


def fetch_all_orders() -> list[dict]:
    windows = split_time_range(START_TRADE_TIME, END_TRADE_TIME)
    print(f"时间范围: {START_TRADE_TIME} ~ {END_TRADE_TIME}")
    print(f"拆分为 {len(windows)} 个窗口，并行拉取\n")
    all_orders = []
    tasks = [(i + 1, ws, we) for i, (ws, we) in enumerate(windows)]
    with ThreadPoolExecutor(max_workers=len(windows)) as executor:
        futures = {executor.submit(_fetch_one_window, t): t[0] for t in tasks}
        for future in as_completed(futures):
            try:
                all_orders.extend(future.result())
            except Exception as e:
                print(f"[窗口 {futures[future]}] 异常: {e}")
    print(f"\n全部完成，共获取 {len(all_orders)} 个订单")
    return all_orders


# ============================================================
# 数据拍平
# ============================================================
def flatten_orders_to_wide_table(orders: list[dict]) -> pd.DataFrame:
    skip_keys = {"goodsDetail", "tradeOrderPayList", "tradeOrderColumnExt",
                 "tradeOrderAssemblyGoodsDtoList", "goodsSerial",
                 "packageDetail", "otherPaymentFees", "tradeOrderGoodsColumnExts",
                 "tradeOrderPre", "tradeOrderRefundTime"}
    rows = []
    for order in orders:
        order_common = {}
        for key, val in order.items():
            if key in skip_keys:
                continue
            if isinstance(val, (dict, list)):
                order_common[key] = json.dumps(val, ensure_ascii=False) if val else ""
            else:
                order_common[key] = val if val is not None else ""
        goods_list = order.get("goodsDetail", [])
        if not goods_list:
            rows.append({**order_common})
        else:
            for goods in goods_list:
                row = {**order_common}
                for gk, gv in goods.items():
                    if isinstance(gv, (dict, list)):
                        row[f"货品_{gk}"] = json.dumps(gv, ensure_ascii=False) if gv else ""
                    else:
                        row[f"货品_{gk}"] = gv if gv is not None else ""
                rows.append(row)
    return pd.DataFrame(rows)


# ============================================================
# 字段映射 + 自算指标
# ============================================================
def map_to_table_fields(df: pd.DataFrame) -> pd.DataFrame:
    # 1. 订单级重命名
    rename_map = {
        "tradeNo": "trade_no", "tradeId": "trade_id",
        "onlineTradeNo": "online_trade_no", "sourceTradeNo": "source_trade_no",
        "shopName": "shop_name", "shopId": "shop_id", "shopcode": "shop_code", "shopCode": "shop_code",
        "logisticName": "logistics_name", "mainPostid": "logistics_no",
        "warehouseName": "warehouse_name", "customerCode": "customer_code", "customerName": "customer_name",
        "tradeStatus": "trade_status", "tradeStatusExplain": "trade_status_explain", "tradeType": "trade_type",
        "tradeTime": "order_time", "payTime": "pay_time", "consignTime": "consign_time",
        "lastShipTime": "last_ship_time", "gmtCreate": "gmt_create", "gmtModified": "gmt_modified",
        "grossProfit": "api_gross_profit", "isDelete": "_is_delete",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # 2. 货品级重命名
    goods_rename = {
        "货品_subTradeId": "sub_trade_id", "货品_goodsNo": "goods_no", "货品_goodsName": "goods_name",
        "货品_skuNo": "sku_no", "货品_specName": "spec_name", "货品_barcode": "barcode",
        "货品_brandName": "brand_name", "货品_brandId": "brand_id",
        "货品_tradeGoodsName": "trade_goods_name", "货品_platGoodsId": "plat_goods_id",
        "货品_inventoryWarehouseName": "inventory_warehouse_name",
        "货品_refundStatus": "refund_status", "货品_isGift": "is_gift", "货品_isFit": "is_fit",
        "货品_sourceSubtradeNo": "source_sub_trade_no", "货品_actualSendCount": "actual_send_count",
        "货品_sellCount": "sales_qty", "货品_sellPrice": "sales_price", "货品_discountFee": "discount_fee",
        "货品_sellTotal": "sales_amount", "货品_cost": "cost_amount",
        "货品_shareFavourableFee": "share_favourable_fee",
        "货品_shareFavourableAfterFee": "_share_favourable_after_fee_raw",
        "货品_divideSellTotal": "divide_sell_total", "货品_shareOrderDiscountFee": "share_order_discount_fee",
        "货品_sourceTradeNo": "_goods_source_trade_no",
    }
    df = df.rename(columns={k: v for k, v in goods_rename.items() if k in df.columns})

    # 3. 缺失列兜底
    for col, default in {
        "trade_no": "", "trade_id": "", "online_trade_no": "", "source_trade_no": "",
        "shop_name": "", "shop_id": "", "shop_code": "", "logistics_name": "", "logistics_no": "",
        "warehouse_name": "", "customer_code": "", "customer_name": "",
        "trade_status": None, "trade_status_explain": "", "trade_type": "",
        "order_time": None, "pay_time": None, "consign_time": None, "last_ship_time": None,
        "gmt_create": None, "gmt_modified": None, "api_gross_profit": None, "_is_delete": 0,
        "sub_trade_id": "", "goods_no": "", "goods_name": "", "sku_no": "", "spec_name": "",
        "barcode": "", "brand_name": "", "brand_id": "", "trade_goods_name": "",
        "plat_goods_id": "", "inventory_warehouse_name": "", "refund_status": "",
        "is_gift": "", "is_fit": "", "source_sub_trade_no": "", "actual_send_count": None,
        "sales_qty": None, "sales_price": None, "discount_fee": None,
        "sales_amount": None, "cost_amount": None, "share_favourable_fee": None,
        "_share_favourable_after_fee_raw": None, "divide_sell_total": None,
        "share_order_discount_fee": None, "_goods_source_trade_no": None,
    }.items():
        if col not in df.columns:
            df[col] = default

    # 4. COALESCE
    df["online_order_no"] = df["_goods_source_trade_no"].fillna(df["online_trade_no"])
    df["display_warehouse_name"] = df["inventory_warehouse_name"].fillna(df["warehouse_name"])
    df["share_favourable_after_fee"] = (
        df["_share_favourable_after_fee_raw"].fillna(df["divide_sell_total"]).fillna(df["sales_amount"])
    )

    # 5. 自算指标
    df["allocated_unit_price"] = df["share_favourable_after_fee"] / df["sales_qty"].replace(0, np.nan)
    df.loc[df["sales_qty"].isna(), "allocated_unit_price"] = None
    df["gross_profit_amount"] = df["share_favourable_after_fee"] - df["cost_amount"]
    df.loc[df["share_favourable_after_fee"].isna() | df["cost_amount"].isna(), "gross_profit_amount"] = None
    df["gross_profit_rate"] = df["gross_profit_amount"] / df["share_favourable_after_fee"].replace(0, np.nan)
    df.loc[
        df["share_favourable_after_fee"].isna() | (df["share_favourable_after_fee"] == 0), "gross_profit_rate"] = None

    # 6. 固定字段 + 清洗
    df["cost_note"] = "待确认"
    df["data_date"] = date.today()
    df = df[df["_is_delete"] != 1].copy()

    # 7. sub_trade_id 兜底
    mask = df["sub_trade_id"].isna() | (df["sub_trade_id"].astype(str).str.strip() == "")
    df.loc[mask, "sub_trade_id"] = (
            df.loc[mask, "trade_no"].astype(str) + "_" + df.loc[mask, "goods_no"].astype(str) + "_" + df.loc[
        mask].index.astype(str)
    )

    # 8. 最终列顺序 + 中文列名
    final_columns = [
        "trade_no", "trade_id", "online_order_no", "source_trade_no", "online_trade_no",
        "shop_name", "shop_id", "shop_code", "logistics_name", "logistics_no",
        "warehouse_name", "display_warehouse_name", "customer_code", "customer_name",
        "trade_status", "trade_status_explain", "trade_type",
        "order_time", "pay_time", "consign_time", "last_ship_time", "gmt_create", "gmt_modified",
        "sub_trade_id", "goods_no", "goods_name", "sku_no", "spec_name", "barcode",
        "brand_name", "brand_id", "trade_goods_name", "plat_goods_id", "inventory_warehouse_name",
        "refund_status", "is_gift", "is_fit", "source_sub_trade_no", "actual_send_count",
        "sales_qty", "sales_price", "discount_fee", "sales_amount", "cost_amount",
        "share_favourable_fee", "share_favourable_after_fee", "divide_sell_total",
        "share_order_discount_fee", "allocated_unit_price", "cost_note",
        "gross_profit_amount", "gross_profit_rate", "api_gross_profit", "data_date",
    ]
    df = df[final_columns]

    cn_rename = {
        "trade_no": "订单编号", "trade_id": "订单ID", "online_order_no": "网店订单号",
        "source_trade_no": "来源订单号", "online_trade_no": "网店订单号_订单级",
        "shop_name": "渠道名称", "shop_id": "渠道ID", "shop_code": "渠道编码",
        "logistics_name": "物流公司", "logistics_no": "物流单号",
        "warehouse_name": "发货仓库_订单级", "display_warehouse_name": "发货仓库",
        "customer_code": "客户编号", "customer_name": "客户名称",
        "trade_status": "订单状态", "trade_status_explain": "订单状态描述", "trade_type": "订单类型",
        "order_time": "下单时间", "pay_time": "付款时间", "consign_time": "发货时间",
        "last_ship_time": "承诺发货时间", "gmt_create": "创建时间", "gmt_modified": "最后修改时间",
        "sub_trade_id": "子订单ID", "goods_no": "货品编号", "goods_name": "货品名称",
        "sku_no": "规格编号", "spec_name": "规格名称", "barcode": "货品条码",
        "brand_name": "品牌名称", "brand_id": "品牌ID", "trade_goods_name": "交易名称",
        "plat_goods_id": "商品链接ID", "inventory_warehouse_name": "货品仓库",
        "refund_status": "退款状态", "is_gift": "是否赠品", "is_fit": "是否组合装",
        "source_sub_trade_no": "来源子订单号", "actual_send_count": "实际发货数量",
        "sales_qty": "销售数量", "sales_price": "单价", "discount_fee": "优惠折扣",
        "sales_amount": "销售金额", "cost_amount": "货品成本",
        "share_favourable_fee": "分摊金额", "share_favourable_after_fee": "分摊后金额",
        "divide_sell_total": "分摊销售总额", "share_order_discount_fee": "分摊订单优惠",
        "allocated_unit_price": "分摊后单价", "cost_note": "成本口径",
        "gross_profit_amount": "毛利额", "gross_profit_rate": "毛利率",
        "api_gross_profit": "API毛利", "data_date": "数据日期",
    }
    df = df.rename(columns=cn_rename)
    return df


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print(f"吉客云销售订单大宽表导出工具  [模式: {RUN_MODE}]")
    print("=" * 60 + "\n")

    if RUN_MODE == "import":
        print("[步骤 1/3] 初始化数据库...")
        init_database(TABLE_NAME, CREATE_TABLE_SQL)

        print(f"\n[步骤 2/3] 读取 CSV: {OUTPUT_CSV}")
        df = pd.read_csv(OUTPUT_CSV, low_memory=False)
        print(f"  读取完成：{len(df)} 行, {len(df.columns)} 列")
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("").astype(str)
                df.loc[df[col].isin(["nan", "None", "NaT"]), col] = ""
        df["子订单ID"] = df["子订单ID"].astype(str)
        df.loc[df["子订单ID"].isin(["nan", "None", "NaT"]), "子订单ID"] = ""
        mask = df["子订单ID"].str.strip() == ""
        if mask.any():
            df.loc[mask, "子订单ID"] = (
                    df.loc[mask, "订单编号"].astype(str) + "_" +
                    df.loc[mask, "货品编号"].astype(str) + "_" + df.loc[mask].index.astype(str)
            )
            print(f"  补全 {mask.sum()} 条空子订单ID")

        print(f"\n[步骤 3/3] 写入 MySQL（影子表原子切换）...")
        write_to_mysql(df, TABLE_NAME, CREATE_TABLE_SQL)
    else:
        print(f"\n[步骤 1/4] 获取 API 数据...")
        orders = fetch_all_orders()
        if not orders:
            print("未获取到数据")
            return

        print(f"\n[步骤 2/4] 拍平订单数据...")
        df_raw = flatten_orders_to_wide_table(orders)
        print(f"  拍平完成：{len(df_raw)} 行, {len(df_raw.columns)} 列")

        print(f"\n[步骤 3/4] 字段映射与指标计算...")
        df = map_to_table_fields(df_raw)
        print(f"  映射完成：{len(df)} 行, {len(df.columns)} 列")
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"  CSV 已保存: {OUTPUT_CSV}")

        print(f"\n[步骤 4/4] 写入 MySQL（影子表原子切换）...")
        write_to_mysql(df, TABLE_NAME, CREATE_TABLE_SQL)

    print(f"\n{'=' * 60}")
    print(f"全部完成！MySQL: {DB_CONFIG['database']}.{TABLE_NAME}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
