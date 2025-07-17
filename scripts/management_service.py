#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理视图服务组件
提供基础数据的CRUD管理功能
"""

import sys
import os
import json
from bson import ObjectId
from datetime import datetime

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_database
from scripts.cache_invalidation import CacheInvalidationManager
from scripts.data_validator import DataValidator

class ManagementService:
    def __init__(self):
        self.db = get_database()
        if self.db is None:
            raise Exception("无法连接到数据库")
        self.cache_invalidator = CacheInvalidationManager()
        self.validator = DataValidator()

    def get_customers(self, filters: dict, page: int, page_size: int) -> dict:
        """获取客户列表"""
        try:
            collection = self.db['customers']
            
            query = {}
            if filters:
                for key, value in filters.items():
                    if value:
                        query[key] = {'$regex': value, '$options': 'i'}

            total = collection.count_documents(query)
            
            cursor = collection.find(query).skip((page - 1) * page_size).limit(page_size)
            
            result = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                result.append(doc)
                
            return {
                'success': True,
                'data': result,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'获取客户列表失败: {str(e)}'
            }

    def create_customer(self, customer_data: dict) -> dict:
        """创建客户"""
        try:
            validation_result = self.validator.validate('customers', customer_data)
            if not validation_result['is_valid']:
                return {'success': False, 'message': '数据验证失败', 'errors': validation_result['errors']}

            collection = self.db['customers']
            
            now = datetime.now()
            customer_data['created_at'] = now
            customer_data['updated_at'] = now
            
            result = collection.insert_one(customer_data)
            
            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('customers')
            
            return {
                'success': True,
                'message': '客户创建成功',
                'data': {'_id': str(result.inserted_id)}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'创建客户失败: {str(e)}'
            }

    def update_customer(self, customer_id: str, customer_data: dict) -> dict:
        """更新客户"""
        try:
            validation_result = self.validator.validate('customers', customer_data)
            if not validation_result['is_valid']:
                return {'success': False, 'message': '数据验证失败', 'errors': validation_result['errors']}

            collection = self.db['customers']
            
            customer_data['updated_at'] = datetime.now()
            
            if '_id' in customer_data:
                del customer_data['_id']
                
            result = collection.update_one(
                {'_id': ObjectId(customer_id)},
                {'$set': customer_data}
            )
            
            if result.matched_count == 0:
                return {'success': False, 'message': '未找到要更新的客户'}
            
            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('customers')
                
            return {
                'success': True,
                'message': '客户更新成功',
                'data': {'modified_count': result.modified_count}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'更新客户失败: {str(e)}'
            }

    def delete_customer(self, customer_id: str) -> dict:
        """删除客户"""
        try:
            collection = self.db['customers']
            result = collection.delete_one({'_id': ObjectId(customer_id)})
            
            if result.deleted_count == 0:
                return {'success': False, 'message': '未找到要删除的客户'}

            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('customers')

            return {
                'success': True,
                'message': '客户删除成功',
                'data': {'deleted_count': result.deleted_count}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'删除客户失败: {str(e)}'
            }

    def get_suppliers(self, filters: dict, page: int, page_size: int) -> dict:
        """获取供应商列表"""
        try:
            collection = self.db['suppliers']
            
            query = {}
            if filters:
                for key, value in filters.items():
                    if value:
                        query[key] = {'$regex': value, '$options': 'i'}

            total = collection.count_documents(query)
            
            cursor = collection.find(query).skip((page - 1) * page_size).limit(page_size)
            
            result = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                result.append(doc)
                
            return {
                'success': True,
                'data': result,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'获取供应商列表失败: {str(e)}'
            }

    def create_supplier(self, supplier_data: dict) -> dict:
        """创建供应商"""
        try:
            validation_result = self.validator.validate('suppliers', supplier_data)
            if not validation_result['is_valid']:
                return {'success': False, 'message': '数据验证失败', 'errors': validation_result['errors']}

            collection = self.db['suppliers']
            
            now = datetime.now()
            supplier_data['created_at'] = now
            supplier_data['updated_at'] = now
            
            result = collection.insert_one(supplier_data)
            
            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('suppliers')
            
            return {
                'success': True,
                'message': '供应商创建成功',
                'data': {'_id': str(result.inserted_id)}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'创建供应商失败: {str(e)}'
            }

    def update_supplier(self, supplier_id: str, supplier_data: dict) -> dict:
        """更新供应商"""
        try:
            validation_result = self.validator.validate('suppliers', supplier_data)
            if not validation_result['is_valid']:
                return {'success': False, 'message': '数据验证失败', 'errors': validation_result['errors']}

            collection = self.db['suppliers']
            
            supplier_data['updated_at'] = datetime.now()
            
            if '_id' in supplier_data:
                del supplier_data['_id']
                
            result = collection.update_one(
                {'_id': ObjectId(supplier_id)},
                {'$set': supplier_data}
            )
            
            if result.matched_count == 0:
                return {'success': False, 'message': '未找到要更新的供应商'}
            
            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('suppliers')
                
            return {
                'success': True,
                'message': '供应商更新成功',
                'data': {'modified_count': result.modified_count}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'更新供应商失败: {str(e)}'
            }

    def delete_supplier(self, supplier_id: str) -> dict:
        """删除供应商"""
        try:
            collection = self.db['suppliers']
            result = collection.delete_one({'_id': ObjectId(supplier_id)})
            
            if result.deleted_count == 0:
                return {'success': False, 'message': '未找到要删除的供应商'}

            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('suppliers')

            return {
                'success': True,
                'message': '供应商删除成功',
                'data': {'deleted_count': result.deleted_count}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'删除供应商失败: {str(e)}'
            }

    def get_materials(self, filters: dict, page: int, page_size: int) -> dict:
        """获取物料列表"""
        try:
            collection = self.db['materials']
            
            query = {}
            if filters:
                for key, value in filters.items():
                    if value:
                        query[key] = {'$regex': value, '$options': 'i'}

            total = collection.count_documents(query)
            
            cursor = collection.find(query).skip((page - 1) * page_size).limit(page_size)
            
            result = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                result.append(doc)
                
            return {
                'success': True,
                'data': result,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'获取物料列表失败: {str(e)}'
            }

    def create_material(self, material_data: dict) -> dict:
        """创建物料"""
        try:
            validation_result = self.validator.validate('materials', material_data)
            if not validation_result['is_valid']:
                return {'success': False, 'message': '数据验证失败', 'errors': validation_result['errors']}

            collection = self.db['materials']
            
            now = datetime.now()
            material_data['created_at'] = now
            material_data['updated_at'] = now
            
            result = collection.insert_one(material_data)
            
            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('materials')
            
            return {
                'success': True,
                'message': '物料创建成功',
                'data': {'_id': str(result.inserted_id)}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'创建物料失败: {str(e)}'
            }

    def update_material(self, material_id: str, material_data: dict) -> dict:
        """更新物料"""
        try:
            validation_result = self.validator.validate('materials', material_data)
            if not validation_result['is_valid']:
                return {'success': False, 'message': '数据验证失败', 'errors': validation_result['errors']}

            collection = self.db['materials']
            
            material_data['updated_at'] = datetime.now()
            
            if '_id' in material_data:
                del material_data['_id']
                
            result = collection.update_one(
                {'_id': ObjectId(material_id)},
                {'$set': material_data}
            )
            
            if result.matched_count == 0:
                return {'success': False, 'message': '未找到要更新的物料'}
            
            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('materials')
                
            return {
                'success': True,
                'message': '物料更新成功',
                'data': {'modified_count': result.modified_count}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'更新物料失败: {str(e)}'
            }

    def delete_material(self, material_id: str) -> dict:
        """删除物料"""
        try:
            collection = self.db['materials']
            result = collection.delete_one({'_id': ObjectId(material_id)})
            
            if result.deleted_count == 0:
                return {'success': False, 'message': '未找到要删除的物料'}

            # 失效相关缓存
            self.cache_invalidator.invalidate_by_collection('materials')

            return {
                'success': True,
                'message': '物料删除成功',
                'data': {'deleted_count': result.deleted_count}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'删除物料失败: {str(e)}'
            }

if __name__ == '__main__':
    # 这是一个示例，展示如何使用ManagementService
    # 实际的调用将通过其他脚本或API进行
    service = ManagementService()
    print("ManagementService 初始化成功")
