"""
吉客云开放平台 - 销售订单大宽表导出脚本
=========================================
功能：
  1. 调用 oms.trade.fullinfoget 接口获取销售订单数据
  2. 自动拆分超过 7 天的时间范围，分段请求后合并
  3. 使用 scrollId 游标分页，自动循环获取所有订单
  4. 将订单数据与商品明细拍平，生成大宽表 CSV

依赖安装：
  pip install requests pandas
"""

import hashlib
import json
import time
from datetime import datetime, timedelta


import pandas as pd
import requests

# ============================================================
# 一、配置区（集中修改此处）
# ============================================================
APP_KEY = "16151323"
APP_SECRET = "b89cb27cc0dc459db2b7f19b3675ba21"
API_URL = "https://open.jackyun.com/open/openapi/do"
METHOD = "oms.trade.fullinfoget"
VERSION = "v1.0"
CONTENT_TYPE = "json"

# 查询时间范围（格式：yyyy-MM-dd HH:mm:ss）
START_TRADE_TIME = "2026-05-29 00:00:00"
END_TRADE_TIME = "2026-06-04 23:59:59"

# 输出文件
OUTPUT_CSV = "sales_order_wide_table.csv"

# 每页条数（最大200）
PAGE_SIZE = 200

# fields 参数：全量字段（根据 API 文档整理）
FIELDS = ",".join([
    # ---- 订单级字段 ----
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
    "departName", "agentShopName", "platFlags",
    "scrollId",

    # ---- 货品明细字段（goodsDetail.xxx）----
    "goodsDetail.goodsNo", "goodsDetail.goodsName", "goodsDetail.specName",
    "goodsDetail.barcode", "goodsDetail.outerId",
    "goodsDetail.sellCount", "goodsDetail.sellPrice", "goodsDetail.sellTotal",
    "goodsDetail.unit", "goodsDetail.cost", "goodsDetail.taxFee", "goodsDetail.taxRate",
    "goodsDetail.discountFee", "goodsDetail.discountTotal", "goodsDetail.discountPoint",
    "goodsDetail.shareFavourableFee", "goodsDetail.shareFavourableAfterFee",
    "goodsDetail.shareOrderDiscountFee", "goodsDetail.shareOrderPlatDiscountFee",
    "goodsDetail.goodsPlatDiscountFee",
    "goodsDetail.divideSellTotal",
    "goodsDetail.estimateWeight", "goodsDetail.estimateGoodsVolume",
    "goodsDetail.isFit", "goodsDetail.isGift", "goodsDetail.isPresell",
    "goodsDetail.goodsMemo", "goodsDetail.cateName", "goodsDetail.brandName",
    "goodsDetail.goodsTags",
    "goodsDetail.customerPrice", "goodsDetail.customerTotal",
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
    "goodsDetail.baseUnitSellCount",
    "goodsDetail.refundStatus",
])


# ============================================================
# 二、签名生成函数
# ============================================================
def generate_sign(params: dict, secret: str) -> str:
    """
    吉客云 API 签名算法（MD5）

    关键：拼接后的整个字符串要转小写，再 MD5
    """
    sorted_keys = sorted(params.keys())

    sign_str = secret
    for key in sorted_keys:
        sign_str += key + str(params[key])
    sign_str += secret

    # 整个签名串转小写！
    sign_str = sign_str.lower()
    sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    return sign


# ============================================================
# 三、构建 bizcontent（包含所有可选字段，与官方工具一致）
# ============================================================
def build_biz_content(
    start_time: str,
    end_time: str,
    scroll_id: str = "",
) -> str:
    """
    构建 bizcontent JSON 字符串
    字段名用驼峰（API 实际返回的格式），签名时 generate_sign 会整体转小写
    """
    biz = {
        "startTradeTime": start_time,
        "endTradeTime": end_time,
        "fields": FIELDS,
        "pageSize": PAGE_SIZE,       # 数字，不是字符串
        "scrollId": scroll_id,
    }
    return json.dumps(biz, ensure_ascii=False, separators=(",", ":"))


# ============================================================
# 四、单次请求函数
# ============================================================
def fetch_orders(
    start_time: str,
    end_time: str,
    scroll_id: str = "",
) -> tuple[list[dict], str]:
    """
    调用 oms.trade.fullinfoget 接口获取一页订单数据
    """
    biz_content_json = build_biz_content(start_time, end_time, scroll_id)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    params = {
        "appkey": APP_KEY,
        "bizcontent": biz_content_json,
        "contenttype": CONTENT_TYPE,
        "method": METHOD,
        "timestamp": timestamp,
        "version": VERSION,
    }

    sign = generate_sign(params, APP_SECRET)
    params["sign"] = sign

    try:
        resp = requests.post(API_URL, data=params, timeout=30)
        result = resp.json()
    except Exception as e:
        print(f"  [错误] 请求异常: {e}")
        return [], ""

    code = result.get("code")
    sub_code = result.get("subCode", "")
    msg = result.get("msg", "")

    if code != 200 or sub_code:
        print(f"  [错误] code={code}, subCode={sub_code}, msg={msg}")
        return [], ""

    data = result.get("result", {}).get("data", {})
    trades = data.get("trades", [])
    next_scroll_id = data.get("scrollId", "")

    print(f"  [成功] 获取 {len(trades)} 条订单")
    return trades, next_scroll_id


# ============================================================
# 五、分页循环函数（单个时间窗口内）
# ============================================================
def fetch_orders_with_pagination(
        start_time: str,
        end_time: str,
) -> list[dict]:
    """
    在一个时间窗口内，使用 scrollId 游标分页获取所有订单
    """
    all_orders = []
    scroll_id = ""
    page = 0

    while True:
        page += 1
        label = scroll_id if scroll_id else "(首次)"
        print(f"  第 {page} 页, scrollId={label}")

        orders, next_scroll_id = fetch_orders(start_time, end_time, scroll_id)

        if not orders:
            print("  无更多数据，分页结束")
            break

        all_orders.extend(orders)
        print(f"  本页 {len(orders)} 条，累计 {len(all_orders)} 条")

        if not next_scroll_id:
            print("  scrollId 为空，分页结束")
            break

        scroll_id = next_scroll_id
        time.sleep(1.2)  # 避免触发限流（1次/秒）

    return all_orders


# ============================================================
# 六、时间拆分函数
# ============================================================
def split_time_range(
        start_time: str,
        end_time: str,
        max_days: int = 7,
) -> list[tuple[str, str]]:
    """
    如果时间跨度超过 max_days 天，自动拆分成多个时间段
    """
    fmt = "%Y-%m-%d %H:%M:%S"
    start_dt = datetime.strptime(start_time, fmt)
    end_dt = datetime.strptime(end_time, fmt)

    delta = end_dt - start_dt
    if delta.days < max_days:
        return [(start_time, end_time)]

    windows = []
    current = start_dt
    while current < end_dt:
        window_end = min(current + timedelta(days=max_days), end_dt)
        windows.append((current.strftime(fmt), window_end.strftime(fmt)))
        current = window_end

    return windows


# ============================================================
# 七、完整获取流程（拆分 + 分页）
# ============================================================
def fetch_all_orders() -> list[dict]:
    """
    完整流程：拆分时间范围 → 逐段分页获取 → 合并结果
    """
    windows = split_time_range(START_TRADE_TIME, END_TRADE_TIME)
    print(f"时间范围: {START_TRADE_TIME} ~ {END_TRADE_TIME}")
    print(f"拆分为 {len(windows)} 个查询窗口（每个不超过 7 天）\n")

    all_orders = []
    for i, (ws, we) in enumerate(windows, 1):
        print(f"[窗口 {i}/{len(windows)}] {ws} ~ {we}")
        orders = fetch_orders_with_pagination(ws, we)
        all_orders.extend(orders)
        print(f"  窗口完成，获取 {len(orders)} 条\n")

    print(f"全部完成，共获取 {len(all_orders)} 个订单")
    return all_orders


# ============================================================
# 八、数据拍平函数
# ============================================================
def flatten_orders_to_wide_table(orders: list[dict]) -> pd.DataFrame:
    """
    将订单 JSON 数据拍平为大宽表（自动提取所有字段）

    核心逻辑：
      - 自动提取订单级字段（排除 goodsDetail 等嵌套对象/数组）
      - 一个订单有 N 个商品 → 输出 N 行
      - goodsDetail 内的字段自动加前缀 "货品_"
    """
    rows = []

    for order in orders:
        # ---- 自动提取订单级字段（跳过数组和嵌套对象） ----
        order_common = {}
        skip_keys = {"goodsDetail", "tradeOrderPayList", "tradeOrderColumnExt",
                     "tradeOrderAssemblyGoodsDtoList", "goodsSerial",
                     "packageDetail", "otherPaymentFees", "tradeOrderGoodsColumnExts",
                     "tradeOrderPre", "tradeOrderRefundTime"}
        for key, val in order.items():
            if key in skip_keys:
                continue
            if isinstance(val, (dict, list)):
                # 嵌套对象/数组转 JSON 字符串
                order_common[key] = json.dumps(val, ensure_ascii=False) if val else ""
            else:
                order_common[key] = val if val is not None else ""

        # ---- 遍历 goodsDetail，逐条拍平 ----
        goods_list = order.get("goodsDetail", [])
        if not goods_list:
            row = {**order_common}
            rows.append(row)
        else:
            for goods in goods_list:
                row = {**order_common}
                for gk, gv in goods.items():
                    if isinstance(gv, (dict, list)):
                        row[f"货品_{gk}"] = json.dumps(gv, ensure_ascii=False) if gv else ""
                    else:
                        row[f"货品_{gk}"] = gv if gv is not None else ""
                rows.append(row)

    df = pd.DataFrame(rows)
    return df


# ============================================================
# 九、主函数
# ============================================================
def main():
    """
    主流程：获取数据 → 拍平 → 输出 CSV
    """
    print("=" * 60)
    print("吉客云销售订单大宽表导出工具")
    print("=" * 60 + "\n")

    orders = fetch_all_orders()

    if not orders:
        print("\n未获取到任何订单数据，请检查配置后重试。")
        return

    print("\n正在将订单数据拍平为大宽表...")
    df = flatten_orders_to_wide_table(orders)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 30)
    print(f"\n大宽表预览（共 {len(df)} 行, {len(df.columns)} 列）：")
    print("-" * 60)
    print(df.head(10).to_string(index=False))
    if len(df) > 10:
        print(f"... 省略 {len(df) - 10} 行")

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[完成] CSV 已保存至: {OUTPUT_CSV}")
    print(f"  总行数: {len(df)}")
    print(f"  总列数: {len(df.columns)}")


if __name__ == "__main__":
    main()
