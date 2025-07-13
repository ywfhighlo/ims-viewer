#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证数据导入结果
"""

import json
import os
from pymongo import MongoClient
from vscode_config_reader import get_vscode_config, get_data_directory, get_mongo_config

def main():
    # 获取MongoDB配置
    mongo_config = get_mongo_config()
    
    # 构建MongoDB连接URI
    if mongo_config['username'] and mongo_config['password']:
        auth_part = f"{mongo_config['username']}:{mongo_config['password']}@"
        auth_db_part = f"?authSource={mongo_config['auth_database']}"
    else:
        auth_part = ""
        auth_db_part = ""
    
    # 从URI中提取主机和端口
    uri_base = mongo_config['uri'].rstrip('/')
    if not uri_base.startswith('mongodb://'):
        uri_base = f"mongodb://{uri_base}"
    
    mongo_uri = f"{uri_base.replace('mongodb://', f'mongodb://{auth_part}')}{auth_db_part}"
    
    client = MongoClient(mongo_uri)
    db = client[mongo_config['database_name']]
    
    print("=== 数据导入验证报告 ===")
    print(f"数据库: {mongo_config['database_name']}")
    print()
    
    # 检查集合数量
    collections = db.list_collection_names()
    print(f"集合总数: {len(collections)}")
    for collection in collections:
        count = db[collection].count_documents({})
        print(f"  {collection}: {count} 条记录")
    
    print("\n=== 标准编码应用示例 ===")
    
    # 检查materials表的标准编码
    materials = list(db.materials.find({}, {
        'material_code': 1, 
        'original_material_code': 1, 
        'material_name': 1, 
        'standard_code_applied': 1,
        '_id': 0
    }).limit(5))
    
    for m in materials:
        original = m.get('original_material_code', 'N/A')
        standard = m.get('material_code', 'N/A')
        name = m.get('material_name', 'N/A')
        applied = m.get('standard_code_applied', False)
        print(f"{original} -> {standard} ({name}) [应用: {applied}]")
    
    print("\n=== 标准编码统计 ===")
    
    # 统计各表的标准编码应用情况
    tables_with_codes = ['materials', 'purchase_params', 'purchase_inbound', 'sales_outbound', 'inventory_stats']
    
    for table in tables_with_codes:
        if table in collections:
            total = db[table].count_documents({})
            mapped = db[table].count_documents({'standard_code_applied': True})
            unmapped = db[table].count_documents({'standard_code_applied': False})
            
            if total > 0:
                mapped_percent = (mapped / total) * 100
                print(f"{table}: {mapped}/{total} ({mapped_percent:.1f}%) 已应用标准编码")
    
    client.close()
    print("\n验证完成!")

if __name__ == "__main__":
    main()