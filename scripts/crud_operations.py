#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRUD操作脚本
用于处理数据库表的增删改查操作
"""

import sys
import os
import json
import argparse
from bson import ObjectId
from datetime import datetime

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_database_connection():
    """获取数据库连接"""
    try:
        from database_config import get_database
        db = get_database()
        if db is None:
            raise Exception("无法连接到数据库")
        return db
    except Exception as e:
        raise Exception(f"数据库连接失败: {str(e)}")

def add_record(table_name, data):
    """添加记录"""
    try:
        db = get_database_connection()
        collection = db[table_name]
        
        # 添加创建时间
        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        
        # 插入记录
        result = collection.insert_one(data)
        
        return {
            'success': True,
            'message': '记录添加成功',
            'data': {'_id': str(result.inserted_id)}
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'添加记录失败: {str(e)}'
        }

def update_record(table_name, data):
    """更新记录"""
    try:
        db = get_database_connection()
        collection = db[table_name]
        
        # 提取_id
        record_id = data.pop('_id', None)
        if not record_id:
            return {
                'success': False,
                'message': '缺少记录ID'
            }
        
        # 添加更新时间
        data['updated_at'] = datetime.now()
        
        # 更新记录
        result = collection.update_one(
            {'_id': ObjectId(record_id)},
            {'$set': data}
        )
        
        if result.matched_count == 0:
            return {
                'success': False,
                'message': '未找到要更新的记录'
            }
        
        return {
            'success': True,
            'message': '记录更新成功',
            'data': {'modified_count': result.modified_count}
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'更新记录失败: {str(e)}'
        }

def delete_record(table_name, data):
    """删除记录"""
    try:
        db = get_database_connection()
        collection = db[table_name]
        
        # 提取_id
        record_id = data.get('_id')
        if not record_id:
            return {
                'success': False,
                'message': '缺少记录ID'
            }
        
        # 删除记录
        result = collection.delete_one({'_id': ObjectId(record_id)})
        
        if result.deleted_count == 0:
            return {
                'success': False,
                'message': '未找到要删除的记录'
            }
        
        return {
            'success': True,
            'message': '记录删除成功',
            'data': {'deleted_count': result.deleted_count}
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'删除记录失败: {str(e)}'
        }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CRUD操作脚本")
    parser.add_argument('--table', type=str, required=True, help='表名')
    parser.add_argument('--operation', type=str, required=True, 
                       choices=['add', 'update', 'delete'], help='操作类型')
    parser.add_argument('--data', type=str, required=True, help='操作数据(JSON格式)')
    
    args = parser.parse_args()
    
    try:
        # 解析数据
        data = json.loads(args.data)
        
        # 根据操作类型执行相应操作
        if args.operation == 'add':
            result = add_record(args.table, data)
        elif args.operation == 'update':
            result = update_record(args.table, data)
        elif args.operation == 'delete':
            result = delete_record(args.table, data)
        else:
            result = {
                'success': False,
                'message': f'未知的操作类型: {args.operation}'
            }
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, default=str))
        
    except json.JSONDecodeError as e:
        result = {
            'success': False,
            'message': f'数据格式错误: {str(e)}'
        }
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        result = {
            'success': False,
            'message': f'操作失败: {str(e)}'
        }
        print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()