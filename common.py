"""
吉客云数据导出工具 - 公共工具模块
提供签名、API 请求、MySQL 写入等通用功能
"""

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, date

import numpy as np
import pandas as pd
import pymysql
import requests

from config import (
    APP_KEY, APP_SECRET, API_URL, VERSION, CONTENT_TYPE,
    DB_CONFIG, REQUEST_INTERVAL, REQUEST_TIMEOUT, MAX_RETRIES, MYSQL_TMP_FILE,
)


# ============================================================
# 签名
# ============================================================
def generate_sign(params: dict, secret: str = APP_SECRET) -> str:
    """吉客云 API 签名算法（MD5）"""
    sorted_keys = sorted(params.keys())
    sign_str = secret
    for key in sorted_keys:
        sign_str += key + str(params[key])
    sign_str += secret
    sign_str = sign_str.lower()
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


# ============================================================
# API 请求
# ============================================================
def build_params(method: str, biz_content: str) -> dict:
    """构建完整的请求参数（含签名）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    params = {
        "appkey": APP_KEY,
        "bizcontent": biz_content,
        "contenttype": CONTENT_TYPE,
        "method": method,
        "timestamp": timestamp,
        "version": VERSION,
    }
    params["sign"] = generate_sign(params)
    return params


def api_request(method: str, biz_content: str, max_retries: int = MAX_RETRIES) -> dict | None:
    """
    通用 API 请求（带重试）
    成功返回 result dict，失败返回 None
    """
    for attempt in range(1, max_retries + 1):
        params = build_params(method, biz_content)

        try:
            resp = requests.post(API_URL, data=params, timeout=REQUEST_TIMEOUT)
            result = resp.json()
        except Exception as e:
            wait = attempt * 3
            print(f"    [重试 {attempt}/{max_retries}] 请求异常: {e}")
            if attempt < max_retries:
                time.sleep(wait)
                continue
            return None

        code = result.get("code")
        if code != 200:
            wait = attempt * 3
            sub_code = result.get("subCode", "")
            msg = result.get("msg", "")
            print(f"    [重试 {attempt}/{max_retries}] code={code}, subCode={sub_code}, msg={msg}")
            if attempt < max_retries:
                time.sleep(wait)
                continue
            return None

        return result

    return None


def sleep_between_requests():
    """请求间隔"""
    time.sleep(REQUEST_INTERVAL)


# ============================================================
# MySQL 写入
# ============================================================
def init_database(create_table_sql: str, table_name: str):
    """创建数据库和表（幂等操作）"""
    conn = pymysql.connect(
        host=DB_CONFIG["host"], port=DB_CONFIG["port"],
        user=DB_CONFIG["user"], password=DB_CONFIG["password"],
        charset=DB_CONFIG["charset"], local_infile=True,
    )
    cursor = conn.cursor()
    cursor.execute("SET GLOBAL local_infile = 1")
    cursor.execute(
        "CREATE DATABASE IF NOT EXISTS dw_ods "
        "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_0900_ai_ci"
    )
    cursor.execute("USE dw_ods")
    cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
    cursor.execute(create_table_sql)
    conn.commit()
    print(f"[完成] 数据库 dw_ods 和表 {table_name} 已就绪")
    cursor.close()
    conn.close()


def write_to_mysql(df: pd.DataFrame, table_name: str, date_col: str = "数据日期"):
    """
    将 DataFrame 写入 MySQL（LOAD DATA LOCAL INFILE）
    - 自动处理 NaN/inf → NULL
    - 按 date_col 删除当日数据后重新导入
    """
    col_list = df.columns.tolist()
    df_clean = df.copy()

    # 清洗数据
    for col_name in col_list:
        series = df_clean[col_name]
        if series.dtype == object:
            df_clean[col_name] = series.fillna("\\N").astype(str)
            df_clean.loc[df_clean[col_name].isin(["nan", "None", "NaT", ""]), col_name] = "\\N"
        elif pd.api.types.is_numeric_dtype(series):
            df_clean[col_name] = series.apply(
                lambda x: "\\N" if pd.isna(x) or (isinstance(x, float) and np.isinf(x)) else x
            )

    # 写入临时 CSV
    tmp_file = os.path.join(tempfile.gettempdir(), MYSQL_TMP_FILE)
    df_clean.to_csv(tmp_file, index=False, header=False, encoding="utf-8")
    print(f"  临时文件：{tmp_file}（{len(df_clean)} 行）")

    # MySQL 导入
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    columns = df_clean.columns.tolist()
    col_names = ", ".join([f"`{c}`" for c in columns])

    # 删除当日数据
    if date_col in columns:
        today = date.today()
        cursor.execute(f"DELETE FROM `{table_name}` WHERE `{date_col}` = %s", (today,))
        print(f"  已清除 {today} 的旧数据")

    tmp_path = tmp_file.replace("\\", "/")
    cursor.execute(f"""
        LOAD DATA LOCAL INFILE '{tmp_path}'
        INTO TABLE `{table_name}`
        CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ',' ENCLOSED BY '"'
        LINES TERMINATED BY '\\n'
        ({col_names})
    """)
    affected = cursor.rowcount
    conn.commit()

    print(f"[完成] 导入 {affected} 行到 {DB_CONFIG['database']}.{table_name}")

    cursor.close()
    conn.close()

    try:
        os.remove(tmp_file)
    except OSError:
        pass
