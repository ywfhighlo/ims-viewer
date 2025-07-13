#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
供应商编码分配脚本
为现有供应商分配编码（01-99）
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

def assign_supplier_codes(db):
    """
    为现有供应商分配编码（01-99）
    按供应商名称排序分配编码以保持一致性
    """
    collection = db[SUPPLIERS_COLLECTION]
    
    # 获取所有供应商，按名称排序
    suppliers = list(collection.find({}).sort("supplier_name", 1))
    
    if not suppliers:
        print("❌ 没有找到供应商数据")
        return False
    
    if len(suppliers) > 99:
        print(f"⚠️ 警告: 供应商数量({len(suppliers)})超过99个，只能为前99个分配编码")
        suppliers = suppliers[:99]
    
    print(f"📋 开始为 {len(suppliers)} 个供应商分配编码...")
    
    updated_count = 0
    for index, supplier in enumerate(suppliers, 1):
        supplier_code = f"{index:02d}"
        supplier_name = supplier.get("supplier_name", "未知供应商")
        
        # 调试输出
        if index <= 3:  # 只显示前3个供应商的详细信息
            print(f"🔍 调试: 供应商 {index} - {supplier}")
        
        try:
            # 更新供应商编码
            result = collection.update_one(
                {"_id": supplier["_id"]},
                {"$set": {"supplier_code": supplier_code}}
            )
            
            if result.modified_count > 0:
                print(f"✅ {supplier_code}: {supplier_name}")
                updated_count += 1
            else:
                print(f"⚠️ {supplier_code}: {supplier_name} (未更新)")
                
        except Exception as e:
            print(f"❌ 更新供应商 {supplier_name} 失败: {e}")
    
    print(f"\n📊 编码分配完成: 成功更新 {updated_count} 个供应商")
    return updated_count > 0

def list_supplier_codes(db):
    """
    列出所有供应商及其编码
    """
    collection = db[SUPPLIERS_COLLECTION]
    
    suppliers = list(collection.find(
        {"supplier_code": {"$exists": True}},
        {"supplier_code": 1, "supplier_name": 1}
    ).sort("supplier_code", 1))
    
    if not suppliers:
        print("❌ 没有找到已分配编码的供应商")
        return
    
    print(f"\n📋 供应商编码列表 (共 {len(suppliers)} 个):")
    print("-" * 60)
    for supplier in suppliers:
        code = supplier.get("supplier_code", "--")
        name = supplier.get("supplier_name", "未知供应商")
        print(f"{code}: {name}")

def main():
    """
    主函数
    """
    print("=== 供应商编码分配工具 ===")
    
    client = get_db_client()
    if not client:
        sys.exit(1)
        
    db = client[DATABASE_NAME]
    
    # 检查是否已有供应商编码
    existing_codes = db[SUPPLIERS_COLLECTION].count_documents({"supplier_code": {"$exists": True}})
    
    if existing_codes > 0:
        print(f"⚠️ 发现 {existing_codes} 个供应商已有编码")
        choice = input("是否重新分配所有编码? (y/N): ").strip().lower()
        if choice != 'y':
            print("📋 显示现有编码:")
            list_supplier_codes(db)
            client.close()
            return
    
    # 分配编码
    success = assign_supplier_codes(db)
    
    if success:
        print("\n📋 编码分配结果:")
        list_supplier_codes(db)
    
    client.close()
    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()