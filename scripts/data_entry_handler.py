#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据录入管理后端处理器
处理供应商、客户、商品的CRUD操作
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_db_client, get_database_name
from enhanced_logger import EnhancedLogger

# 数据库配置
DATABASE_NAME = get_database_name()
SUPPLIERS_COLLECTION = 'suppliers'
CUSTOMERS_COLLECTION = 'customers'
PRODUCTS_COLLECTION = 'products'

def json_serializer(obj):
    """JSON序列化辅助函数，处理MongoDB的ObjectId和datetime"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

class DataEntryHandler:
    """数据录入管理处理器"""
    
    def __init__(self):
        self.logger = EnhancedLogger("data_entry_handler")
        self.client = get_db_client()
        self.db = self.client[DATABASE_NAME] if self.client else None
        
        if not self.db:
            self.logger.error("数据库连接失败")
            raise Exception("数据库连接失败")
    
    def handle_request(self, command: str, data: Dict = None) -> Dict[str, Any]:
        """处理Web界面请求"""
        try:
            self.logger.info(f"处理请求: {command}", data=data)
            
            # 供应商相关操作
            if command == 'loadSuppliers':
                return self.load_suppliers()
            elif command == 'saveSupplier':
                return self.save_supplier(data)
            elif command == 'updateRecord' and data.get('type') == 'supplier':
                return self.update_supplier(data.get('data'))
            elif command == 'deleteRecord' and data.get('type') == 'supplier':
                return self.delete_supplier(data.get('id'))
            
            # 客户相关操作
            elif command == 'loadCustomers':
                return self.load_customers()
            elif command == 'saveCustomer':
                return self.save_customer(data)
            elif command == 'updateRecord' and data.get('type') == 'customer':
                return self.update_customer(data.get('data'))
            elif command == 'deleteRecord' and data.get('type') == 'customer':
                return self.delete_customer(data.get('id'))
            
            # 商品相关操作
            elif command == 'loadProducts':
                return self.load_products()
            elif command == 'saveProduct':
                return self.save_product(data)
            elif command == 'updateRecord' and data.get('type') == 'product':
                return self.update_product(data.get('data'))
            elif command == 'deleteRecord' and data.get('type') == 'product':
                return self.delete_product(data.get('id'))
            
            else:
                return {
                    'success': False,
                    'error': f'未知命令: {command}'
                }
                
        except Exception as e:
            self.logger.error(f"处理请求失败: {str(e)}", command=command)
            return {
                'success': False,
                'error': f'处理请求时发生错误: {str(e)}'
            }
    
    # ==================== 供应商管理 ====================
    
    def load_suppliers(self) -> Dict[str, Any]:
        """加载供应商列表"""
        try:
            collection = self.db[SUPPLIERS_COLLECTION]
            suppliers = list(collection.find(
                {},
                {
                    'supplier_name': 1,
                    'supplier_code': 1,
                    'credit_code': 1,
                    'contact_person': 1,
                    'phone': 1,
                    'email': 1,
                    'address': 1,
                    'status': 1,
                    'created_at': 1
                }
            ).sort('supplier_name', 1))
            
            self.logger.info(f"加载供应商列表成功，共 {len(suppliers)} 条记录")
            
            return {
                'success': True,
                'command': 'suppliersLoaded',
                'data': suppliers
            }
        except Exception as e:
            self.logger.error(f"加载供应商列表失败: {str(e)}")
            return {
                'success': False,
                'error': f'加载供应商列表失败: {str(e)}'
            }
    
    def save_supplier(self, data: Dict) -> Dict[str, Any]:
        """保存新供应商"""
        try:
            # 验证必填字段
            if not data.get('supplier_name'):
                return {
                    'success': False,
                    'error': '供应商名称不能为空'
                }
            
            collection = self.db[SUPPLIERS_COLLECTION]
            
            # 检查供应商名称是否已存在
            existing = collection.find_one({'supplier_name': data['supplier_name']})
            if existing:
                return {
                    'success': False,
                    'error': '供应商名称已存在'
                }
            
            # 生成供应商编码
            supplier_code = self.generate_supplier_code()
            
            # 构建供应商数据
            supplier_data = {
                'supplier_name': data['supplier_name'],
                'supplier_code': supplier_code,
                'credit_code': data.get('credit_code', ''),
                'contact_person': data.get('contact_person', ''),
                'phone': data.get('phone', ''),
                'email': data.get('email', ''),
                'address': data.get('address', ''),
                'remarks': data.get('remarks', ''),
                'status': 'active',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # 插入数据库
            result = collection.insert_one(supplier_data)
            
            if result.inserted_id:
                self.logger.info(f"供应商保存成功: {data['supplier_name']}", supplier_code=supplier_code)
                return {
                    'success': True,
                    'command': 'recordSaved',
                    'type': 'supplier',
                    'message': f'供应商 "{data["supplier_name"]}" 保存成功，编码: {supplier_code}'
                }
            else:
                return {
                    'success': False,
                    'error': '保存供应商失败'
                }
                
        except Exception as e:
            self.logger.error(f"保存供应商失败: {str(e)}", data=data)
            return {
                'success': False,
                'error': f'保存供应商失败: {str(e)}'
            }
    
    def update_supplier(self, data: Dict) -> Dict[str, Any]:
        """更新供应商信息"""
        try:
            if not data.get('_id'):
                return {
                    'success': False,
                    'error': '缺少供应商ID'
                }
            
            if not data.get('supplier_name'):
                return {
                    'success': False,
                    'error': '供应商名称不能为空'
                }
            
            collection = self.db[SUPPLIERS_COLLECTION]
            supplier_id = ObjectId(data['_id'])
            
            # 检查供应商名称是否与其他记录重复
            existing = collection.find_one({
                'supplier_name': data['supplier_name'],
                '_id': {'$ne': supplier_id}
            })
            if existing:
                return {
                    'success': False,
                    'error': '供应商名称已存在'
                }
            
            # 构建更新数据
            update_data = {
                'supplier_name': data['supplier_name'],
                'supplier_code': data.get('supplier_code', ''),
                'credit_code': data.get('credit_code', ''),
                'contact_person': data.get('contact_person', ''),
                'phone': data.get('phone', ''),
                'email': data.get('email', ''),
                'address': data.get('address', ''),
                'remarks': data.get('remarks', ''),
                'updated_at': datetime.now()
            }
            
            # 更新数据库
            result = collection.update_one(
                {'_id': supplier_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self.logger.info(f"供应商更新成功: {data['supplier_name']}")
                return {
                    'success': True,
                    'command': 'recordUpdated',
                    'type': 'supplier',
                    'message': f'供应商 "{data["supplier_name"]}" 更新成功'
                }
            else:
                return {
                    'success': False,
                    'error': '更新供应商失败，可能数据没有变化'
                }
                
        except Exception as e:
            self.logger.error(f"更新供应商失败: {str(e)}", data=data)
            return {
                'success': False,
                'error': f'更新供应商失败: {str(e)}'
            }
    
    def delete_supplier(self, supplier_id: str) -> Dict[str, Any]:
        """删除供应商"""
        try:
            collection = self.db[SUPPLIERS_COLLECTION]
            
            # 先获取供应商信息
            supplier = collection.find_one({'_id': ObjectId(supplier_id)})
            if not supplier:
                return {
                    'success': False,
                    'error': '供应商不存在'
                }
            
            # 检查是否有关联的物料
            materials_collection = self.db['materials']
            material_count = materials_collection.count_documents({
                'supplier_code': supplier.get('supplier_code')
            })
            
            if material_count > 0:
                return {
                    'success': False,
                    'error': f'无法删除供应商，存在 {material_count} 个关联的物料记录'
                }
            
            # 删除供应商
            result = collection.delete_one({'_id': ObjectId(supplier_id)})
            
            if result.deleted_count > 0:
                self.logger.info(f"供应商删除成功: {supplier.get('supplier_name')}")
                return {
                    'success': True,
                    'command': 'recordDeleted',
                    'type': 'supplier',
                    'message': f'供应商 "{supplier.get("supplier_name")}" 删除成功'
                }
            else:
                return {
                    'success': False,
                    'error': '删除供应商失败'
                }
                
        except Exception as e:
            self.logger.error(f"删除供应商失败: {str(e)}", supplier_id=supplier_id)
            return {
                'success': False,
                'error': f'删除供应商失败: {str(e)}'
            }
    
    def generate_supplier_code(self) -> str:
        """生成供应商编码"""
        try:
            collection = self.db[SUPPLIERS_COLLECTION]
            
            # 获取已使用的编码
            used_codes = set()
            suppliers = collection.find(
                {'supplier_code': {'$exists': True, '$ne': None, '$ne': ''}},
                {'supplier_code': 1}
            )
            
            for supplier in suppliers:
                code = supplier.get('supplier_code')
                if code and code.isdigit():
                    used_codes.add(int(code))
            
            # 找到下一个可用编码
            for code_num in range(1, 1000):
                if code_num not in used_codes:
                    return f"{code_num:02d}"
            
            # 如果前999个都用完了，使用时间戳
            return str(int(datetime.now().timestamp()) % 10000)
            
        except Exception as e:
            self.logger.error(f"生成供应商编码失败: {str(e)}")
            return str(int(datetime.now().timestamp()) % 10000)
    
    # ==================== 客户管理 ====================
    
    def load_customers(self) -> Dict[str, Any]:
        """加载客户列表"""
        try:
            collection = self.db[CUSTOMERS_COLLECTION]
            customers = list(collection.find(
                {},
                {
                    'customer_name': 1,
                    'customer_code': 1,
                    'customer_type': 1,
                    'customer_credit_code': 1,
                    'customer_contact_person': 1,
                    'customer_phone': 1,
                    'customer_email': 1,
                    'customer_address': 1,
                    'credit_limit': 1,
                    'status': 1,
                    'created_at': 1
                }
            ).sort('customer_name', 1))
            
            self.logger.info(f"加载客户列表成功，共 {len(customers)} 条记录")
            
            return {
                'success': True,
                'command': 'customersLoaded',
                'data': customers
            }
        except Exception as e:
            self.logger.error(f"加载客户列表失败: {str(e)}")
            return {
                'success': False,
                'error': f'加载客户列表失败: {str(e)}'
            }
    
    def save_customer(self, data: Dict) -> Dict[str, Any]:
        """保存新客户"""
        try:
            # 验证必填字段
            if not data.get('customer_name'):
                return {
                    'success': False,
                    'error': '客户名称不能为空'
                }
            
            collection = self.db[CUSTOMERS_COLLECTION]
            
            # 检查客户名称是否已存在
            existing = collection.find_one({'customer_name': data['customer_name']})
            if existing:
                return {
                    'success': False,
                    'error': '客户名称已存在'
                }
            
            # 生成客户编码
            customer_code = self.generate_customer_code()
            
            # 构建客户数据
            customer_data = {
                'customer_name': data['customer_name'],
                'customer_code': customer_code,
                'customer_type': data.get('customer_type', ''),
                'customer_credit_code': data.get('customer_credit_code', ''),
                'customer_contact_person': data.get('customer_contact_person', ''),
                'customer_phone': data.get('customer_phone', ''),
                'customer_email': data.get('customer_email', ''),
                'customer_address': data.get('customer_address', ''),
                'customer_remarks': data.get('customer_remarks', ''),
                'credit_limit': float(data.get('credit_limit', 0)) if data.get('credit_limit') else 0,
                'status': 'active',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # 插入数据库
            result = collection.insert_one(customer_data)
            
            if result.inserted_id:
                self.logger.info(f"客户保存成功: {data['customer_name']}", customer_code=customer_code)
                return {
                    'success': True,
                    'command': 'recordSaved',
                    'type': 'customer',
                    'message': f'客户 "{data["customer_name"]}" 保存成功，编码: {customer_code}'
                }
            else:
                return {
                    'success': False,
                    'error': '保存客户失败'
                }
                
        except Exception as e:
            self.logger.error(f"保存客户失败: {str(e)}", data=data)
            return {
                'success': False,
                'error': f'保存客户失败: {str(e)}'
            }
    
    def update_customer(self, data: Dict) -> Dict[str, Any]:
        """更新客户信息"""
        try:
            if not data.get('_id'):
                return {
                    'success': False,
                    'error': '缺少客户ID'
                }
            
            if not data.get('customer_name'):
                return {
                    'success': False,
                    'error': '客户名称不能为空'
                }
            
            collection = self.db[CUSTOMERS_COLLECTION]
            customer_id = ObjectId(data['_id'])
            
            # 检查客户名称是否与其他记录重复
            existing = collection.find_one({
                'customer_name': data['customer_name'],
                '_id': {'$ne': customer_id}
            })
            if existing:
                return {
                    'success': False,
                    'error': '客户名称已存在'
                }
            
            # 构建更新数据
            update_data = {
                'customer_name': data['customer_name'],
                'customer_code': data.get('customer_code', ''),
                'customer_type': data.get('customer_type', ''),
                'customer_credit_code': data.get('customer_credit_code', ''),
                'customer_contact_person': data.get('customer_contact_person', ''),
                'customer_phone': data.get('customer_phone', ''),
                'customer_email': data.get('customer_email', ''),
                'customer_address': data.get('customer_address', ''),
                'customer_remarks': data.get('customer_remarks', ''),
                'credit_limit': float(data.get('credit_limit', 0)) if data.get('credit_limit') else 0,
                'updated_at': datetime.now()
            }
            
            # 更新数据库
            result = collection.update_one(
                {'_id': customer_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self.logger.info(f"客户更新成功: {data['customer_name']}")
                return {
                    'success': True,
                    'command': 'recordUpdated',
                    'type': 'customer',
                    'message': f'客户 "{data["customer_name"]}" 更新成功'
                }
            else:
                return {
                    'success': False,
                    'error': '更新客户失败，可能数据没有变化'
                }
                
        except Exception as e:
            self.logger.error(f"更新客户失败: {str(e)}", data=data)
            return {
                'success': False,
                'error': f'更新客户失败: {str(e)}'
            }
    
    def delete_customer(self, customer_id: str) -> Dict[str, Any]:
        """删除客户"""
        try:
            collection = self.db[CUSTOMERS_COLLECTION]
            
            # 先获取客户信息
            customer = collection.find_one({'_id': ObjectId(customer_id)})
            if not customer:
                return {
                    'success': False,
                    'error': '客户不存在'
                }
            
            # 检查是否有关联的销售记录
            sales_collection = self.db.get('sales_outbound', None)
            if sales_collection:
                sales_count = sales_collection.count_documents({
                    'customer_name': customer.get('customer_name')
                })
                
                if sales_count > 0:
                    return {
                        'success': False,
                        'error': f'无法删除客户，存在 {sales_count} 个关联的销售记录'
                    }
            
            # 删除客户
            result = collection.delete_one({'_id': ObjectId(customer_id)})
            
            if result.deleted_count > 0:
                self.logger.info(f"客户删除成功: {customer.get('customer_name')}")
                return {
                    'success': True,
                    'command': 'recordDeleted',
                    'type': 'customer',
                    'message': f'客户 "{customer.get("customer_name")}" 删除成功'
                }
            else:
                return {
                    'success': False,
                    'error': '删除客户失败'
                }
                
        except Exception as e:
            self.logger.error(f"删除客户失败: {str(e)}", customer_id=customer_id)
            return {
                'success': False,
                'error': f'删除客户失败: {str(e)}'
            }
    
    def generate_customer_code(self) -> str:
        """生成客户编码"""
        try:
            collection = self.db[CUSTOMERS_COLLECTION]
            
            # 获取已使用的编码
            used_codes = set()
            customers = collection.find(
                {'customer_code': {'$exists': True, '$ne': None, '$ne': ''}},
                {'customer_code': 1}
            )
            
            for customer in customers:
                code = customer.get('customer_code')
                if code and code.startswith('C') and code[1:].isdigit():
                    used_codes.add(int(code[1:]))
            
            # 找到下一个可用编码
            for code_num in range(1, 10000):
                if code_num not in used_codes:
                    return f"C{code_num:04d}"
            
            # 如果前9999个都用完了，使用时间戳
            return f"C{int(datetime.now().timestamp()) % 10000:04d}"
            
        except Exception as e:
            self.logger.error(f"生成客户编码失败: {str(e)}")
            return f"C{int(datetime.now().timestamp()) % 10000:04d}"
    
    # ==================== 商品管理 ====================
    
    def load_products(self) -> Dict[str, Any]:
        """加载商品列表"""
        try:
            collection = self.db[PRODUCTS_COLLECTION]
            products = list(collection.find(
                {},
                {
                    'product_name': 1,
                    'product_code': 1,
                    'product_category': 1,
                    'product_model': 1,
                    'product_unit': 1,
                    'product_price': 1,
                    'product_cost': 1,
                    'stock_quantity': 1,
                    'min_stock': 1,
                    'max_stock': 1,
                    'product_description': 1,
                    'status': 1,
                    'created_at': 1
                }
            ).sort('product_name', 1))
            
            self.logger.info(f"加载商品列表成功，共 {len(products)} 条记录")
            
            return {
                'success': True,
                'command': 'productsLoaded',
                'data': products
            }
        except Exception as e:
            self.logger.error(f"加载商品列表失败: {str(e)}")
            return {
                'success': False,
                'error': f'加载商品列表失败: {str(e)}'
            }
    
    def save_product(self, data: Dict) -> Dict[str, Any]:
        """保存新商品"""
        try:
            # 验证必填字段
            if not data.get('product_name'):
                return {
                    'success': False,
                    'error': '商品名称不能为空'
                }
            
            collection = self.db[PRODUCTS_COLLECTION]
            
            # 检查商品名称是否已存在
            existing = collection.find_one({'product_name': data['product_name']})
            if existing:
                return {
                    'success': False,
                    'error': '商品名称已存在'
                }
            
            # 生成商品编码
            product_code = self.generate_product_code()
            
            # 构建商品数据
            product_data = {
                'product_name': data['product_name'],
                'product_code': product_code,
                'product_category': data.get('product_category', ''),
                'product_model': data.get('product_model', ''),
                'product_unit': data.get('product_unit', ''),
                'product_description': data.get('product_description', ''),
                'product_remarks': data.get('product_remarks', ''),
                'product_price': float(data.get('product_price', 0)) if data.get('product_price') else 0,
                'product_cost': float(data.get('product_cost', 0)) if data.get('product_cost') else 0,
                'stock_quantity': int(data.get('stock_quantity', 0)) if data.get('stock_quantity') else 0,
                'min_stock': int(data.get('min_stock', 0)) if data.get('min_stock') else 0,
                'max_stock': int(data.get('max_stock', 0)) if data.get('max_stock') else 0,
                'status': 'active',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # 插入数据库
            result = collection.insert_one(product_data)
            
            if result.inserted_id:
                self.logger.info(f"商品保存成功: {data['product_name']}", product_code=product_code)
                return {
                    'success': True,
                    'command': 'recordSaved',
                    'type': 'product',
                    'message': f'商品 "{data["product_name"]}" 保存成功，编码: {product_code}'
                }
            else:
                return {
                    'success': False,
                    'error': '保存商品失败'
                }
                
        except Exception as e:
            self.logger.error(f"保存商品失败: {str(e)}", data=data)
            return {
                'success': False,
                'error': f'保存商品失败: {str(e)}'
            }
    
    def update_product(self, data: Dict) -> Dict[str, Any]:
        """更新商品信息"""
        try:
            if not data.get('_id'):
                return {
                    'success': False,
                    'error': '缺少商品ID'
                }
            
            if not data.get('product_name'):
                return {
                    'success': False,
                    'error': '商品名称不能为空'
                }
            
            collection = self.db[PRODUCTS_COLLECTION]
            product_id = ObjectId(data['_id'])
            
            # 检查商品名称是否与其他记录重复
            existing = collection.find_one({
                'product_name': data['product_name'],
                '_id': {'$ne': product_id}
            })
            if existing:
                return {
                    'success': False,
                    'error': '商品名称已存在'
                }
            
            # 构建更新数据
            update_data = {
                'product_name': data['product_name'],
                'product_code': data.get('product_code', ''),
                'product_category': data.get('product_category', ''),
                'product_model': data.get('product_model', ''),
                'product_unit': data.get('product_unit', ''),
                'product_description': data.get('product_description', ''),
                'product_remarks': data.get('product_remarks', ''),
                'product_price': float(data.get('product_price', 0)) if data.get('product_price') else 0,
                'product_cost': float(data.get('product_cost', 0)) if data.get('product_cost') else 0,
                'stock_quantity': int(data.get('stock_quantity', 0)) if data.get('stock_quantity') else 0,
                'min_stock': int(data.get('min_stock', 0)) if data.get('min_stock') else 0,
                'max_stock': int(data.get('max_stock', 0)) if data.get('max_stock') else 0,
                'updated_at': datetime.now()
            }
            
            # 更新数据库
            result = collection.update_one(
                {'_id': product_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self.logger.info(f"商品更新成功: {data['product_name']}")
                return {
                    'success': True,
                    'command': 'recordUpdated',
                    'type': 'product',
                    'message': f'商品 "{data["product_name"]}" 更新成功'
                }
            else:
                return {
                    'success': False,
                    'error': '更新商品失败，可能数据没有变化'
                }
                
        except Exception as e:
            self.logger.error(f"更新商品失败: {str(e)}", data=data)
            return {
                'success': False,
                'error': f'更新商品失败: {str(e)}'
            }
    
    def delete_product(self, product_id: str) -> Dict[str, Any]:
        """删除商品"""
        try:
            collection = self.db[PRODUCTS_COLLECTION]
            
            # 先获取商品信息
            product = collection.find_one({'_id': ObjectId(product_id)})
            if not product:
                return {
                    'success': False,
                    'error': '商品不存在'
                }
            
            # 检查是否有关联的库存记录
            # 这里可以根据实际业务需求添加更多的关联检查
            
            # 删除商品
            result = collection.delete_one({'_id': ObjectId(product_id)})
            
            if result.deleted_count > 0:
                self.logger.info(f"商品删除成功: {product.get('product_name')}")
                return {
                    'success': True,
                    'command': 'recordDeleted',
                    'type': 'product',
                    'message': f'商品 "{product.get("product_name")}" 删除成功'
                }
            else:
                return {
                    'success': False,
                    'error': '删除商品失败'
                }
                
        except Exception as e:
            self.logger.error(f"删除商品失败: {str(e)}", product_id=product_id)
            return {
                'success': False,
                'error': f'删除商品失败: {str(e)}'
            }
    
    def generate_product_code(self) -> str:
        """生成商品编码"""
        try:
            collection = self.db[PRODUCTS_COLLECTION]
            
            # 获取已使用的编码
            used_codes = set()
            products = collection.find(
                {'product_code': {'$exists': True, '$ne': None, '$ne': ''}},
                {'product_code': 1}
            )
            
            for product in products:
                code = product.get('product_code')
                if code and code.startswith('P') and code[1:].isdigit():
                    used_codes.add(int(code[1:]))
            
            # 找到下一个可用编码
            for code_num in range(1, 100000):
                if code_num not in used_codes:
                    return f"P{code_num:05d}"
            
            # 如果前99999个都用完了，使用时间戳
            return f"P{int(datetime.now().timestamp()) % 100000:05d}"
            
        except Exception as e:
            self.logger.error(f"生成商品编码失败: {str(e)}")
            return f"P{int(datetime.now().timestamp()) % 100000:05d}"

def main():
    """主函数 - 处理命令行参数"""
    if len(sys.argv) < 2:
        print("用法: python data_entry_handler.py <command> [data]")
        print("命令:")
        print("  loadSuppliers - 加载供应商列表")
        print("  saveSupplier - 保存供应商")
        print("  loadCustomers - 加载客户列表")
        print("  saveCustomer - 保存客户")
        print("  loadProducts - 加载商品列表")
        print("  saveProduct - 保存商品")
        return
    
    command = sys.argv[1]
    data = None
    
    if len(sys.argv) > 2:
        try:
            data = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(f"错误: 无法解析JSON数据: {sys.argv[2]}")
            return
    
    handler = DataEntryHandler()
    result = handler.handle_request(command, data)
    
    print(json.dumps(result, ensure_ascii=False, indent=2, default=json_serializer))

if __name__ == '__main__':
    main()