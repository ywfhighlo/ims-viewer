#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进销存管理处理器
处理采购、销售和库存管理的业务逻辑
"""

import sys
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

# 添加项目根目录到Python路径
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from scripts.db_connection import get_database_connection
from scripts.enhanced_logger import get_logger

# 设置日志
logger = get_logger('inventory_management_handler')

class InventoryManagementHandler:
    """进销存管理处理器"""
    
    def __init__(self):
        self.db = get_database_connection()
        
    def handle_request(self, action: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理请求"""
        try:
            logger.info(f"处理请求: {action}")
            
            if action == 'load_purchase_data':
                return self.load_purchase_data(data or {})
            elif action == 'save_purchase_order':
                return self.save_purchase_order(data)
            elif action == 'delete_purchase_order':
                return self.delete_purchase_order(data.get('id'))
            elif action == 'load_sales_data':
                return self.load_sales_data(data or {})
            elif action == 'save_sales_order':
                return self.save_sales_order(data)
            elif action == 'delete_sales_order':
                return self.delete_sales_order(data.get('id'))
            elif action == 'load_inventory_data':
                return self.load_inventory_data(data or {})
            elif action == 'save_inventory_adjustment':
                return self.save_inventory_adjustment(data)
            elif action == 'save_inventory_transfer':
                return self.save_inventory_transfer(data)
            elif action == 'save_inventory_count':
                return self.save_inventory_count(data)
            elif action == 'get_suppliers':
                return self.get_suppliers()
            elif action == 'get_customers':
                return self.get_customers()
            elif action == 'get_materials':
                return self.get_materials()
            elif action == 'purchase_receipt':
                return self.handle_purchase_receipt(data)
            elif action == 'purchase_order':
                return self.handle_purchase_order(data)
            elif action == 'purchase_return':
                return self.handle_purchase_return(data)
            elif action == 'purchase_report':
                return self.handle_purchase_report(data)
            elif action == 'sales_order':
                return self.handle_sales_order(data)
            elif action == 'sales_outbound':
                return self.handle_sales_outbound(data)
            elif action == 'sales_return':
                return self.handle_sales_return(data)
            elif action == 'sales_report':
                return self.handle_sales_report(data)
            else:
                return {'success': False, 'error': f'未知操作: {action}'}
                
        except Exception as e:
            logger.error(f"处理请求失败: {str(e)}")
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def load_purchase_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """加载采购数据"""
        try:
            # 构建查询条件
            query = {}
            
            if filters.get('supplier'):
                query['supplier_name'] = {'$regex': filters['supplier'], '$options': 'i'}
            
            if filters.get('status'):
                query['status'] = filters['status']
            
            if filters.get('date_from') or filters.get('date_to'):
                date_query = {}
                if filters.get('date_from'):
                    date_query['$gte'] = filters['date_from']
                if filters.get('date_to'):
                    date_query['$lte'] = filters['date_to']
                query['order_date'] = date_query
            
            # 查询采购订单
            orders = list(self.db['purchase_orders'].find(query)
                         .sort([('order_date', -1), ('created_at', -1)])
                         .limit(1000))
            
            # 转换ObjectId为字符串
            for order in orders:
                order['_id'] = str(order['_id'])
                if 'created_at' in order and order['created_at']:
                    order['created_at'] = order['created_at'].isoformat()
                if 'updated_at' in order and order['updated_at']:
                    order['updated_at'] = order['updated_at'].isoformat()
                if 'order_date' in order and isinstance(order['order_date'], datetime):
                    order['order_date'] = order['order_date'].isoformat()
            
            # 统计数据
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_orders': {'$sum': 1},
                        'pending_orders': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'pending']}, 1, 0]}
                        },
                        'completed_orders': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                        },
                        'total_amount': {'$sum': '$total_amount'}
                    }
                }
            ]
            
            stats_result = list(self.db['purchase_orders'].aggregate(pipeline))
            stats = stats_result[0] if stats_result else {
                'total_orders': 0,
                'pending_orders': 0,
                'completed_orders': 0,
                'total_amount': 0
            }
            
            return {
                'success': True,
                'data': orders,
                'stats': {
                    'total_orders': stats.get('total_orders', 0),
                    'pending_orders': stats.get('pending_orders', 0),
                    'completed_orders': stats.get('completed_orders', 0),
                    'total_amount': stats.get('total_amount', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"加载采购数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def save_purchase_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存采购订单"""
        try:
            # 验证必填字段
            required_fields = ['order_no', 'supplier_name', 'order_date', 'total_amount']
            for field in required_fields:
                if not data.get(field):
                    return {'success': False, 'error': f'缺少必填字段: {field}'}
            
            # 检查订单号是否已存在
            existing = self.db['purchase_orders'].find_one({'order_no': data['order_no']})
            if existing:
                return {'success': False, 'error': '订单号已存在'}
            
            # 准备文档
            now = datetime.now()
            doc = {
                'order_no': data['order_no'],
                'supplier_name': data['supplier_name'],
                'order_date': datetime.fromisoformat(data['order_date']) if isinstance(data['order_date'], str) else data['order_date'],
                'total_amount': float(data['total_amount']),
                'status': data.get('status', 'pending'),
                'remark': data.get('remark', ''),
                'created_at': now,
                'updated_at': now
            }
            
            # 插入文档
            result = self.db['purchase_orders'].insert_one(doc)
            
            logger.info(f"采购订单保存成功: {data['order_no']}")
            return {'success': True, 'message': '采购订单保存成功', 'id': str(result.inserted_id)}
            
        except Exception as e:
            logger.error(f"保存采购订单失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_purchase_order(self, order_id: str) -> Dict[str, Any]:
        """删除采购订单"""
        try:
            if not order_id:
                return {'success': False, 'error': '订单ID不能为空'}
            
            # 查找并删除订单
            result = self.db['purchase_orders'].delete_one({'_id': ObjectId(order_id)})
            
            if result.deleted_count == 0:
                return {'success': False, 'error': '订单不存在'}
            
            logger.info(f"采购订单删除成功: {order_id}")
            return {'success': True, 'message': '采购订单删除成功'}
            
        except Exception as e:
            logger.error(f"删除采购订单失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def load_sales_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """加载销售数据"""
        try:
            # 构建查询条件
            query = {}
            
            if filters.get('customer'):
                query['customer_name'] = {'$regex': filters['customer'], '$options': 'i'}
            
            if filters.get('status'):
                query['status'] = filters['status']
            
            if filters.get('date_from') or filters.get('date_to'):
                date_query = {}
                if filters.get('date_from'):
                    date_query['$gte'] = filters['date_from']
                if filters.get('date_to'):
                    date_query['$lte'] = filters['date_to']
                query['order_date'] = date_query
            
            # 查询销售订单
            orders = list(self.db['sales_orders'].find(query)
                         .sort([('order_date', -1), ('created_at', -1)])
                         .limit(1000))
            
            # 转换ObjectId为字符串
            for order in orders:
                order['_id'] = str(order['_id'])
                if 'created_at' in order and order['created_at']:
                    order['created_at'] = order['created_at'].isoformat()
                if 'updated_at' in order and order['updated_at']:
                    order['updated_at'] = order['updated_at'].isoformat()
                if 'order_date' in order and isinstance(order['order_date'], datetime):
                    order['order_date'] = order['order_date'].isoformat()
            
            # 统计数据
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_orders': {'$sum': 1},
                        'pending_orders': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'pending']}, 1, 0]}
                        },
                        'completed_orders': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                        },
                        'total_amount': {'$sum': '$total_amount'}
                    }
                }
            ]
            
            stats_result = list(self.db['sales_orders'].aggregate(pipeline))
            stats = stats_result[0] if stats_result else {
                'total_orders': 0,
                'pending_orders': 0,
                'completed_orders': 0,
                'total_amount': 0
            }
            
            return {
                'success': True,
                'data': orders,
                'stats': {
                    'total_orders': stats.get('total_orders', 0),
                    'pending_orders': stats.get('pending_orders', 0),
                    'completed_orders': stats.get('completed_orders', 0),
                    'total_amount': stats.get('total_amount', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"加载销售数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def save_sales_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存销售订单"""
        try:
            # 验证必填字段
            required_fields = ['order_no', 'customer_name', 'order_date', 'total_amount']
            for field in required_fields:
                if not data.get(field):
                    return {'success': False, 'error': f'缺少必填字段: {field}'}
            
            # 检查订单号是否已存在
            existing = self.db['sales_orders'].find_one({'order_no': data['order_no']})
            if existing:
                return {'success': False, 'error': '订单号已存在'}
            
            # 准备文档
            now = datetime.now()
            doc = {
                'order_no': data['order_no'],
                'customer_name': data['customer_name'],
                'order_date': datetime.fromisoformat(data['order_date']) if isinstance(data['order_date'], str) else data['order_date'],
                'total_amount': float(data['total_amount']),
                'status': data.get('status', 'pending'),
                'remark': data.get('remark', ''),
                'created_at': now,
                'updated_at': now
            }
            
            # 插入文档
            result = self.db['sales_orders'].insert_one(doc)
            
            logger.info(f"销售订单保存成功: {data['order_no']}")
            return {'success': True, 'message': '销售订单保存成功', 'id': str(result.inserted_id)}
            
        except Exception as e:
            logger.error(f"保存销售订单失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_sales_order(self, order_id: str) -> Dict[str, Any]:
        """删除销售订单"""
        try:
            if not order_id:
                return {'success': False, 'error': '订单ID不能为空'}
            
            # 查找并删除订单
            result = self.db['sales_orders'].delete_one({'_id': ObjectId(order_id)})
            
            if result.deleted_count == 0:
                return {'success': False, 'error': '订单不存在'}
            
            logger.info(f"销售订单删除成功: {order_id}")
            return {'success': True, 'message': '销售订单删除成功'}
            
        except Exception as e:
            logger.error(f"删除销售订单失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def load_inventory_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """加载库存数据"""
        try:
            # 构建查询条件
            query = {}
            
            if filters.get('material_code'):
                query['material_code'] = {'$regex': filters['material_code'], '$options': 'i'}
            
            if filters.get('material_name'):
                query['material_name'] = {'$regex': filters['material_name'], '$options': 'i'}
            
            if filters.get('warehouse'):
                query['warehouse'] = filters['warehouse']
            
            # 查询库存数据
            inventory = list(self.db['inventory_summary'].find(query)
                           .sort([('material_code', 1)])
                           .limit(1000))
            
            # 转换ObjectId为字符串
            for item in inventory:
                item['_id'] = str(item['_id'])
                if 'last_updated' in item and item['last_updated']:
                    item['last_updated'] = item['last_updated'].isoformat()
            
            # 统计数据
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_items': {'$sum': 1},
                        'total_stock': {'$sum': '$current_stock'},
                        'low_stock_items': {
                            '$sum': {'$cond': [{'$lt': ['$current_stock', '$safety_stock']}, 1, 0]}
                        },
                        'total_value': {
                            '$sum': {'$multiply': ['$current_stock', '$unit_price']}
                        }
                    }
                }
            ]
            
            stats_result = list(self.db['inventory_summary'].aggregate(pipeline))
            stats = stats_result[0] if stats_result else {
                'total_items': 0,
                'total_stock': 0,
                'low_stock_items': 0,
                'total_value': 0
            }
            
            return {
                'success': True,
                'data': inventory,
                'stats': {
                    'total_items': stats.get('total_items', 0),
                    'total_stock': stats.get('total_stock', 0),
                    'low_stock_items': stats.get('low_stock_items', 0),
                    'total_value': stats.get('total_value', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"加载库存数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def save_inventory_adjustment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存库存调整"""
        try:
            # 验证必填字段
            required_fields = ['material_code', 'adjustment_qty', 'reason']
            for field in required_fields:
                if not data.get(field):
                    return {'success': False, 'error': f'缺少必填字段: {field}'}
            
            # 准备调整记录
            now = datetime.now()
            adjustment_doc = {
                'material_code': data['material_code'],
                'warehouse': data.get('warehouse', '默认仓库'),
                'adjustment_qty': float(data['adjustment_qty']),
                'reason': data['reason'],
                'operator': data.get('operator', 'system'),
                'created_at': now
            }
            
            # 插入调整记录
            self.db['inventory_adjustments'].insert_one(adjustment_doc)
            
            # 更新库存汇总
            filter_query = {
                'material_code': data['material_code'],
                'warehouse': data.get('warehouse', '默认仓库')
            }
            
            update_query = {
                '$inc': {'current_stock': float(data['adjustment_qty'])},
                '$set': {'last_updated': now}
            }
            
            self.db['inventory_summary'].update_one(filter_query, update_query, upsert=True)
            
            logger.info(f"库存调整保存成功: {data['material_code']}")
            return {'success': True, 'message': '库存调整保存成功'}
            
        except Exception as e:
            logger.error(f"保存库存调整失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def save_inventory_transfer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存库存转移"""
        try:
            # 验证必填字段
            required_fields = ['material_code', 'from_warehouse', 'to_warehouse', 'transfer_qty']
            for field in required_fields:
                if not data.get(field):
                    return {'success': False, 'error': f'缺少必填字段: {field}'}
            
            if data['from_warehouse'] == data['to_warehouse']:
                return {'success': False, 'error': '源仓库和目标仓库不能相同'}
            
            # 检查源仓库库存是否足够
            from_inventory = self.db['inventory_summary'].find_one({
                'material_code': data['material_code'],
                'warehouse': data['from_warehouse']
            })
            
            if not from_inventory or from_inventory['current_stock'] < float(data['transfer_qty']):
                return {'success': False, 'error': '源仓库库存不足'}
            
            # 准备转移记录
            now = datetime.now()
            transfer_doc = {
                'material_code': data['material_code'],
                'from_warehouse': data['from_warehouse'],
                'to_warehouse': data['to_warehouse'],
                'transfer_qty': float(data['transfer_qty']),
                'reason': data.get('reason', ''),
                'operator': data.get('operator', 'system'),
                'created_at': now
            }
            
            # 插入转移记录
            self.db['inventory_transfers'].insert_one(transfer_doc)
            
            # 更新源仓库库存（减少）
            self.db['inventory_summary'].update_one(
                {
                    'material_code': data['material_code'],
                    'warehouse': data['from_warehouse']
                },
                {
                    '$inc': {'current_stock': -float(data['transfer_qty'])},
                    '$set': {'last_updated': now}
                }
            )
            
            # 更新目标仓库库存（增加）
            self.db['inventory_summary'].update_one(
                {
                    'material_code': data['material_code'],
                    'warehouse': data['to_warehouse']
                },
                {
                    '$inc': {'current_stock': float(data['transfer_qty'])},
                    '$set': {'last_updated': now}
                },
                upsert=True
            )
            
            logger.info(f"库存转移保存成功: {data['material_code']}")
            return {'success': True, 'message': '库存转移保存成功'}
            
        except Exception as e:
            logger.error(f"保存库存转移失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def save_inventory_count(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存库存盘点"""
        try:
            # 验证必填字段
            required_fields = ['material_code', 'counted_qty']
            for field in required_fields:
                if not data.get(field):
                    return {'success': False, 'error': f'缺少必填字段: {field}'}
            
            # 获取当前库存
            current_inventory = self.db['inventory_summary'].find_one({
                'material_code': data['material_code'],
                'warehouse': data.get('warehouse', '默认仓库')
            })
            
            current_stock = current_inventory['current_stock'] if current_inventory else 0
            counted_qty = float(data['counted_qty'])
            difference = counted_qty - current_stock
            
            # 准备盘点记录
            now = datetime.now()
            count_doc = {
                'material_code': data['material_code'],
                'warehouse': data.get('warehouse', '默认仓库'),
                'current_stock': current_stock,
                'counted_qty': counted_qty,
                'difference': difference,
                'reason': data.get('reason', ''),
                'operator': data.get('operator', 'system'),
                'created_at': now
            }
            
            # 插入盘点记录
            self.db['inventory_counts'].insert_one(count_doc)
            
            # 如果有差异，更新库存
            if difference != 0:
                self.db['inventory_summary'].update_one(
                    {
                        'material_code': data['material_code'],
                        'warehouse': data.get('warehouse', '默认仓库')
                    },
                    {
                        '$set': {
                            'current_stock': counted_qty,
                            'last_updated': now
                        }
                    },
                    upsert=True
                )
            
            logger.info(f"库存盘点保存成功: {data['material_code']}")
            return {
                'success': True, 
                'message': '库存盘点保存成功',
                'difference': difference
            }
            
        except Exception as e:
            logger.error(f"保存库存盘点失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_suppliers(self) -> Dict[str, Any]:
        """获取供应商列表"""
        try:
            # 从采购订单中获取供应商
            suppliers = self.db['purchase_orders'].distinct('supplier_name')
            
            # 也可以从专门的供应商表中获取（如果存在）
            supplier_collection = self.db.get_collection('supplier_info')
            if supplier_collection:
                supplier_docs = list(supplier_collection.find({}, {'supplier_name': 1}))
                for doc in supplier_docs:
                    if doc.get('supplier_name') and doc['supplier_name'] not in suppliers:
                        suppliers.append(doc['supplier_name'])
            
            return {
                'success': True,
                'data': sorted(suppliers)
            }
            
        except Exception as e:
            logger.error(f"获取供应商列表失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_customers(self) -> Dict[str, Any]:
        """获取客户列表"""
        try:
            # 从销售订单中获取客户
            customers = self.db['sales_orders'].distinct('customer_name')
            
            # 也可以从专门的客户表中获取（如果存在）
            customer_collection = self.db.get_collection('customer_info')
            if customer_collection:
                customer_docs = list(customer_collection.find({}, {'customer_name': 1}))
                for doc in customer_docs:
                    if doc.get('customer_name') and doc['customer_name'] not in customers:
                        customers.append(doc['customer_name'])
            
            return {
                'success': True,
                'data': sorted(customers)
            }
            
        except Exception as e:
            logger.error(f"获取客户列表失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_materials(self) -> Dict[str, Any]:
        """获取物料列表"""
        try:
            # 从库存汇总中获取物料
            materials = list(self.db['inventory_summary'].find(
                {},
                {
                    'material_code': 1,
                    'material_name': 1,
                    'specification': 1,
                    'unit': 1,
                    'current_stock': 1
                }
            ))
            
            # 转换ObjectId为字符串
            for material in materials:
                material['_id'] = str(material['_id'])
            
            # 也可以从专门的物料表中获取（如果存在）
            material_collection = self.db.get_collection('materials')
            if material_collection:
                material_docs = list(material_collection.find(
                    {},
                    {
                        'material_code': 1,
                        'material_name': 1,
                        'specification': 1,
                        'unit': 1
                    }
                ))
                
                # 合并物料数据，避免重复
                existing_codes = {m['material_code'] for m in materials}
                for doc in material_docs:
                    if doc.get('material_code') and doc['material_code'] not in existing_codes:
                        doc['_id'] = str(doc['_id'])
                        doc['current_stock'] = 0  # 默认库存为0
                        materials.append(doc)
            
            return {
                'success': True,
                'data': sorted(materials, key=lambda x: x.get('material_code', ''))
            }
            
        except Exception as e:
            logger.error(f"获取物料列表失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_purchase_receipt(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理采购入库"""
        try:
            return {
                'success': True,
                'message': '采购入库功能',
                'data': {
                    'action': 'purchase_receipt',
                    'description': '处理采购商品的入库操作',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理采购入库失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_purchase_order(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理采购订单"""
        try:
            return {
                'success': True,
                'message': '采购订单功能',
                'data': {
                    'action': 'purchase_order',
                    'description': '处理采购订单的创建和管理',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理采购订单失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_purchase_return(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理采购退货"""
        try:
            return {
                'success': True,
                'message': '采购退货功能',
                'data': {
                    'action': 'purchase_return',
                    'description': '处理采购商品的退货操作',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理采购退货失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_purchase_report(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理采购报表"""
        try:
            return {
                'success': True,
                'message': '采购报表功能',
                'data': {
                    'action': 'purchase_report',
                    'description': '生成采购相关的统计报表',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理采购报表失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_sales_order(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理销售订单"""
        try:
            return {
                'success': True,
                'message': '销售订单功能',
                'data': {
                    'action': 'sales_order',
                    'description': '处理销售订单的创建和管理',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理销售订单失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_sales_outbound(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理销售出库"""
        try:
            return {
                'success': True,
                'message': '销售出库功能',
                'data': {
                    'action': 'sales_outbound',
                    'description': '处理销售商品的出库操作',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理销售出库失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_sales_return(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理销售退货"""
        try:
            return {
                'success': True,
                'message': '销售退货功能',
                'data': {
                    'action': 'sales_return',
                    'description': '处理销售商品的退货操作',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理销售退货失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_sales_report(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理销售报表"""
        try:
            return {
                'success': True,
                'message': '销售报表功能',
                'data': {
                    'action': 'sales_report',
                    'description': '生成销售相关的统计报表',
                    'status': 'available'
                }
            }
        except Exception as e:
            logger.error(f"处理销售报表失败: {str(e)}")
            return {'success': False, 'error': str(e)}

def main():
    """主函数 - 用于命令行调用"""
    if len(sys.argv) < 2:
        print("用法: python inventory_management_handler.py <action> [data]")
        return
    
    action = sys.argv[1]
    data = {}
    
    if len(sys.argv) > 2:
        try:
            data = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print("错误: 无效的JSON数据")
            return
    
    handler = InventoryManagementHandler()
    result = handler.handle_request(action, data)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()