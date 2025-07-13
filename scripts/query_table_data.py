#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMS Viewer - 数据表查询脚本
用于查询MongoDB中指定表的数据
"""

import sys
import json
import os
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import traceback

def json_serializer(obj):
    """JSON序列化器，处理MongoDB特殊类型"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def get_database_connection():
    """获取数据库连接"""
    try:
        # 导入数据库配置模块
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from database_config import get_database
        
        db = get_database()
        if db is None:
            raise Exception("无法连接到数据库")
        return db
    except Exception as e:
        raise Exception(f"数据库连接失败: {str(e)}")

def query_table_data(table_name, limit=100):
    """查询表数据"""
    try:
        db = get_database_connection()
        collection = db[table_name]
        
        # 检查集合是否存在
        if table_name not in db.list_collection_names():
            return {
                'error': f'表 {table_name} 不存在',
                'data': []
            }
        
        # 获取文档总数
        total_count = collection.count_documents({})
        
        if total_count == 0:
            return {
                'message': f'表 {table_name} 暂无数据',
                'data': [],
                'total': 0
            }
        
        # 查询数据，限制返回数量，包含_id字段
        cursor = collection.find({}).limit(limit)
        documents = list(cursor)
        
        data = documents
        
        return {
            'data': data,
            'total': total_count,
            'displayed': len(data),
            'limit': limit
        }
        
    except Exception as e:
        return {
            'error': f'查询失败: {str(e)}',
            'data': []
        }

def query_materials_for_view():
    """专门为VS Code树视图查询物料列表"""
    try:
        db = get_database_connection()
        collection = db["materials"]
        
        # 只查询需要展示的字段，并按物料编码排序
        cursor = collection.find(
            {}, 
            {'_id': 1, 'material_code': 1, 'material_name': 1, 'material_model': 1, 'unit': 1}
        ).sort("material_code", 1)
        
        materials = list(cursor)
        
        return { 'data': materials }
        
    except Exception as e:
        return {
            'error': f'物料查询失败: {str(e)}',
            'data': []
        }


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="IMS Viewer - 数据查询脚本")
    parser.add_argument('--type', type=str, default='table', help='查询类型 (table, materials)')
    parser.add_argument('--name', type=str, help='要查询的表名')
    parser.add_argument('--limit', type=int, default=100, help='返回记录数限制')
    
    args = parser.parse_args()

    try:
        result = {}
        if args.type == 'table':
            if not args.name:
                raise ValueError("查询类型为'table'时,必须提供--name参数")
            result = query_table_data(args.name, args.limit)
        elif args.type == 'materials':
            result = query_materials_for_view()
        else:
            result = {'error': f'未知的查询类型: {args.type}'}
        
        # 输出JSON结果
        print(json.dumps(result, ensure_ascii=False, default=json_serializer))
        
    except Exception as e:
        error_result = {
            'error': f'脚本执行失败: {str(e)}',
            'data': [],
            'traceback': traceback.format_exc()
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()