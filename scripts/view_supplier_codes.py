#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看供应商编码脚本
显示所有供应商及其编码
"""

import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# --- 数据库配置 ---
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = os.environ.get('IMS_DB_NAME', 'ims_viewer')
SUPPLIERS_COLLECTION = "suppliers"

def get_db_client():
    """获取MongoDB数据库客户端"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except (ConnectionFailure, Exception) as e:
        print(f"❌ 数据库连接失败: {e}", file=sys.stderr)
        return None

def list_supplier_codes(db):
    """
    列出所有供应商及其编码
    """
    collection = db[SUPPLIERS_COLLECTION]
    
    # 查询所有供应商
    suppliers = list(collection.find(
        {},
        {"supplier_code": 1, "supplier_name": 1}
    ).sort("supplier_name", 1))
    
    if not suppliers:
        print("❌ 没有找到供应商数据")
        return
    
    # 统计编码情况
    coded_suppliers = [s for s in suppliers if "supplier_code" in s and s["supplier_code"]]
    uncoded_suppliers = [s for s in suppliers if "supplier_code" not in s or not s["supplier_code"]]
    
    print(f"\n📋 供应商编码统计:")
    print(f"总供应商数: {len(suppliers)}")
    print(f"已分配编码: {len(coded_suppliers)}")
    print(f"未分配编码: {len(uncoded_suppliers)}")
    
    if coded_suppliers:
        print(f"\n✅ 已分配编码的供应商 (共 {len(coded_suppliers)} 个):")
        print("-" * 80)
        # 按编码排序
        coded_suppliers.sort(key=lambda x: x.get("supplier_code", "99"))
        for supplier in coded_suppliers:
            code = supplier.get("supplier_code", "--")
            name = supplier.get("supplier_name", "未知供应商")
            print(f"{code}: {name}")
    
    if uncoded_suppliers:
        print(f"\n⚠️ 未分配编码的供应商 (共 {len(uncoded_suppliers)} 个):")
        print("-" * 80)
        for supplier in uncoded_suppliers[:10]:  # 只显示前10个
            name = supplier.get("supplier_name", "未知供应商")
            print(f"--: {name}")
        if len(uncoded_suppliers) > 10:
            print(f"... 还有 {len(uncoded_suppliers) - 10} 个未显示")

def main():
    """
    主函数
    """
    print("=== 供应商编码查看工具 ===")
    
    client = get_db_client()
    if not client:
        sys.exit(1)
        
    db = client[DATABASE_NAME]
    
    list_supplier_codes(db)
    
    client.close()
    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()