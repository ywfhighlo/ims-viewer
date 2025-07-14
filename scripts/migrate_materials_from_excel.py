#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料迁移脚本
从Excel文件中读取物料信息，并将其导入到MongoDB的materials集合中。
"""

import pandas as pd
import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from vscode_config_reader import get_data_directory

# --- 配置 ---
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = os.environ.get('IMS_DB_NAME', 'ims_viewer')
MATERIALS_COLLECTION = "materials"
# EXCEL_FILE将在运行时动态获取
SHEET_NAME = "进货入库明细表"

# Excel中的列名
COL_CODE = "进货物料编码"
COL_NAME = "进货物料名称"
COL_SPEC = "进货规格型号"
COL_UNIT = "单位"

def get_db_client():
    """获取MongoDB数据库客户端"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except (ConnectionFailure, Exception) as e:
        print(f"❌ 数据库连接失败: {e}", file=sys.stderr)
        return None

def migrate_materials():
    """执行物料迁移"""
    print("--- 开始物料迁移 ---")
    
    # 1. 连接数据库
    client = get_db_client()
    if not client:
        sys.exit(1)
    db = client[DATABASE_NAME]
    collection = db[MATERIALS_COLLECTION]
    print(f"✅ 数据库连接成功，目标集合: '{MATERIALS_COLLECTION}'")
    
    # 2. 读取Excel文件
    data_dir = get_data_directory()
    excel_file = os.path.join(data_dir, "imsviewer.xlsx")
    if not os.path.exists(excel_file):
        print(f"❌ Excel文件不存在: {excel_file}", file=sys.stderr)
        sys.exit(1)
        
    try:
        df = pd.read_excel(excel_file, sheet_name=SHEET_NAME, header=1)
        print(f"✅ 成功读取Excel文件 '{excel_file}', 工作表: '{SHEET_NAME}'")
    except Exception as e:
        print(f"❌ 读取Excel失败: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 3. 提取并去重物料信息
    material_cols = [COL_CODE, COL_NAME, COL_SPEC, COL_UNIT]
    if not all(col in df.columns for col in material_cols):
        print(f"❌ Excel工作表中缺少必要的列，需要: {material_cols}", file=sys.stderr)
        sys.exit(1)
        
    unique_materials_df = df[material_cols].drop_duplicates().dropna(subset=[COL_CODE])
    print(f"🔍 发现 {len(unique_materials_df)} 条独立物料信息。")
    
    # 4. 遍历并插入数据库
    inserted_count = 0
    skipped_count = 0
    
    for _, row in unique_materials_df.iterrows():
        material_code = row[COL_CODE]
        
        # 检查物料是否已存在
        if collection.count_documents({"material_code": material_code}) > 0:
            # print(f"⏭️  跳过已存在的物料: {material_code}")
            skipped_count += 1
            continue
            
        # 准备要插入的文档
        material_doc = {
            "material_code": material_code,
            "material_name": row[COL_NAME],
            "material_model": row[COL_SPEC],
            "unit": row[COL_UNIT],
            "source": "legacy_excel_import" # 标记数据来源
        }
        
        try:
            collection.insert_one(material_doc)
            print(f"➕ 新增物料: {material_code} - {row[COL_NAME]}")
            inserted_count += 1
        except Exception as e:
            print(f"❌ 插入物料 '{material_code}' 时出错: {e}", file=sys.stderr)
            
    print("\n--- 物料迁移完成 ---")
    print(f"报告:")
    print(f"  - 新增物料: {inserted_count} 条")
    print(f"  - 跳过重复: {skipped_count} 条")
    
    client.close()
    print("✅ 数据库连接已关闭。")

if __name__ == "__main__":
    migrate_materials()