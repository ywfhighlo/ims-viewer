#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
测试MongoDB连接是否正常
"""

import sys
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# 导入数据库配置模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database_config import get_database_config, get_db_client, get_database_name, test_connection

def test_mongodb_connection():
    """
    测试MongoDB连接
    """
    try:
        print("=== MongoDB连接测试 ===")
        
        # 获取数据库配置
        config = get_database_config()
        print(f"连接URI: {config['mongo_uri']}")
        print(f"数据库名: {config['database_name']}")
        if config['username']:
            print(f"用户名: {config['username']}")
            print(f"认证数据库: {config['auth_database']}")
        
        # 创建MongoDB客户端
        client = get_db_client()
        if client is None:
            return False
        
        print("✅ MongoDB服务器连接成功")
        
        # 获取数据库
        DATABASE_NAME = get_database_name()
        db = client[DATABASE_NAME]
        
        # 列出所有集合
        collections = db.list_collection_names()
        print(f"\n数据库 '{DATABASE_NAME}' 中的集合:")
        if collections:
            for i, collection in enumerate(collections, 1):
                count = db[collection].count_documents({})
                print(f"  {i}. {collection} ({count} 条记录)")
        else:
            print("  (暂无集合)")
        
        # 测试写入权限
        print("\n测试写入权限...")
        test_collection = db['_connection_test']
        test_doc = {"test": "connection", "timestamp": "2024-01-01"}
        result = test_collection.insert_one(test_doc)
        print(f"✅ 写入测试成功，文档ID: {result.inserted_id}")
        
        # 清理测试数据
        test_collection.delete_one({"_id": result.inserted_id})
        print("✅ 测试数据已清理")
        
        client.close()
        print("\n=== 数据库连接测试完成 ===")
        return True
        
    except ConnectionFailure as e:
        print(f"❌ MongoDB连接失败: {e}")
        print("请检查:")
        print("  1. MongoDB服务是否已启动")
        print("  2. 连接URI是否正确")
        print("  3. 网络连接是否正常")
        return False
        
    except ServerSelectionTimeoutError as e:
        print(f"❌ 服务器选择超时: {e}")
        print("请检查:")
        print("  1. MongoDB服务是否在指定端口运行")
        print("  2. 防火墙设置是否阻止连接")
        return False
        
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

def check_dependencies():
    """
    检查依赖包是否已安装
    """
    try:
        import pymongo
        print(f"✅ pymongo版本: {pymongo.version}")
        return True
    except ImportError:
        print("❌ 缺少pymongo依赖包")
        print("请运行: pip install pymongo")
        return False

def main():
    """
    主函数
    """
    print("IMS Viewer - 数据库连接测试")
    print("=" * 40)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 测试连接
    if test_mongodb_connection():
        print("\n🎉 所有测试通过！数据库连接正常。")
        sys.exit(0)
    else:
        print("\n💥 测试失败！请检查MongoDB配置。")
        sys.exit(1)

if __name__ == "__main__":
    main()