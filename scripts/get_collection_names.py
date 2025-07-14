#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMS Viewer - 获取所有集合名称的脚本
"""

import sys
import json
import os
from pymongo import MongoClient

def get_database_connection():
    """获取数据库连接"""
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from database_config import get_database
        
        db = get_database()
        if db is None:
            raise Exception("无法连接到数据库")
        return db
    except Exception as e:
        raise Exception(f"数据库连接失败: {str(e)}")

def get_collection_names():
    """获取所有集合的名称"""
    try:
        db = get_database_connection()
        collection_names = db.list_collection_names()
        return {'collections': collection_names}
    except Exception as e:
        return {'error': str(e)}

def main():
    """主函数"""
    try:
        result = get_collection_names()
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'error': f'脚本执行失败: {str(e)}'}))
        sys.exit(1)

if __name__ == '__main__':
    main()