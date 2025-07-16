#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询优化引擎
提供统一的数据库查询优化功能，使用聚合管道和批量操作提升性能
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.db_connection import get_database_connection


class QueryOptimizer:
    """查询优化引擎类"""
    
    def __init__(self, logger: Optional[EnhancedLogger] = None):
        """
        初始化查询优化器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or EnhancedLogger("query_optimizer")
        self.db = None
        
    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db is None:
            self.db = get_database_connection()
        return self.db
    
    def _build_date_filter(self, start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        构建日期过滤条件
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            日期过滤条件字典
        """
        date_filter = {}
        if start_date:
            date_filter['$gte'] = start_date
        if end_date:
            date_filter['$lte'] = end_date
        return date_filter
    
    def optimize_supplier_reconciliation_query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        优化供应商对账表查询
        
        Args:
            filters: 查询过滤条件
                - start_date: 开始日期
                - end_date: 结束日期
                - supplier_name: 供应商名称
                
        Returns:
            供应商对账表数据列表
        """
        try:
            self.logger.info("开始执行优化的供应商对账表查询")
            db = self._get_db_connection()
            
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            supplier_name = filters.get('supplier_name')
            
            # 构建日期过滤条件
            date_filter = self._build_date_filter(start_date, end_date)
            
            # 1. 构建采购数据聚合管道
            purchase_pipeline = [{'$match': {}}]
            
            if date_filter:
                purchase_pipeline[0]['$match']['inbound_date'] = date_filter
            if supplier_name:
                purchase_pipeline[0]['$match']['supplier_name'] = supplier_name
            
            purchase_pipeline.extend([
                {
                    '$group': {
                        '_id': '$supplier_name',
                        'total_purchase_amount': {'$sum': '$amount'},
                        'purchase_count': {'$sum': 1},
                        'latest_purchase_date': {'$max': '$inbound_date'}
                    }
                }
            ])
            
            # 2. 构建付款数据聚合管道
            payment_pipeline = [{'$match': {}}]
            
            if date_filter:
                payment_pipeline[0]['$match']['payment_date'] = date_filter
            if supplier_name:
                payment_pipeline[0]['$match']['supplier_name'] = supplier_name
            
            payment_pipeline.extend([
                {
                    '$group': {
                        '_id': '$supplier_name',
                        'total_payment_amount': {'$sum': '$amount'},
                        'payment_count': {'$sum': 1},
                        'latest_payment_date': {'$max': '$payment_date'}
                    }
                }
            ])
            
            # 3. 并行执行聚合查询
            purchase_collection = db['purchase_inbound']
            payment_collection = db['payment_details']
            
            purchase_aggregated = list(purchase_collection.aggregate(purchase_pipeline))
            payment_aggregated = list(payment_collection.aggregate(payment_pipeline))
            
            purchase_dict = {item['_id']: item for item in purchase_aggregated}
            payment_dict = {item['_id']: item for item in payment_aggregated}
            
            # 4. 获取所有涉及的供应商名称
            all_supplier_names = set(purchase_dict.keys()) | set(payment_dict.keys())
            
            if not all_supplier_names:
                self.logger.info("没有找到相关的采购或付款数据")
                return []
            
            # 5. 批量获取供应商基础信息
            suppliers_collection = db['suppliers']
            suppliers_query = {'supplier_name': {'$in': list(all_supplier_names)}}
            suppliers = list(suppliers_collection.find(suppliers_query, {'_id': 0}))
            suppliers_dict = {supplier.get('supplier_name'): supplier for supplier in suppliers if supplier.get('supplier_name')}
            
            # 6. 构建对账表数据
            reconciliation_data = []
            
            for supplier_name_key in all_supplier_names:
                if not supplier_name_key:
                    continue
                
                supplier_info = suppliers_dict.get(supplier_name_key, {})
                purchase_data = purchase_dict.get(supplier_name_key, {})
                payment_data = payment_dict.get(supplier_name_key, {})
                
                total_purchase_amount = purchase_data.get('total_purchase_amount', 0) or 0
                total_payment_amount = payment_data.get('total_payment_amount', 0) or 0
                balance = total_purchase_amount - total_payment_amount
                
                # 处理日期字段
                latest_purchase_date = purchase_data.get('latest_purchase_date')
                latest_payment_date = payment_data.get('latest_payment_date')
                
                latest_purchase_str = None
                if latest_purchase_date:
                    if isinstance(latest_purchase_date, datetime):
                        latest_purchase_str = latest_purchase_date.strftime('%Y-%m-%d')
                    else:
                        latest_purchase_str = str(latest_purchase_date)[:10]
                
                latest_payment_str = None
                if latest_payment_date:
                    if isinstance(latest_payment_date, datetime):
                        latest_payment_str = latest_payment_date.strftime('%Y-%m-%d')
                    else:
                        latest_payment_str = str(latest_payment_date)[:10]
                
                reconciliation_record = {
                    'supplier_name': supplier_name_key,
                    'supplier_credit_code': supplier_info.get('credit_code', ''),
                    'supplier_contact': supplier_info.get('contact_person', ''),
                    'supplier_phone': supplier_info.get('phone', ''),
                    'total_purchase_amount': round(total_purchase_amount, 2),
                    'total_payment_amount': round(total_payment_amount, 2),
                    'balance': round(balance, 2),
                    'purchase_count': purchase_data.get('purchase_count', 0) or 0,
                    'payment_count': payment_data.get('payment_count', 0) or 0,
                    'latest_purchase_date': latest_purchase_str,
                    'latest_payment_date': latest_payment_str,
                    'status': '正常' if balance >= 0 else '超付',
                    'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                reconciliation_data.append(reconciliation_record)
            
            # 按余额降序排序
            reconciliation_data.sort(key=lambda x: x['balance'], reverse=True)
            
            self.logger.info(f"供应商对账表查询优化完成，共 {len(reconciliation_data)} 条记录")
            return reconciliation_data
            
        except Exception as e:
            self.logger.error(f"供应商对账表查询优化失败: {str(e)}")
            raise
    
    def optimize_customer_reconciliation_query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        优化客户对账单查询
        
        Args:
            filters: 查询过滤条件
                - start_date: 开始日期
                - end_date: 结束日期
                - customer_name: 客户名称
                
        Returns:
            客户对账单数据列表
        """
        try:
            self.logger.info("开始执行优化的客户对账单查询")
            db = self._get_db_connection()
            
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            customer_name = filters.get('customer_name')
            
            # 构建日期过滤条件
            date_filter = self._build_date_filter(start_date, end_date)
            
            # 1. 获取客户基础信息
            customers_collection = db['customers']
            customer_filter = {}
            if customer_name:
                customer_filter = {'customer_name': customer_name}
            
            customers = list(customers_collection.find(customer_filter, {'_id': 0}))
            customer_names = [customer.get('customer_name', '') for customer in customers if customer.get('customer_name')]
            
            if not customer_names:
                self.logger.info("没有找到有效的客户名称")
                return []
            
            # 2. 构建销售数据聚合管道
            sales_pipeline = [
                {
                    '$match': {
                        'customer_name': {'$in': customer_names}
                    }
                }
            ]
            
            if date_filter:
                sales_pipeline[0]['$match']['outbound_date'] = date_filter
            
            sales_pipeline.extend([
                {
                    '$group': {
                        '_id': '$customer_name',
                        'total_sales_amount': {'$sum': '$outbound_amount'},
                        'sales_count': {'$sum': 1},
                        'latest_sales_date': {'$max': '$outbound_date'}
                    }
                }
            ])
            
            # 3. 构建收款数据聚合管道
            receipt_pipeline = [
                {
                    '$match': {
                        'customer_name': {'$in': customer_names}
                    }
                }
            ]
            
            if date_filter:
                receipt_pipeline[0]['$match']['receipt_date'] = date_filter
            
            receipt_pipeline.extend([
                {
                    '$group': {
                        '_id': '$customer_name',
                        'total_receipt_amount': {'$sum': '$amount'},
                        'receipt_count': {'$sum': 1},
                        'latest_receipt_date': {'$max': '$receipt_date'}
                    }
                }
            ])
            
            # 4. 并行执行聚合查询
            sales_collection = db['sales_outbound']
            receipt_collection = db['receipt_details']
            
            sales_aggregated = list(sales_collection.aggregate(sales_pipeline))
            receipt_aggregated = list(receipt_collection.aggregate(receipt_pipeline))
            
            sales_dict = {item['_id']: item for item in sales_aggregated}
            receipt_dict = {item['_id']: item for item in receipt_aggregated}
            
            # 5. 构建对账单数据
            reconciliation_data = []
            
            for customer in customers:
                customer_name_key = customer.get('customer_name', '')
                if not customer_name_key:
                    continue
                
                sales_data = sales_dict.get(customer_name_key, {})
                receipt_data = receipt_dict.get(customer_name_key, {})
                
                total_sales_amount = sales_data.get('total_sales_amount', 0) or 0
                total_receipt_amount = receipt_data.get('total_receipt_amount', 0) or 0
                balance = total_sales_amount - total_receipt_amount
                
                # 处理日期字段
                latest_sales_date = sales_data.get('latest_sales_date')
                latest_receipt_date = receipt_data.get('latest_receipt_date')
                
                latest_sales_str = None
                if latest_sales_date:
                    if isinstance(latest_sales_date, datetime):
                        latest_sales_str = latest_sales_date.strftime('%Y-%m-%d')
                    else:
                        latest_sales_str = str(latest_sales_date)[:10]
                
                latest_receipt_str = None
                if latest_receipt_date:
                    if isinstance(latest_receipt_date, datetime):
                        latest_receipt_str = latest_receipt_date.strftime('%Y-%m-%d')
                    else:
                        latest_receipt_str = str(latest_receipt_date)[:10]
                
                reconciliation_record = {
                    'customer_name': customer_name_key,
                    'customer_credit_code': customer.get('credit_code', ''),
                    'customer_contact': customer.get('contact_person', ''),
                    'customer_phone': customer.get('phone', ''),
                    'customer_address': customer.get('address', ''),
                    'total_sales_amount': round(total_sales_amount, 2),
                    'total_receipt_amount': round(total_receipt_amount, 2),
                    'balance': round(balance, 2),
                    'sales_count': sales_data.get('sales_count', 0) or 0,
                    'receipt_count': receipt_data.get('receipt_count', 0) or 0,
                    'latest_sales_date': latest_sales_str,
                    'latest_receipt_date': latest_receipt_str,
                    'status': '正常' if balance >= 0 else '超收',
                    'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                reconciliation_data.append(reconciliation_record)
            
            # 按余额降序排序
            reconciliation_data.sort(key=lambda x: x['balance'], reverse=True)
            
            self.logger.info(f"客户对账单查询优化完成，共 {len(reconciliation_data)} 条记录")
            return reconciliation_data
            
        except Exception as e:
            self.logger.error(f"客户对账单查询优化失败: {str(e)}")
            raise    

    def optimize_inventory_report_query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        优化库存报表查询
        
        Args:
            filters: 查询过滤条件
                - product_name: 产品名称
                
        Returns:
            库存报表数据列表
        """
        try:
            self.logger.info("开始执行优化的库存报表查询")
            db = self._get_db_connection()
            
            product_name = filters.get('product_name')
            
            # 构建聚合管道
            pipeline = []
            
            # 1. 匹配阶段 - 构建过滤条件
            match_conditions = {}
            
            if product_name:
                match_conditions['material_name'] = {'$regex': product_name, '$options': 'i'}
                
            if match_conditions:
                pipeline.append({'$match': match_conditions})
            
            # 2. 投影阶段 - 计算衍生字段和优化数据传输
            pipeline.append({
                '$project': {
                    'product_code': '$material_code',
                    'product_name': '$material_name',
                    'product_model': '$specification',
                    'unit': '$unit',
                    'current_stock': {
                        '$toDouble': {
                            '$ifNull': ['$stock_quantity', 0]
                        }
                    },
                    'inbound_amount': {
                        '$toDouble': {
                            '$ifNull': ['$inbound_amount', 0]
                        }
                    },
                    'inbound_quantity': {
                        '$toDouble': {
                            '$ifNull': ['$inbound_quantity', 1]
                        }
                    },
                    'safety_stock': {
                        '$toDouble': {
                            '$ifNull': ['$safety_stock', 0]
                        }
                    },
                    'last_update_date': '$code_mapping_time',
                    'unit_price': {
                        '$cond': {
                            'if': {'$gt': [{'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}, 0]},
                            'then': {
                                '$divide': [
                                    {'$toDouble': {'$ifNull': ['$inbound_amount', 0]}},
                                    {'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}
                                ]
                            },
                            'else': 0
                        }
                    },
                    'stock_value': {
                        '$multiply': [
                            {'$toDouble': {'$ifNull': ['$stock_quantity', 0]}},
                            {
                                '$cond': {
                                    'if': {'$gt': [{'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}, 0]},
                                    'then': {
                                        '$divide': [
                                            {'$toDouble': {'$ifNull': ['$inbound_amount', 0]}},
                                            {'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}
                                        ]
                                    },
                                    'else': 0
                                }
                            }
                        ]
                    },
                    'stock_status': {
                        '$switch': {
                            'branches': [
                                {
                                    'case': {'$lte': [{'$toDouble': {'$ifNull': ['$stock_quantity', 0]}}, 0]},
                                    'then': '缺货'
                                },
                                {
                                    'case': {
                                        '$lte': [
                                            {'$toDouble': {'$ifNull': ['$stock_quantity', 0]}},
                                            {'$toDouble': {'$ifNull': ['$safety_stock', 0]}}
                                        ]
                                    },
                                    'then': '低库存'
                                }
                            ],
                            'default': '正常'
                        }
                    },
                    'supplier_name': {'$literal': ''},  # inventory_stats中没有供应商信息
                    'generated_date': {'$literal': datetime.now().isoformat()},
                    '_id': 0
                }
            })
            
            # 3. 排序阶段 - 按库存价值降序
            pipeline.append({'$sort': {'stock_value': -1}})
            
            # 执行聚合查询
            inventory_collection = db['inventory_stats']
            report_data = list(inventory_collection.aggregate(pipeline))
            
            self.logger.info(f"库存报表查询优化完成，共 {len(report_data)} 条记录")
            return report_data
            
        except Exception as e:
            self.logger.error(f"库存报表查询优化失败: {str(e)}")
            raise
    
    def optimize_sales_report_query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        优化销售统计报表查询
        
        Args:
            filters: 查询过滤条件
                - start_date: 开始日期
                - end_date: 结束日期
                - customer_name: 客户名称
                - product_name: 产品名称
                
        Returns:
            销售统计报表数据列表
        """
        try:
            self.logger.info("开始执行优化的销售统计报表查询")
            db = self._get_db_connection()
            
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            customer_name = filters.get('customer_name')
            product_name = filters.get('product_name')
            
            # 构建聚合管道
            pipeline = []
            
            # 1. 匹配阶段 - 构建过滤条件
            match_conditions = {}
            
            # 日期范围筛选
            date_filter = self._build_date_filter(start_date, end_date)
            if date_filter:
                match_conditions['outbound_date'] = date_filter
                
            # 客户名称筛选
            if customer_name:
                match_conditions['customer_name'] = {'$regex': customer_name, '$options': 'i'}
                
            # 产品名称筛选
            if product_name:
                match_conditions['material_name'] = {'$regex': product_name, '$options': 'i'}
                
            if match_conditions:
                pipeline.append({'$match': match_conditions})
            
            # 2. 分组聚合阶段
            pipeline.append({
                '$group': {
                    '_id': {
                        'material_code': '$material_code',
                        'material_name': '$material_name'
                    },
                    'product_model': {'$first': '$specification'},
                    'unit': {'$first': '$unit'},
                    'total_quantity': {'$sum': '$quantity'},
                    'total_amount': {'$sum': '$outbound_amount'},
                    'sales_count': {'$sum': 1},
                    'customers': {'$addToSet': '$customer_name'},
                    'latest_sale_date': {'$max': '$outbound_date'}
                }
            })
            
            # 3. 投影阶段 - 计算衍生字段
            pipeline.append({
                '$project': {
                    'product_code': '$_id.material_code',
                    'product_name': '$_id.material_name',
                    'product_model': 1,
                    'unit': 1,
                    'total_quantity': 1,
                    'total_amount': 1,
                    'sales_count': 1,
                    'customer_count': {'$size': '$customers'},
                    'latest_sale_date': 1,
                    'avg_unit_price': {
                        '$cond': {
                            'if': {'$gt': ['$total_quantity', 0]},
                            'then': {'$divide': ['$total_amount', '$total_quantity']},
                            'else': 0
                        }
                    },
                    'sales_trend': {
                        '$switch': {
                            'branches': [
                                {'case': {'$gte': ['$sales_count', 10]}, 'then': '热销'},
                                {'case': {'$gte': ['$sales_count', 5]}, 'then': '正常'}
                            ],
                            'default': '滞销'
                        }
                    },
                    'generated_date': {'$literal': datetime.now().isoformat()},
                    '_id': 0
                }
            })
            
            # 4. 排序阶段 - 按销售金额降序
            pipeline.append({'$sort': {'total_amount': -1}})
            
            # 执行聚合查询
            sales_collection = db['sales_outbound']
            report_data = list(sales_collection.aggregate(pipeline))
            
            self.logger.info(f"销售统计报表查询优化完成，共 {len(report_data)} 个产品")
            return report_data
            
        except Exception as e:
            self.logger.error(f"销售统计报表查询优化失败: {str(e)}")
            raise
    
    def optimize_purchase_report_query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        优化采购统计报表查询
        
        Args:
            filters: 查询过滤条件
                - start_date: 开始日期
                - end_date: 结束日期
                - supplier_name: 供应商名称
                - product_name: 产品名称
                
        Returns:
            采购统计报表数据列表
        """
        try:
            self.logger.info("开始执行优化的采购统计报表查询")
            db = self._get_db_connection()
            
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            supplier_name = filters.get('supplier_name')
            product_name = filters.get('product_name')
            
            # 构建聚合管道
            pipeline = []
            
            # 1. 匹配阶段 - 构建过滤条件
            match_conditions = {}
            
            # 日期范围筛选
            date_filter = self._build_date_filter(start_date, end_date)
            if date_filter:
                match_conditions['inbound_date'] = date_filter
                
            # 供应商名称筛选
            if supplier_name:
                match_conditions['supplier_name'] = {'$regex': supplier_name, '$options': 'i'}
                
            # 产品名称筛选
            if product_name:
                match_conditions['material_name'] = {'$regex': product_name, '$options': 'i'}
                
            if match_conditions:
                pipeline.append({'$match': match_conditions})
            
            # 2. 分组聚合阶段
            pipeline.append({
                '$group': {
                    '_id': {
                        'material_code': '$material_code',
                        'material_name': '$material_name'
                    },
                    'product_model': {'$first': '$specification'},
                    'unit': {'$first': '$unit'},
                    'total_quantity': {'$sum': '$quantity'},
                    'total_amount': {'$sum': '$amount'},
                    'purchase_count': {'$sum': 1},
                    'suppliers': {'$addToSet': '$supplier_name'},
                    'latest_purchase_date': {'$max': '$inbound_date'},
                    'min_unit_price': {'$min': '$purchase_unit_price'},
                    'max_unit_price': {'$max': '$purchase_unit_price'}
                }
            })
            
            # 3. 投影阶段 - 计算衍生字段
            pipeline.append({
                '$project': {
                    'product_code': '$_id.material_code',
                    'product_name': '$_id.material_name',
                    'product_model': 1,
                    'unit': 1,
                    'total_quantity': 1,
                    'total_amount': 1,
                    'purchase_count': 1,
                    'supplier_count': {'$size': '$suppliers'},
                    'latest_purchase_date': 1,
                    'min_unit_price': 1,
                    'max_unit_price': 1,
                    'avg_unit_price': {
                        '$cond': {
                            'if': {'$gt': ['$total_quantity', 0]},
                            'then': {'$divide': ['$total_amount', '$total_quantity']},
                            'else': 0
                        }
                    },
                    'purchase_frequency': {
                        '$switch': {
                            'branches': [
                                {'case': {'$gte': ['$purchase_count', 10]}, 'then': '高频'},
                                {'case': {'$gte': ['$purchase_count', 5]}, 'then': '正常'}
                            ],
                            'default': '低频'
                        }
                    },
                    'price_stability': {
                        '$switch': {
                            'branches': [
                                {
                                    'case': {
                                        '$and': [
                                            {'$gt': ['$min_unit_price', 0]},
                                            {'$lte': [{'$divide': [{'$subtract': ['$max_unit_price', '$min_unit_price']}, '$min_unit_price']}, 0.05]}
                                        ]
                                    },
                                    'then': '稳定'
                                },
                                {
                                    'case': {
                                        '$and': [
                                            {'$gt': ['$min_unit_price', 0]},
                                            {'$lte': [{'$divide': [{'$subtract': ['$max_unit_price', '$min_unit_price']}, '$min_unit_price']}, 0.15]}
                                        ]
                                    },
                                    'then': '一般'
                                }
                            ],
                            'default': '波动大'
                        }
                    },
                    'generated_date': {'$literal': datetime.now().isoformat()},
                    '_id': 0
                }
            })
            
            # 4. 排序阶段 - 按采购金额降序
            pipeline.append({'$sort': {'total_amount': -1}})
            
            # 执行聚合查询
            purchase_collection = db['purchase_inbound']
            report_data = list(purchase_collection.aggregate(pipeline))
            
            self.logger.info(f"采购统计报表查询优化完成，共 {len(report_data)} 个产品")
            return report_data
            
        except Exception as e:
            self.logger.error(f"采购统计报表查询优化失败: {str(e)}")
            raise
    
    def get_query_execution_plan(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取查询执行计划
        
        Args:
            query: 查询条件
            
        Returns:
            查询执行计划信息
        """
        try:
            self.logger.info("获取查询执行计划")
            db = self._get_db_connection()
            
            collection_name = query.get('collection', 'purchase_inbound')
            query_filter = query.get('filter', {})
            
            collection = db[collection_name]
            
            # 获取查询执行计划
            explain_result = collection.find(query_filter).explain()
            
            execution_plan = {
                'collection': collection_name,
                'query_filter': query_filter,
                'execution_stats': explain_result.get('executionStats', {}),
                'winning_plan': explain_result.get('queryPlanner', {}).get('winningPlan', {}),
                'rejected_plans': explain_result.get('queryPlanner', {}).get('rejectedPlans', []),
                'index_usage': explain_result.get('executionStats', {}).get('totalKeysExamined', 0),
                'documents_examined': explain_result.get('executionStats', {}).get('totalDocsExamined', 0),
                'documents_returned': explain_result.get('executionStats', {}).get('totalDocsReturned', 0),
                'execution_time_ms': explain_result.get('executionStats', {}).get('executionTimeMillis', 0)
            }
            
            self.logger.info(f"查询执行计划获取完成，执行时间: {execution_plan['execution_time_ms']}ms")
            return execution_plan
            
        except Exception as e:
            self.logger.error(f"获取查询执行计划失败: {str(e)}")
            raise


def main():
    """测试查询优化器功能"""
    import json
    
    logger = EnhancedLogger("query_optimizer_test")
    optimizer = QueryOptimizer(logger)
    
    try:
        # 测试供应商对账表查询优化
        print("=== 测试供应商对账表查询优化 ===")
        supplier_filters = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        supplier_result = optimizer.optimize_supplier_reconciliation_query(supplier_filters)
        print(f"供应商对账表查询结果: {len(supplier_result)} 条记录")
        
        # 测试客户对账单查询优化
        print("\n=== 测试客户对账单查询优化 ===")
        customer_filters = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        customer_result = optimizer.optimize_customer_reconciliation_query(customer_filters)
        print(f"客户对账单查询结果: {len(customer_result)} 条记录")
        
        # 测试库存报表查询优化
        print("\n=== 测试库存报表查询优化 ===")
        inventory_filters = {}
        inventory_result = optimizer.optimize_inventory_report_query(inventory_filters)
        print(f"库存报表查询结果: {len(inventory_result)} 条记录")
        
        print("\n查询优化器测试完成！")
        
    except Exception as e:
        logger.error(f"查询优化器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()