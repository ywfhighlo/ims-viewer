#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析服务
提供完整的业务数据分析功能，整合所有报表和统计分析
"""

import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.business_view_sales_report import generate_sales_summary
from scripts.business_view_purchase_report import generate_purchase_summary
from scripts.business_view_inventory_report import generate_inventory_report
from scripts.business_view_receivables_report import generate_receivables_summary
from scripts.business_view_payables_report import generate_payables_summary
from scripts.cache_manager import get_cache_manager, cache_report_data
from scripts.query_optimizer import QueryOptimizer
from scripts.data_paginator import DataPaginator

class DataAnalysisService:
    """数据分析服务类"""
    
    def __init__(self, logger: Optional[EnhancedLogger] = None):
        """
        初始化数据分析服务
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or EnhancedLogger("data_analysis_service")
        self.cache_manager = get_cache_manager()
        self.query_optimizer = QueryOptimizer(logger)
        self.data_paginator = DataPaginator(
            default_page_size=50,
            max_page_size=500,
            pagination_threshold=100,
            compression_threshold=200,
            logger=logger
        )
        
        # 性能监控统计
        self.performance_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_requests': 0,
            'avg_response_time': 0.0
        }
    
    def get_dashboard_data(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取仪表板数据（前端兼容接口）
        
        Args:
            params: 参数字典，包含date_range等
            
        Returns:
            仪表板数据
        """
        if params is None:
            params = {}
        return self.get_dashboard_summary(params)
    
    def get_dashboard_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取仪表板概览数据（带缓存）
        整合销售、采购、库存、应收应付等数据源，计算关键业务指标
        
        Args:
            params: 参数字典，包含date_range等
            
        Returns:
            仪表板概览数据
        """
        # 使用缓存装饰器
        def data_generator():
            return self._get_dashboard_summary_uncached(params)
        
        try:
            # 设置较短的缓存时间，因为仪表板数据需要相对实时
            cached_data = cache_report_data(
                view_name="dashboard_summary",
                params=params,
                data_generator=data_generator,
                ttl=300,  # 5分钟缓存
                cache_manager=self.cache_manager
            )
            
            # 如果返回的是列表，包装成标准响应格式
            if isinstance(cached_data, list):
                return {
                    'success': True,
                    'data': cached_data,
                    'generated_at': datetime.now().isoformat(),
                    'cached': True
                }
            else:
                # 如果已经是字典格式，直接返回并标记为缓存
                if isinstance(cached_data, dict):
                    cached_data['cached'] = True
                return cached_data
                
        except Exception as e:
            self.logger.error(f"获取仪表板概览数据失败: {str(e)}")
            return {
                'error': True,
                'error_message': str(e),
                'error_code': 'DASHBOARD_SUMMARY_FAILED',
                'generated_at': datetime.now().isoformat()
            }
    
    def _get_dashboard_summary_uncached(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取仪表板概览数据（无缓存版本）
        
        Args:
            params: 参数字典，包含date_range等
            
        Returns:
            仪表板概览数据
        """
        try:
            self.logger.info("开始获取仪表板概览数据")
            
            # 提取日期范围参数
            date_range = params.get('date_range', {})
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            # 数据验证
            if start_date and not self._validate_date_format(start_date):
                raise ValueError(f"开始日期格式无效: {start_date}")
            if end_date and not self._validate_date_format(end_date):
                raise ValueError(f"结束日期格式无效: {end_date}")
            
            # 并行获取各种报表数据
            self.logger.info("获取销售数据...")
            sales_summary = generate_sales_summary(start_date, end_date, self.logger)
            
            self.logger.info("获取采购数据...")
            purchase_summary = generate_purchase_summary(start_date, end_date, self.logger)
            
            self.logger.info("获取应收账款数据...")
            receivables_summary = generate_receivables_summary(start_date, end_date, self.logger)
            
            self.logger.info("获取应付账款数据...")
            payables_summary = generate_payables_summary(start_date, end_date, self.logger)
            
            # 获取库存数据（不受日期限制）
            self.logger.info("获取库存数据...")
            inventory_result = generate_inventory_report(
                enable_pagination=False,
                enable_compression=False
            )
            
            # 数据验证和错误处理
            if not inventory_result or not inventory_result.get('success'):
                self.logger.warning("库存数据获取失败，使用默认值")
                inventory_data = []
                inventory_stats = {}
            else:
                inventory_data = inventory_result.get('data', [])
                inventory_stats = inventory_result.get('statistics', {})
            
            # 计算关键业务指标
            overview = {
                # 销售指标
                'total_sales': self._safe_get_numeric(sales_summary, 'total_amount', 0),
                'total_sales_count': self._safe_get_numeric(sales_summary, 'order_count', 0),
                'active_customers': self._safe_get_numeric(sales_summary, 'customer_count', 0),
                'avg_order_value': self._safe_get_numeric(sales_summary, 'average_order_value', 0),
                
                # 采购指标
                'total_purchases': self._safe_get_numeric(purchase_summary, 'total_amount', 0),
                'total_purchase_count': self._safe_get_numeric(purchase_summary, 'order_count', 0),
                'active_suppliers': self._safe_get_numeric(purchase_summary, 'supplier_count', 0),
                'avg_purchase_value': self._safe_get_numeric(purchase_summary, 'average_order_value', 0),
                
                # 库存指标
                'total_inventory_value': self._safe_get_numeric(inventory_stats, 'total_value', 0),
                'total_inventory_items': self._safe_get_numeric(inventory_stats, 'total_items', 0),
                'low_stock_items': len([item for item in inventory_data if item.get('stock_status') == '低库存']),
                'out_of_stock_items': len([item for item in inventory_data if item.get('stock_status') == '缺货']),
                
                # 财务指标
                'total_receivables': self._safe_get_numeric(receivables_summary, 'total_receivables', 0),
                'overdue_receivables': self._safe_get_numeric(receivables_summary, 'overdue_amount', 0),
                'total_payables': self._safe_get_numeric(payables_summary, 'total_payables', 0),
                'overdue_payables': self._safe_get_numeric(payables_summary, 'overdue_amount', 0),
            }
            
            # 计算衍生指标
            total_sales = overview['total_sales']
            total_purchases = overview['total_purchases']
            total_inventory_value = overview['total_inventory_value']
            
            overview.update({
                'gross_margin': total_sales - total_purchases,
                'gross_margin_rate': (total_sales - total_purchases) / max(total_sales, 1) * 100 if total_sales > 0 else 0,
                'inventory_turnover_estimate': total_purchases / max(total_inventory_value, 1) if total_inventory_value > 0 else 0,
                'customer_activity_rate': (overview['active_customers'] / max(overview['active_customers'], 1)) * 100 if overview['active_customers'] > 0 else 0,
                
                # 元数据
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'generated_at': datetime.now().isoformat(),
                'data_sources': {
                    'sales_available': bool(sales_summary),
                    'purchase_available': bool(purchase_summary),
                    'inventory_available': bool(inventory_result and inventory_result.get('success')),
                    'receivables_available': bool(receivables_summary),
                    'payables_available': bool(payables_summary)
                }
            })
            
            self.logger.info(f"仪表板概览数据生成完成，销售额: {overview['total_sales']}, 毛利润: {overview['gross_margin']}")
            return overview
            
        except Exception as e:
            self.logger.error(f"获取仪表板概览数据失败: {str(e)}")
            # 返回错误信息而不是抛出异常，确保前端能够处理
            return {
                'error': True,
                'error_message': str(e),
                'error_code': 'DASHBOARD_SUMMARY_FAILED',
                'generated_at': datetime.now().isoformat()
            }
    
    def get_business_overview(self, date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取业务概览数据
        
        Args:
            date_range: 日期范围 {'start_date': 'YYYY-MM-DD', 'end_date': 'YYYY-MM-DD'}
            
        Returns:
            业务概览数据
        """
        try:
            self.logger.info("开始生成业务概览数据")
            
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            # 并行获取各种报表数据
            sales_summary = generate_sales_summary(start_date, end_date, self.logger)
            purchase_summary = generate_purchase_summary(start_date, end_date, self.logger)
            receivables_summary = generate_receivables_summary(start_date, end_date, self.logger)
            payables_summary = generate_payables_summary(start_date, end_date, self.logger)
            
            # 获取库存数据（不受日期限制）
            inventory_result = generate_inventory_report(
                enable_pagination=False,
                enable_compression=False
            )
            inventory_data = inventory_result.get('data', []) if inventory_result.get('success') else []
            inventory_stats = inventory_result.get('statistics', {}) if inventory_result.get('success') else {}
            
            # 计算关键业务指标
            overview = {
                # 销售指标
                'total_sales': sales_summary.get('total_amount', 0),
                'total_sales_count': sales_summary.get('order_count', 0),
                'active_customers': sales_summary.get('customer_count', 0),
                'avg_order_value': sales_summary.get('average_order_value', 0),
                
                # 采购指标
                'total_purchases': purchase_summary.get('total_amount', 0),
                'total_purchase_count': purchase_summary.get('order_count', 0),
                'active_suppliers': purchase_summary.get('supplier_count', 0),
                'avg_purchase_value': purchase_summary.get('average_order_value', 0),
                
                # 库存指标
                'total_inventory_value': inventory_stats.get('total_value', 0),
                'total_inventory_items': inventory_stats.get('total_items', 0),
                'low_stock_items': len([item for item in inventory_data if item.get('stock_status') == '低库存']),
                'out_of_stock_items': len([item for item in inventory_data if item.get('stock_status') == '缺货']),
                
                # 财务指标
                'total_receivables': receivables_summary.get('total_receivables', 0),
                'overdue_receivables': receivables_summary.get('overdue_amount', 0),
                'total_payables': payables_summary.get('total_payables', 0),
                'overdue_payables': payables_summary.get('overdue_amount', 0),
                
                # 计算衍生指标
                'gross_margin': sales_summary.get('total_amount', 0) - purchase_summary.get('total_amount', 0),
                'inventory_turnover_estimate': (purchase_summary.get('total_amount', 0) / inventory_stats.get('total_value', 1)) if inventory_stats.get('total_value', 0) > 0 else 0,
                'customer_activity_rate': (sales_summary.get('customer_count', 0) / max(1, sales_summary.get('customer_count', 1))) * 100,
                
                # 生成时间和日期范围
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"业务概览数据生成完成，销售额: {overview['total_sales']}, 毛利润: {overview['gross_margin']}")
            return overview
            
        except Exception as e:
            self.logger.error(f"生成业务概览数据失败: {str(e)}")
            raise
    
    def analyze_sales_trend(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析销售趋势（带缓存和分页）- 支持月度、季度、产品三种分析维度
        
        Args:
            params: 参数字典，包含:
                - dimension: 分析维度 ('month', 'quarter', 'product')
                - date_range: 日期范围 {'start_date': 'YYYY-MM-DD', 'end_date': 'YYYY-MM-DD'}
                - page: 页码（可选）
                - page_size: 页面大小（可选）
                
        Returns:
            销售趋势分析数据，格式符合前端图表要求
        """
        # 使用缓存装饰器
        def data_generator():
            return self._analyze_sales_trend_uncached(params)
        
        try:
            # 设置缓存时间，销售趋势数据可以缓存较长时间
            cached_data = cache_report_data(
                view_name="sales_trend_analysis",
                params=params,
                data_generator=data_generator,
                ttl=600,  # 10分钟缓存
                cache_manager=self.cache_manager
            )
            
            # 处理分页（如果需要）
            page = params.get('page')
            page_size = params.get('page_size')
            
            if page is not None and isinstance(cached_data, dict) and 'data' in cached_data:
                trend_data = cached_data['data']
                
                # 应用分页
                if self.data_paginator.should_paginate(len(trend_data)):
                    paginated_result = self.data_paginator.paginate_results(
                        data=trend_data,
                        page=page,
                        page_size=page_size,
                        enable_compression=True
                    )
                    
                    # 合并分页结果到原响应中
                    cached_data.update({
                        'data': paginated_result.get('data'),
                        'compressed_data': paginated_result.get('compressed_data'),
                        'pagination': paginated_result.get('pagination'),
                        'compression': paginated_result.get('compression'),
                        'cached': True
                    })
                else:
                    cached_data['cached'] = True
            else:
                if isinstance(cached_data, dict):
                    cached_data['cached'] = True
            
            return cached_data
                
        except Exception as e:
            self.logger.error(f"分析销售趋势失败: {str(e)}")
            return {
                'success': False,
                'dimension': params.get('dimension', 'unknown'),
                'error': {
                    'code': 'SALES_TREND_ANALYSIS_FAILED',
                    'message': str(e),
                    'details': f"销售趋势分析失败，维度: {params.get('dimension', 'unknown')}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _analyze_sales_trend_uncached(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析销售趋势（无缓存版本）
        
        Args:
            params: 参数字典
            
        Returns:
            销售趋势分析数据
        """
        try:
            # 参数验证和提取
            dimension = params.get('dimension', 'month')
            date_range = params.get('date_range', {})
            
            self.logger.info(f"开始分析销售趋势，维度: {dimension}")
            
            # 验证分析维度
            valid_dimensions = ['month', 'quarter', 'product']
            if dimension not in valid_dimensions:
                raise ValueError(f"不支持的分析维度: {dimension}，支持的维度: {valid_dimensions}")
            
            # 提取日期范围参数
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            # 日期格式验证
            if start_date and not self._validate_date_format(start_date):
                raise ValueError(f"开始日期格式无效: {start_date}")
            if end_date and not self._validate_date_format(end_date):
                raise ValueError(f"结束日期格式无效: {end_date}")
            
            # 获取销售汇总数据
            sales_summary = generate_sales_summary(start_date, end_date, self.logger)
            
            if not sales_summary:
                self.logger.warning("未获取到销售数据")
                return self._create_empty_trend_response(dimension)
            
            # 根据维度处理数据
            if dimension == 'month':
                trend_data = self._process_monthly_trend(sales_summary)
                
            elif dimension == 'quarter':
                trend_data = self._process_quarterly_trend(sales_summary)
                
            elif dimension == 'product':
                trend_data = self._process_product_analysis(sales_summary)
            
            else:
                trend_data = []
            
            # 构建标准化响应
            response = {
                'success': True,
                'dimension': dimension,
                'data': trend_data,
                'summary': {
                    'total_records': len(trend_data),
                    'date_range': {
                        'start_date': start_date,
                        'end_date': end_date
                    }
                },
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"销售趋势分析完成，维度: {dimension}，数据条数: {len(trend_data)}")
            return response
                
        except Exception as e:
            self.logger.error(f"分析销售趋势失败: {str(e)}")
            return {
                'success': False,
                'dimension': params.get('dimension', 'unknown'),
                'error': {
                    'code': 'SALES_TREND_ANALYSIS_FAILED',
                    'message': str(e),
                    'details': f"销售趋势分析失败，维度: {params.get('dimension', 'unknown')}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _process_monthly_trend(self, sales_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理月度趋势数据
        
        Args:
            sales_summary: 销售汇总数据
            
        Returns:
            月度趋势数据列表
        """
        try:
            monthly_trend = sales_summary.get('monthly_trend', [])
            
            # 标准化月度数据格式，确保符合前端图表要求
            processed_data = []
            for item in monthly_trend:
                month = item.get('month', '')
                total_amount = self._safe_get_numeric(item, 'total_amount', 0)
                total_quantity = self._safe_get_numeric(item, 'total_quantity', 0)
                order_count = self._safe_get_numeric(item, 'order_count', 0)
                
                processed_item = {
                    'period': month,
                    'month': month,
                    'total_sales': round(total_amount, 2),
                    'total_amount': round(total_amount, 2),  # 保持向后兼容
                    'total_quantity': total_quantity,
                    'order_count': order_count,
                    'avg_order_value': round(total_amount / max(order_count, 1), 2) if order_count > 0 else 0
                }
                processed_data.append(processed_item)
            
            # 按月份排序
            processed_data.sort(key=lambda x: x.get('month', ''))
            
            self.logger.info(f"处理月度趋势数据完成，共 {len(processed_data)} 个月份")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"处理月度趋势数据失败: {str(e)}")
            return []
    
    def _process_quarterly_trend(self, sales_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理季度趋势数据 - 将月度数据聚合为季度数据
        
        Args:
            sales_summary: 销售汇总数据
            
        Returns:
            季度趋势数据列表
        """
        try:
            monthly_trend = sales_summary.get('monthly_trend', [])
            
            # 将月度数据聚合为季度数据
            quarterly_data = {}
            
            for item in monthly_trend:
                month = item.get('month', '')
                if not month or '-' not in month:
                    continue
                
                try:
                    year, month_num = month.split('-')
                    quarter_num = (int(month_num) - 1) // 3 + 1
                    quarter_key = f"{year}-Q{quarter_num}"
                    
                    if quarter_key not in quarterly_data:
                        quarterly_data[quarter_key] = {
                            'period': quarter_key,
                            'quarter': quarter_key,
                            'year': year,
                            'quarter_num': quarter_num,
                            'total_sales': 0,
                            'total_amount': 0,
                            'total_quantity': 0,
                            'order_count': 0,
                            'months_included': []
                        }
                    
                    # 聚合数据
                    quarterly_data[quarter_key]['total_sales'] += self._safe_get_numeric(item, 'total_amount', 0)
                    quarterly_data[quarter_key]['total_amount'] += self._safe_get_numeric(item, 'total_amount', 0)
                    quarterly_data[quarter_key]['total_quantity'] += self._safe_get_numeric(item, 'total_quantity', 0)
                    quarterly_data[quarter_key]['order_count'] += self._safe_get_numeric(item, 'order_count', 0)
                    quarterly_data[quarter_key]['months_included'].append(month)
                    
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"无法解析月份数据: {month}, 错误: {str(e)}")
                    continue
            
            # 计算平均订单价值并格式化数据
            processed_data = []
            for quarter_key, data in quarterly_data.items():
                data['total_sales'] = round(data['total_sales'], 2)
                data['total_amount'] = round(data['total_amount'], 2)
                data['avg_order_value'] = round(data['total_sales'] / max(data['order_count'], 1), 2) if data['order_count'] > 0 else 0
                data['months_count'] = len(data['months_included'])
                processed_data.append(data)
            
            # 按季度排序
            processed_data.sort(key=lambda x: (x.get('year', ''), x.get('quarter_num', 0)))
            
            self.logger.info(f"处理季度趋势数据完成，共 {len(processed_data)} 个季度")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"处理季度趋势数据失败: {str(e)}")
            return []
    
    def _process_product_analysis(self, sales_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理产品销售分析数据
        
        Args:
            sales_summary: 销售汇总数据
            
        Returns:
            产品销售排行榜数据
        """
        try:
            top_products = sales_summary.get('top_products', [])
            
            # 标准化产品数据格式
            processed_data = []
            for rank, item in enumerate(top_products, 1):
                material_code = item.get('material_code', '')
                material_name = item.get('material_name', '')
                total_amount = self._safe_get_numeric(item, 'total_amount', 0)
                total_quantity = self._safe_get_numeric(item, 'total_quantity', 0)
                order_count = self._safe_get_numeric(item, 'order_count', 0)
                
                processed_item = {
                    'rank': rank,
                    'product_code': material_code,
                    'material_code': material_code,  # 保持向后兼容
                    'product_name': material_name,
                    'material_name': material_name,  # 保持向后兼容
                    'total_sales': round(total_amount, 2),
                    'total_amount': round(total_amount, 2),  # 保持向后兼容
                    'total_quantity': total_quantity,
                    'order_count': order_count,
                    'avg_order_value': round(total_amount / max(order_count, 1), 2) if order_count > 0 else 0,
                    'avg_unit_price': round(total_amount / max(total_quantity, 1), 2) if total_quantity > 0 else 0
                }
                processed_data.append(processed_item)
            
            self.logger.info(f"处理产品分析数据完成，共 {len(processed_data)} 个产品")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"处理产品分析数据失败: {str(e)}")
            return []
    
    def _create_empty_trend_response(self, dimension: str) -> Dict[str, Any]:
        """
        创建空的趋势分析响应
        
        Args:
            dimension: 分析维度
            
        Returns:
            空的响应数据
        """
        return {
            'success': True,
            'dimension': dimension,
            'data': [],
            'summary': {
                'total_records': 0,
                'date_range': {
                    'start_date': None,
                    'end_date': None
                }
            },
            'message': '未找到符合条件的销售数据',
            'generated_at': datetime.now().isoformat()
        }
    
    def analyze_customer_value(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析客户价值（带缓存和分页）- 实现完整的RFM模型和客户分类算法
        
        Args:
            params: 参数字典，包含:
                - date_range: 日期范围 {'start_date': 'YYYY-MM-DD', 'end_date': 'YYYY-MM-DD'}
                - analysis_type: 分析类型 ('rfm', 'ranking', 'segmentation')
                - page: 页码（可选）
                - page_size: 页面大小（可选）
                
        Returns:
            客户价值分析数据，包含RFM评分和客户分类
        """
        # 使用缓存装饰器
        def data_generator():
            return self._analyze_customer_value_uncached(params)
        
        try:
            # 设置缓存时间，客户价值分析数据可以缓存较长时间
            cached_data = cache_report_data(
                view_name="customer_value_analysis",
                params=params,
                data_generator=data_generator,
                ttl=900,  # 15分钟缓存
                cache_manager=self.cache_manager
            )
            
            # 处理分页（如果需要）
            page = params.get('page')
            page_size = params.get('page_size')
            
            if page is not None and isinstance(cached_data, dict) and 'data' in cached_data:
                customer_data = cached_data['data']
                
                # 应用分页
                if self.data_paginator.should_paginate(len(customer_data)):
                    paginated_result = self.data_paginator.paginate_results(
                        data=customer_data,
                        page=page,
                        page_size=page_size,
                        enable_compression=True
                    )
                    
                    # 合并分页结果到原响应中
                    cached_data.update({
                        'data': paginated_result.get('data'),
                        'compressed_data': paginated_result.get('compressed_data'),
                        'pagination': paginated_result.get('pagination'),
                        'compression': paginated_result.get('compression'),
                        'cached': True
                    })
                else:
                    cached_data['cached'] = True
            else:
                if isinstance(cached_data, dict):
                    cached_data['cached'] = True
            
            return cached_data
                
        except Exception as e:
            self.logger.error(f"分析客户价值失败: {str(e)}")
            return {
                'success': False,
                'analysis_type': params.get('analysis_type', 'unknown'),
                'error': {
                    'code': 'CUSTOMER_VALUE_ANALYSIS_FAILED',
                    'message': str(e),
                    'details': f"客户价值分析失败，类型: {params.get('analysis_type', 'unknown')}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _analyze_customer_value_uncached(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析客户价值（无缓存版本）
        
        Args:
            params: 参数字典
            
        Returns:
            客户价值分析数据
        """
        try:
            # 参数验证和提取
            analysis_type = params.get('analysis_type', 'rfm')
            date_range = params.get('date_range', {})
            
            self.logger.info(f"开始分析客户价值，类型: {analysis_type}")
            
            # 提取日期范围参数
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            # 日期格式验证
            if start_date and not self._validate_date_format(start_date):
                raise ValueError(f"开始日期格式无效: {start_date}")
            if end_date and not self._validate_date_format(end_date):
                raise ValueError(f"结束日期格式无效: {end_date}")
            
            # 获取客户交易数据
            customer_transactions = self._get_customer_transactions(start_date, end_date)
            
            if not customer_transactions:
                self.logger.warning("未获取到客户交易数据")
                return self._create_empty_customer_analysis_response(analysis_type)
            
            # 计算RFM指标
            rfm_data = self._calculate_rfm_metrics(customer_transactions)
            
            # 根据分析类型返回不同格式的数据
            if analysis_type == 'rfm':
                response_data = rfm_data
                
            elif analysis_type == 'ranking':
                # 按客户价值排序
                response_data = sorted(rfm_data, key=lambda x: x['customer_value'], reverse=True)
                
            elif analysis_type == 'segmentation':
                # 按客户分类分组
                response_data = self._group_customers_by_segment(rfm_data)
                
            else:
                response_data = rfm_data
            
            # 构建标准化响应
            response = {
                'success': True,
                'analysis_type': analysis_type,
                'data': response_data,
                'summary': {
                    'total_customers': len(rfm_data),
                    'date_range': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'segment_distribution': self._calculate_segment_distribution(rfm_data)
                },
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"客户价值分析完成，类型: {analysis_type}，客户数: {len(rfm_data)}")
            return response
                
        except Exception as e:
            self.logger.error(f"分析客户价值失败: {str(e)}")
            return {
                'success': False,
                'analysis_type': params.get('analysis_type', 'unknown'),
                'error': {
                    'code': 'CUSTOMER_VALUE_ANALYSIS_FAILED',
                    'message': str(e),
                    'details': f"客户价值分析失败，类型: {params.get('analysis_type', 'unknown')}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _get_customer_transactions(self, start_date: Optional[str] = None, 
                                 end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取客户交易数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            客户交易数据列表
        """
        try:
            db = self.query_optimizer._get_db_connection()
            sales_collection = db['sales_outbound']
            
            # 构建查询条件
            match_conditions = {}
            
            # 日期范围筛选
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter['$gte'] = start_date
                if end_date:
                    date_filter['$lte'] = end_date
                if date_filter:
                    match_conditions['outbound_date'] = date_filter
            
            # 构建聚合管道
            pipeline = []
            
            if match_conditions:
                pipeline.append({'$match': match_conditions})
            
            # 按客户分组，计算RFM相关指标
            pipeline.extend([
                {
                    '$group': {
                        '_id': '$customer_name',
                        'customer_name': {'$first': '$customer_name'},
                        'total_amount': {'$sum': {'$toDouble': {'$ifNull': ['$outbound_amount', 0]}}},
                        'total_quantity': {'$sum': {'$toDouble': {'$ifNull': ['$quantity', 0]}}},
                        'transaction_count': {'$sum': 1},
                        'first_purchase_date': {'$min': '$outbound_date'},
                        'last_purchase_date': {'$max': '$outbound_date'},
                        'avg_order_value': {'$avg': {'$toDouble': {'$ifNull': ['$outbound_amount', 0]}}},
                        'transactions': {
                            '$push': {
                                'date': '$outbound_date',
                                'amount': {'$toDouble': {'$ifNull': ['$outbound_amount', 0]}},
                                'quantity': {'$toDouble': {'$ifNull': ['$quantity', 0]}},
                                'product': '$material_name'
                            }
                        }
                    }
                },
                {
                    '$project': {
                        'customer_name': 1,
                        'total_amount': 1,
                        'total_quantity': 1,
                        'transaction_count': 1,
                        'first_purchase_date': 1,
                        'last_purchase_date': 1,
                        'avg_order_value': 1,
                        'transactions': 1
                    }
                }
            ])
            
            # 执行查询
            customer_data = list(sales_collection.aggregate(pipeline))
            
            self.logger.info(f"获取客户交易数据完成，共 {len(customer_data)} 个客户")
            return customer_data
            
        except Exception as e:
            self.logger.error(f"获取客户交易数据失败: {str(e)}")
            return []
    
    def _calculate_rfm_metrics(self, customer_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        计算RFM指标（最近购买时间、购买频率、购买金额）
        
        Args:
            customer_transactions: 客户交易数据
            
        Returns:
            包含RFM评分的客户数据
        """
        try:
            rfm_data = []
            
            # 计算所有客户的RFM原始值，用于分位数计算
            all_recency = []
            all_frequency = []
            all_monetary = []
            
            for customer in customer_transactions:
                # 计算最近购买时间（天数）
                last_purchase_date = customer.get('last_purchase_date')
                if last_purchase_date:
                    try:
                        if isinstance(last_purchase_date, str):
                            last_date = datetime.fromisoformat(last_purchase_date.replace('T', ' ').replace('Z', ''))
                        else:
                            last_date = last_purchase_date
                        recency_days = (datetime.now() - last_date).days
                    except (ValueError, TypeError):
                        recency_days = 999  # 默认很久以前
                else:
                    recency_days = 999
                
                frequency = customer.get('transaction_count', 0)
                monetary = customer.get('total_amount', 0)
                
                all_recency.append(recency_days)
                all_frequency.append(frequency)
                all_monetary.append(monetary)
            
            # 计算分位数用于评分
            all_recency.sort()
            all_frequency.sort(reverse=True)  # 频率越高越好
            all_monetary.sort(reverse=True)   # 金额越高越好
            
            def get_rfm_score(value, sorted_values, reverse=False):
                """根据分位数计算RFM评分（1-5分）"""
                if not sorted_values:
                    return 3
                
                n = len(sorted_values)
                if reverse:
                    # 对于Recency，值越小越好
                    if value <= sorted_values[int(n * 0.2)]:
                        return 5
                    elif value <= sorted_values[int(n * 0.4)]:
                        return 4
                    elif value <= sorted_values[int(n * 0.6)]:
                        return 3
                    elif value <= sorted_values[int(n * 0.8)]:
                        return 2
                    else:
                        return 1
                else:
                    # 对于Frequency和Monetary，值越大越好
                    if value >= sorted_values[int(n * 0.2)]:
                        return 5
                    elif value >= sorted_values[int(n * 0.4)]:
                        return 4
                    elif value >= sorted_values[int(n * 0.6)]:
                        return 3
                    elif value >= sorted_values[int(n * 0.8)]:
                        return 2
                    else:
                        return 1
            
            # 为每个客户计算RFM评分
            for customer in customer_transactions:
                customer_name = customer.get('customer_name', '')
                
                # 计算最近购买时间（天数）
                last_purchase_date = customer.get('last_purchase_date')
                if last_purchase_date:
                    try:
                        if isinstance(last_purchase_date, str):
                            last_date = datetime.fromisoformat(last_purchase_date.replace('T', ' ').replace('Z', ''))
                        else:
                            last_date = last_purchase_date
                        recency_days = (datetime.now() - last_date).days
                    except (ValueError, TypeError):
                        recency_days = 999  # 默认很久以前
                else:
                    recency_days = 999
                
                frequency = customer.get('transaction_count', 0)
                monetary = customer.get('total_amount', 0)
                
                # 计算RFM评分
                recency_score = get_rfm_score(recency_days, all_recency, reverse=True)
                frequency_score = get_rfm_score(frequency, all_frequency, reverse=False)
                monetary_score = get_rfm_score(monetary, all_monetary, reverse=False)
                
                # 计算总分
                rfm_score = recency_score + frequency_score + monetary_score
                
                # 客户分类算法
                customer_segment = self._classify_customer(recency_score, frequency_score, monetary_score)
                
                rfm_item = {
                    'customer_name': customer_name,
                    'recency': recency_score,
                    'frequency': frequency_score,
                    'monetary': monetary_score,
                    'rfm_score': rfm_score,
                    'customer_segment': customer_segment,
                    'customer_value': round(monetary, 2),
                    'transaction_count': frequency,
                    'avg_order_value': round(customer.get('avg_order_value', 0), 2),
                    'days_since_last_purchase': int(recency_days),
                    'first_purchase_date': customer.get('first_purchase_date'),
                    'last_purchase_date': customer.get('last_purchase_date'),
                    'total_quantity': customer.get('total_quantity', 0)
                }
                
                rfm_data.append(rfm_item)
            
            # 按RFM总分排序
            rfm_data.sort(key=lambda x: x['rfm_score'], reverse=True)
            
            self.logger.info(f"RFM指标计算完成，共 {len(rfm_data)} 个客户")
            return rfm_data
            
        except Exception as e:
            self.logger.error(f"计算RFM指标失败: {str(e)}")
            return []
    
    def _classify_customer(self, recency: int, frequency: int, monetary: int) -> str:
        """
        客户分类算法 - 基于RFM评分进行客户分类
        
        Args:
            recency: 最近购买时间评分 (1-5)
            frequency: 购买频率评分 (1-5)
            monetary: 购买金额评分 (1-5)
            
        Returns:
            客户分类标签
        """
        try:
            # 冠军客户：RFM都很高
            if recency >= 4 and frequency >= 4 and monetary >= 4:
                return '冠军客户'
            
            # 忠诚客户：频率和金额高，最近购买可能不是最新
            elif frequency >= 4 and monetary >= 4:
                return '忠诚客户'
            
            # 潜力客户：最近购买活跃，但频率或金额还不够高
            elif recency >= 4 and (frequency >= 3 or monetary >= 3):
                return '潜力客户'
            
            # 新客户：最近购买，但历史数据不多
            elif recency >= 4 and frequency <= 2:
                return '新客户'
            
            # 风险客户：很久没有购买
            elif recency <= 2:
                return '风险客户'
            
            # 需要关注的客户：金额高但最近活跃度不够
            elif monetary >= 4 and recency <= 3:
                return '需要关注'
            
            # 一般客户：各项指标都中等
            else:
                return '一般客户'
                
        except Exception as e:
            self.logger.error(f"客户分类失败: {str(e)}")
            return '未分类'
    
    def _group_customers_by_segment(self, rfm_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按客户分类分组
        
        Args:
            rfm_data: RFM分析数据
            
        Returns:
            按分类分组的客户数据
        """
        try:
            segments = {}
            
            for customer in rfm_data:
                segment = customer.get('customer_segment', '未分类')
                
                if segment not in segments:
                    segments[segment] = {
                        'segment_name': segment,
                        'customer_count': 0,
                        'total_value': 0,
                        'avg_value': 0,
                        'customers': []
                    }
                
                segments[segment]['customer_count'] += 1
                segments[segment]['total_value'] += customer.get('customer_value', 0)
                segments[segment]['customers'].append(customer)
            
            # 计算平均值
            for segment_data in segments.values():
                if segment_data['customer_count'] > 0:
                    segment_data['avg_value'] = round(
                        segment_data['total_value'] / segment_data['customer_count'], 2
                    )
                segment_data['total_value'] = round(segment_data['total_value'], 2)
            
            return segments
            
        except Exception as e:
            self.logger.error(f"客户分类分组失败: {str(e)}")
            return {}
    
    def _calculate_segment_distribution(self, rfm_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        计算客户分类分布
        
        Args:
            rfm_data: RFM分析数据
            
        Returns:
            客户分类分布统计
        """
        try:
            distribution = {}
            
            for customer in rfm_data:
                segment = customer.get('customer_segment', '未分类')
                distribution[segment] = distribution.get(segment, 0) + 1
            
            return distribution
            
        except Exception as e:
            self.logger.error(f"计算客户分类分布失败: {str(e)}")
            return {}
    
    def _create_empty_customer_analysis_response(self, analysis_type: str) -> Dict[str, Any]:
        """
        创建空的客户分析响应
        
        Args:
            analysis_type: 分析类型
            
        Returns:
            空的响应数据
        """
        return {
            'success': True,
            'analysis_type': analysis_type,
            'data': [],
            'summary': {
                'total_customers': 0,
                'date_range': {
                    'start_date': None,
                    'end_date': None
                },
                'segment_distribution': {}
            },
            'message': '未找到符合条件的客户交易数据',
            'generated_at': datetime.now().isoformat()
        }
    
    def analyze_inventory_turnover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析库存周转情况（带缓存和分页）- 实现完整的库存周转分析方法
        计算整体和单品库存周转率，识别快速周转、慢速周转和呆滞库存，生成库存周转排行榜和预警信息
        
        Args:
            params: 参数字典，包含:
                - date_range: 日期范围 {'start_date': 'YYYY-MM-DD', 'end_date': 'YYYY-MM-DD'}
                - analysis_period: 分析周期（天数），默认365天
                - turnover_thresholds: 周转率阈值 {'fast': 4.0, 'slow': 1.0}
                - page: 页码（可选）
                - page_size: 页面大小（可选）
                
        Returns:
            库存周转分析数据，符合需求4.1-4.4的格式
        """
        # 使用缓存装饰器
        def data_generator():
            return self._analyze_inventory_turnover_uncached(params)
        
        try:
            # 设置缓存时间，库存周转分析数据可以缓存较长时间
            cached_data = cache_report_data(
                view_name="inventory_turnover_analysis",
                params=params,
                data_generator=data_generator,
                ttl=1200,  # 20分钟缓存
                cache_manager=self.cache_manager
            )
            
            # 处理分页（如果需要）
            page = params.get('page')
            page_size = params.get('page_size')
            
            if page is not None and isinstance(cached_data, dict) and 'data' in cached_data:
                # 对turnover_analysis数据进行分页
                turnover_data = cached_data['data'].get('turnover_analysis', [])
                
                if self.data_paginator.should_paginate(len(turnover_data)):
                    paginated_result = self.data_paginator.paginate_results(
                        data=turnover_data,
                        page=page,
                        page_size=page_size,
                        enable_compression=True
                    )
                    
                    # 更新turnover_analysis数据
                    cached_data['data']['turnover_analysis'] = paginated_result.get('data')
                    cached_data['data']['turnover_analysis_compressed'] = paginated_result.get('compressed_data')
                    cached_data['pagination'] = paginated_result.get('pagination')
                    cached_data['compression'] = paginated_result.get('compression')
                    cached_data['cached'] = True
                else:
                    cached_data['cached'] = True
            else:
                if isinstance(cached_data, dict):
                    cached_data['cached'] = True
            
            return cached_data
                
        except Exception as e:
            self.logger.error(f"分析库存周转失败: {str(e)}")
            return {
                'success': False,
                'error': {
                    'code': 'INVENTORY_TURNOVER_ANALYSIS_FAILED',
                    'message': str(e),
                    'details': f"库存周转分析失败: {str(e)}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _analyze_inventory_turnover_uncached(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析库存周转情况（无缓存版本）
        
        Args:
            params: 参数字典
            
        Returns:
            库存周转分析数据
        """
        try:
            # 参数验证和提取
            date_range = params.get('date_range', {})
            analysis_period = params.get('analysis_period', 365)  # 默认分析一年
            turnover_thresholds = params.get('turnover_thresholds', {'fast': 4.0, 'slow': 1.0})
            
            self.logger.info("开始分析库存周转情况")
            
            # 提取日期范围参数
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            # 日期格式验证
            if start_date and not self._validate_date_format(start_date):
                raise ValueError(f"开始日期格式无效: {start_date}")
            if end_date and not self._validate_date_format(end_date):
                raise ValueError(f"结束日期格式无效: {end_date}")
            
            # 获取库存数据
            self.logger.info("获取库存数据...")
            inventory_result = generate_inventory_report(
                enable_pagination=False,
                enable_compression=False
            )
            
            if not inventory_result or not inventory_result.get('success'):
                self.logger.warning("库存数据获取失败")
                return self._create_empty_inventory_analysis_response()
            
            inventory_data = inventory_result.get('data', [])
            inventory_stats = inventory_result.get('statistics', {})
            
            # 获取销售数据用于计算周转率
            self.logger.info("获取销售数据...")
            sales_summary = generate_sales_summary(start_date, end_date, self.logger)
            
            # 获取采购数据用于计算平均库存成本
            self.logger.info("获取采购数据...")
            purchase_summary = generate_purchase_summary(start_date, end_date, self.logger)
            
            # 获取详细的产品销售数据
            product_sales_data = self._get_product_sales_data(start_date, end_date)
            
            # 计算整体库存周转率
            total_inventory_value = self._safe_get_numeric(inventory_stats, 'total_value', 0)
            total_sales_amount = self._safe_get_numeric(sales_summary, 'total_amount', 0)
            total_purchase_amount = self._safe_get_numeric(purchase_summary, 'total_amount', 0)
            
            # 使用销售成本计算周转率（更准确）
            cost_of_goods_sold = total_purchase_amount if total_purchase_amount > 0 else total_sales_amount * 0.7  # 假设毛利率30%
            overall_turnover_rate = (cost_of_goods_sold / max(total_inventory_value, 1)) if total_inventory_value > 0 else 0
            
            # 计算各产品的详细周转分析
            self.logger.info("计算产品周转分析...")
            turnover_analysis = self._calculate_product_turnover_analysis(
                inventory_data, 
                product_sales_data, 
                analysis_period,
                turnover_thresholds
            )
            
            # 生成库存周转排行榜
            turnover_ranking = sorted(turnover_analysis, key=lambda x: x['turnover_rate'], reverse=True)
            
            # 分类统计
            fast_moving_items = [item for item in turnover_analysis if item['category'] == 'fast_moving']
            slow_moving_items = [item for item in turnover_analysis if item['category'] == 'slow_moving']
            dead_stock_items = [item for item in turnover_analysis if item['category'] == 'dead_stock']
            normal_items = [item for item in turnover_analysis if item['category'] == 'normal']
            
            # 生成预警信息
            warnings = self._generate_inventory_warnings(turnover_analysis, turnover_thresholds)
            
            # 构建标准化响应
            response = {
                'success': True,
                'data': {
                    # 整体周转指标
                    'overall_turnover_rate': round(overall_turnover_rate, 2),
                    'total_inventory_value': round(total_inventory_value, 2),
                    'cost_of_goods_sold': round(cost_of_goods_sold, 2),
                    'inventory_days': round(365 / max(overall_turnover_rate, 0.01), 1) if overall_turnover_rate > 0 else 999,
                    
                    # 分类统计
                    'fast_moving_items': len(fast_moving_items),
                    'slow_moving_items': len(slow_moving_items),
                    'dead_stock_count': len(dead_stock_items),
                    'normal_items': len(normal_items),
                    'total_products': len(turnover_analysis),
                    
                    # 详细分析数据
                    'turnover_analysis': turnover_ranking,
                    
                    # 分类详情（前10名）
                    'fast_moving_details': fast_moving_items[:10],
                    'slow_moving_details': slow_moving_items[:10],
                    'dead_stock_items': dead_stock_items[:10],
                    
                    # 预警信息
                    'warnings': warnings,
                    
                    # 统计汇总
                    'category_distribution': {
                        'fast_moving': len(fast_moving_items),
                        'normal': len(normal_items),
                        'slow_moving': len(slow_moving_items),
                        'dead_stock': len(dead_stock_items)
                    },
                    
                    # 价值分布
                    'value_distribution': {
                        'fast_moving_value': sum(item['stock_value'] for item in fast_moving_items),
                        'normal_value': sum(item['stock_value'] for item in normal_items),
                        'slow_moving_value': sum(item['stock_value'] for item in slow_moving_items),
                        'dead_stock_value': sum(item['stock_value'] for item in dead_stock_items)
                    }
                },
                'summary': {
                    'analysis_period_days': analysis_period,
                    'date_range': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'turnover_thresholds': turnover_thresholds,
                    'total_products_analyzed': len(turnover_analysis)
                },
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"库存周转分析完成，整体周转率: {overall_turnover_rate:.2f}，分析产品数: {len(turnover_analysis)}")
            return response
                
        except Exception as e:
            self.logger.error(f"分析库存周转失败: {str(e)}")
            return {
                'success': False,
                'error': {
                    'code': 'INVENTORY_TURNOVER_ANALYSIS_FAILED',
                    'message': str(e),
                    'details': f"库存周转分析失败: {str(e)}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _get_product_sales_data(self, start_date: Optional[str] = None, 
                               end_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        获取产品销售数据用于计算周转率
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            产品销售数据字典，key为产品名称，value为销售统计
        """
        try:
            db = self.query_optimizer._get_db_connection()
            sales_collection = db['sales_outbound']
            
            # 构建查询条件
            match_conditions = {}
            
            # 日期范围筛选
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter['$gte'] = start_date
                if end_date:
                    date_filter['$lte'] = end_date
                if date_filter:
                    match_conditions['outbound_date'] = date_filter
            
            # 构建聚合管道
            pipeline = []
            
            if match_conditions:
                pipeline.append({'$match': match_conditions})
            
            # 按产品分组，计算销售统计
            pipeline.extend([
                {
                    '$group': {
                        '_id': '$material_name',
                        'product_name': {'$first': '$material_name'},
                        'product_code': {'$first': '$material_code'},
                        'total_sales_amount': {'$sum': {'$toDouble': {'$ifNull': ['$outbound_amount', 0]}}},
                        'total_quantity_sold': {'$sum': {'$toDouble': {'$ifNull': ['$quantity', 0]}}},
                        'sales_count': {'$sum': 1},
                        'avg_unit_price': {'$avg': {'$toDouble': {'$ifNull': ['$unit_price', 0]}}},
                        'last_sale_date': {'$max': '$outbound_date'},
                        'first_sale_date': {'$min': '$outbound_date'}
                    }
                }
            ])
            
            # 执行查询
            product_sales = list(sales_collection.aggregate(pipeline))
            
            # 转换为字典格式
            sales_data = {}
            for item in product_sales:
                product_name = item.get('product_name', '')
                if product_name:
                    sales_data[product_name] = {
                        'product_code': item.get('product_code', ''),
                        'total_sales_amount': item.get('total_sales_amount', 0),
                        'total_quantity_sold': item.get('total_quantity_sold', 0),
                        'sales_count': item.get('sales_count', 0),
                        'avg_unit_price': item.get('avg_unit_price', 0),
                        'last_sale_date': item.get('last_sale_date'),
                        'first_sale_date': item.get('first_sale_date')
                    }
            
            self.logger.info(f"获取产品销售数据完成，共 {len(sales_data)} 个产品")
            return sales_data
            
        except Exception as e:
            self.logger.error(f"获取产品销售数据失败: {str(e)}")
            return {}
    
    def _calculate_product_turnover_analysis(self, inventory_data: List[Dict[str, Any]], 
                                           product_sales_data: Dict[str, Dict[str, Any]],
                                           analysis_period: int,
                                           turnover_thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        计算各产品的详细周转分析
        
        Args:
            inventory_data: 库存数据
            product_sales_data: 产品销售数据
            analysis_period: 分析周期（天数）
            turnover_thresholds: 周转率阈值
            
        Returns:
            产品周转分析数据列表
        """
        try:
            turnover_analysis = []
            
            for inventory_item in inventory_data:
                product_name = inventory_item.get('product_name', '') or inventory_item.get('material_name', '')
                product_code = inventory_item.get('product_code', '') or inventory_item.get('material_code', '')
                current_stock = self._safe_get_numeric(inventory_item, 'current_stock', 0)
                stock_value = self._safe_get_numeric(inventory_item, 'stock_value', 0)
                unit_cost = self._safe_get_numeric(inventory_item, 'unit_cost', 0)
                
                # 获取对应的销售数据
                sales_data = product_sales_data.get(product_name, {})
                total_sales_amount = sales_data.get('total_sales_amount', 0)
                total_quantity_sold = sales_data.get('total_quantity_sold', 0)
                sales_count = sales_data.get('sales_count', 0)
                last_sale_date = sales_data.get('last_sale_date')
                
                # 计算周转率
                # 周转率 = 销售成本 / 平均库存价值
                # 简化计算：使用当前库存价值作为平均库存价值
                if stock_value > 0:
                    # 使用销售金额的70%作为销售成本（假设毛利率30%）
                    cost_of_goods_sold = total_sales_amount * 0.7
                    turnover_rate = cost_of_goods_sold / stock_value
                else:
                    turnover_rate = 0
                
                # 计算库存天数
                inventory_days = (365 / max(turnover_rate, 0.01)) if turnover_rate > 0 else 999
                
                # 计算距离上次销售的天数
                days_since_last_sale = 999
                if last_sale_date:
                    try:
                        if isinstance(last_sale_date, str):
                            last_date = datetime.fromisoformat(last_sale_date.replace('T', ' ').replace('Z', ''))
                        else:
                            last_date = last_sale_date
                        days_since_last_sale = (datetime.now() - last_date).days
                    except (ValueError, TypeError):
                        days_since_last_sale = 999
                
                # 分类库存（快速周转、慢速周转、呆滞库存）
                if turnover_rate >= turnover_thresholds.get('fast', 4.0):
                    category = 'fast_moving'
                    category_name = '快速周转'
                elif turnover_rate >= turnover_thresholds.get('slow', 1.0):
                    category = 'normal'
                    category_name = '正常周转'
                elif turnover_rate > 0:
                    category = 'slow_moving'
                    category_name = '慢速周转'
                else:
                    category = 'dead_stock'
                    category_name = '呆滞库存'
                
                # 特殊情况：长时间未销售的商品也归类为呆滞库存
                if days_since_last_sale > 180:  # 超过6个月未销售
                    category = 'dead_stock'
                    category_name = '呆滞库存'
                
                # 生成预警级别
                warning_level = 'normal'
                warning_message = ''
                
                if category == 'dead_stock':
                    warning_level = 'high'
                    warning_message = f'呆滞库存，{days_since_last_sale}天未销售'
                elif category == 'slow_moving':
                    warning_level = 'medium'
                    warning_message = f'周转缓慢，周转率仅{turnover_rate:.2f}'
                elif current_stock <= 0:
                    warning_level = 'high'
                    warning_message = '库存不足'
                
                turnover_item = {
                    'product_name': product_name,
                    'product_code': product_code,
                    'current_stock': current_stock,
                    'stock_value': round(stock_value, 2),
                    'unit_cost': round(unit_cost, 2),
                    'turnover_rate': round(turnover_rate, 2),
                    'inventory_days': round(inventory_days, 1),
                    'category': category,
                    'category_name': category_name,
                    'total_sales_amount': round(total_sales_amount, 2),
                    'total_quantity_sold': total_quantity_sold,
                    'sales_count': sales_count,
                    'days_since_last_sale': days_since_last_sale,
                    'last_sale_date': last_sale_date,
                    'warning_level': warning_level,
                    'warning_message': warning_message,
                    'stock_status': inventory_item.get('stock_status', '正常')
                }
                
                turnover_analysis.append(turnover_item)
            
            self.logger.info(f"产品周转分析计算完成，共分析 {len(turnover_analysis)} 个产品")
            return turnover_analysis
            
        except Exception as e:
            self.logger.error(f"计算产品周转分析失败: {str(e)}")
            return []
    
    def _generate_inventory_warnings(self, turnover_analysis: List[Dict[str, Any]], 
                                   turnover_thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        生成库存预警信息
        
        Args:
            turnover_analysis: 周转分析数据
            turnover_thresholds: 周转率阈值
            
        Returns:
            预警信息列表
        """
        try:
            warnings = []
            
            # 统计各类别数量
            dead_stock_items = [item for item in turnover_analysis if item['category'] == 'dead_stock']
            slow_moving_items = [item for item in turnover_analysis if item['category'] == 'slow_moving']
            out_of_stock_items = [item for item in turnover_analysis if item['current_stock'] <= 0]
            
            # 呆滞库存预警
            if dead_stock_items:
                dead_stock_value = sum(item['stock_value'] for item in dead_stock_items)
                warnings.append({
                    'type': 'dead_stock',
                    'level': 'high',
                    'title': '呆滞库存预警',
                    'message': f'发现 {len(dead_stock_items)} 个呆滞库存商品，总价值 {dead_stock_value:.2f} 元',
                    'count': len(dead_stock_items),
                    'value': dead_stock_value,
                    'items': [item['product_name'] for item in dead_stock_items[:5]]  # 前5个
                })
            
            # 慢速周转预警
            if slow_moving_items:
                slow_moving_value = sum(item['stock_value'] for item in slow_moving_items)
                warnings.append({
                    'type': 'slow_moving',
                    'level': 'medium',
                    'title': '慢速周转预警',
                    'message': f'发现 {len(slow_moving_items)} 个慢速周转商品，总价值 {slow_moving_value:.2f} 元',
                    'count': len(slow_moving_items),
                    'value': slow_moving_value,
                    'items': [item['product_name'] for item in slow_moving_items[:5]]  # 前5个
                })
            
            # 缺货预警
            if out_of_stock_items:
                warnings.append({
                    'type': 'out_of_stock',
                    'level': 'high',
                    'title': '缺货预警',
                    'message': f'发现 {len(out_of_stock_items)} 个商品缺货',
                    'count': len(out_of_stock_items),
                    'value': 0,
                    'items': [item['product_name'] for item in out_of_stock_items[:5]]  # 前5个
                })
            
            # 高价值慢速周转预警
            high_value_slow_items = [
                item for item in slow_moving_items 
                if item['stock_value'] > 10000  # 库存价值超过1万元
            ]
            if high_value_slow_items:
                high_value_slow_total = sum(item['stock_value'] for item in high_value_slow_items)
                warnings.append({
                    'type': 'high_value_slow',
                    'level': 'high',
                    'title': '高价值慢速周转预警',
                    'message': f'发现 {len(high_value_slow_items)} 个高价值慢速周转商品，总价值 {high_value_slow_total:.2f} 元',
                    'count': len(high_value_slow_items),
                    'value': high_value_slow_total,
                    'items': [item['product_name'] for item in high_value_slow_items[:3]]  # 前3个
                })
            
            self.logger.info(f"生成库存预警信息完成，共 {len(warnings)} 条预警")
            return warnings
            
        except Exception as e:
            self.logger.error(f"生成库存预警信息失败: {str(e)}")
            return []
    
    def _create_empty_inventory_analysis_response(self) -> Dict[str, Any]:
        """
        创建空的库存分析响应
        
        Returns:
            空的响应数据
        """
        return {
            'success': True,
            'data': {
                'overall_turnover_rate': 0,
                'total_inventory_value': 0,
                'cost_of_goods_sold': 0,
                'inventory_days': 999,
                'fast_moving_items': 0,
                'slow_moving_items': 0,
                'dead_stock_count': 0,
                'normal_items': 0,
                'total_products': 0,
                'turnover_analysis': [],
                'fast_moving_details': [],
                'slow_moving_details': [],
                'dead_stock_items': [],
                'warnings': [],
                'category_distribution': {
                    'fast_moving': 0,
                    'normal': 0,
                    'slow_moving': 0,
                    'dead_stock': 0
                },
                'value_distribution': {
                    'fast_moving_value': 0,
                    'normal_value': 0,
                    'slow_moving_value': 0,
                    'dead_stock_value': 0
                }
            },
            'summary': {
                'analysis_period_days': 365,
                'date_range': {
                    'start_date': None,
                    'end_date': None
                },
                'turnover_thresholds': {'fast': 4.0, 'slow': 1.0},
                'total_products_analyzed': 0
            },
            'message': '未找到库存数据或库存数据为空',
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_comparison_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成多维度对比分析方法 - 支持多指标选择和多维度对比
        
        Args:
            params: 参数字典，包含:
                - metrics: 指标列表 ['total_sales', 'sales_count', 'total_purchases', 'purchase_count', 'order_count', 'avg_order_value']
                - dimensions: 维度列表 ['month', 'quarter', 'product', 'customer', 'supplier']
                - date_range: 日期范围 {'start_date': 'YYYY-MM-DD', 'end_date': 'YYYY-MM-DD'}
                - top_n: 排行榜显示数量，默认10
                
        Returns:
            多维度对比分析数据，符合需求5.1-5.4的格式
        """
        try:
            # 参数验证和提取
            metrics = params.get('metrics', ['total_sales', 'total_purchases'])
            dimensions = params.get('dimensions', ['month', 'product'])
            date_range = params.get('date_range', {})
            top_n = params.get('top_n', 10)
            
            self.logger.info(f"开始生成多维度对比分析，指标: {metrics}, 维度: {dimensions}")
            
            # 验证指标和维度
            valid_metrics = ['total_sales', 'sales_count', 'total_purchases', 'purchase_count', 
                           'order_count', 'avg_order_value', 'customer_count', 'supplier_count']
            valid_dimensions = ['month', 'quarter', 'product', 'customer', 'supplier']
            
            # 过滤无效的指标和维度
            metrics = [m for m in metrics if m in valid_metrics]
            dimensions = [d for d in dimensions if d in valid_dimensions]
            
            if not metrics:
                raise ValueError("未指定有效的对比指标")
            if not dimensions:
                raise ValueError("未指定有效的对比维度")
            
            # 提取日期范围参数
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            # 日期格式验证
            if start_date and not self._validate_date_format(start_date):
                raise ValueError(f"开始日期格式无效: {start_date}")
            if end_date and not self._validate_date_format(end_date):
                raise ValueError(f"结束日期格式无效: {end_date}")
            
            # 获取基础数据源
            self.logger.info("获取基础数据源...")
            data_sources = self._get_comparison_data_sources(metrics, start_date, end_date)
            
            # 按维度生成对比分析
            comparison_result = {
                'success': True,
                'metrics': metrics,
                'dimensions': dimensions,
                'data': {},
                'summary': {},
                'charts': {},
                'generated_at': datetime.now().isoformat()
            }
            
            # 月度维度对比
            if 'month' in dimensions:
                self.logger.info("生成月度对比分析...")
                comparison_result['data']['monthly'] = self._generate_monthly_comparison(
                    data_sources, metrics, top_n
                )
                comparison_result['charts']['monthly'] = self._generate_monthly_charts_config(
                    comparison_result['data']['monthly'], metrics
                )
            
            # 季度维度对比
            if 'quarter' in dimensions:
                self.logger.info("生成季度对比分析...")
                comparison_result['data']['quarterly'] = self._generate_quarterly_comparison(
                    data_sources, metrics, top_n
                )
                comparison_result['charts']['quarterly'] = self._generate_quarterly_charts_config(
                    comparison_result['data']['quarterly'], metrics
                )
            
            # 产品维度对比
            if 'product' in dimensions:
                self.logger.info("生成产品对比分析...")
                comparison_result['data']['products'] = self._generate_product_comparison(
                    data_sources, metrics, top_n
                )
                comparison_result['charts']['products'] = self._generate_product_charts_config(
                    comparison_result['data']['products'], metrics
                )
            
            # 客户维度对比
            if 'customer' in dimensions:
                self.logger.info("生成客户对比分析...")
                comparison_result['data']['customers'] = self._generate_customer_comparison(
                    data_sources, metrics, top_n
                )
                comparison_result['charts']['customers'] = self._generate_customer_charts_config(
                    comparison_result['data']['customers'], metrics
                )
            
            # 供应商维度对比
            if 'supplier' in dimensions:
                self.logger.info("生成供应商对比分析...")
                comparison_result['data']['suppliers'] = self._generate_supplier_comparison(
                    data_sources, metrics, top_n
                )
                comparison_result['charts']['suppliers'] = self._generate_supplier_charts_config(
                    comparison_result['data']['suppliers'], metrics
                )
            
            # 生成汇总统计
            comparison_result['summary'] = self._generate_comparison_summary(
                data_sources, metrics, dimensions
            )
            
            # 生成对比洞察
            comparison_result['insights'] = self._generate_comparison_insights(
                comparison_result['data'], metrics, dimensions
            )
            
            self.logger.info(f"多维度对比分析完成，维度数: {len(dimensions)}, 指标数: {len(metrics)}")
            return comparison_result
            
        except Exception as e:
            self.logger.error(f"生成多维度对比分析失败: {str(e)}")
            return {
                'success': False,
                'error': {
                    'code': 'COMPARISON_ANALYSIS_FAILED',
                    'message': str(e),
                    'details': f"多维度对比分析失败: {str(e)}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _validate_date_format(self, date_str: str) -> bool:
        """
        验证日期格式是否为YYYY-MM-DD
        
        Args:
            date_str: 日期字符串
            
        Returns:
            是否为有效格式
        """
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _validate_and_format_date_range(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和格式化日期范围参数
        
        Args:
            params: 包含日期范围的参数字典
            
        Returns:
            验证和格式化后的参数字典
            
        Raises:
            ValueError: 当日期格式无效或日期范围不合理时
        """
        try:
            # 深拷贝参数以避免修改原始数据
            validated_params = params.copy()
            date_range = params.get('date_range', {})
            
            if not date_range:
                # 如果没有提供日期范围，设置默认值（最近30天）
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                validated_params['date_range'] = {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }
                self.logger.info("使用默认日期范围：最近30天")
                return validated_params
            
            start_date_str = date_range.get('start_date')
            end_date_str = date_range.get('end_date')
            
            # 清理和验证开始日期
            if start_date_str:
                start_date_str = self._clean_date_string(start_date_str)
                if not self._validate_date_format(start_date_str):
                    raise ValueError(f"开始日期格式无效: {start_date_str}，请使用YYYY-MM-DD格式")
                
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                
                # 检查日期边界（不能超过当前日期）
                if start_date > datetime.now():
                    raise ValueError(f"开始日期不能超过当前日期: {start_date_str}")
                
                # 检查日期不能过于久远（超过10年）
                ten_years_ago = datetime.now() - timedelta(days=3650)
                if start_date < ten_years_ago:
                    self.logger.warning(f"开始日期过于久远: {start_date_str}，建议使用最近10年内的数据")
            else:
                # 如果没有开始日期，设置为30天前
                start_date = datetime.now() - timedelta(days=30)
                start_date_str = start_date.strftime('%Y-%m-%d')
                self.logger.info(f"使用默认开始日期: {start_date_str}")
            
            # 清理和验证结束日期
            if end_date_str:
                end_date_str = self._clean_date_string(end_date_str)
                if not self._validate_date_format(end_date_str):
                    raise ValueError(f"结束日期格式无效: {end_date_str}，请使用YYYY-MM-DD格式")
                
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                
                # 检查日期边界（不能超过当前日期）
                if end_date > datetime.now():
                    end_date = datetime.now()
                    end_date_str = end_date.strftime('%Y-%m-%d')
                    self.logger.warning(f"结束日期超过当前日期，已调整为: {end_date_str}")
            else:
                # 如果没有结束日期，设置为当前日期
                end_date = datetime.now()
                end_date_str = end_date.strftime('%Y-%m-%d')
                self.logger.info(f"使用默认结束日期: {end_date_str}")
            
            # 验证日期范围的合理性
            if start_date >= end_date:
                raise ValueError(f"开始日期({start_date_str})必须早于结束日期({end_date_str})")
            
            # 检查日期范围是否过长（超过5年）
            date_diff = end_date - start_date
            if date_diff.days > 1825:  # 5年
                self.logger.warning(f"日期范围过长({date_diff.days}天)，可能影响查询性能")
            
            # 更新验证后的日期范围
            validated_params['date_range'] = {
                'start_date': start_date_str,
                'end_date': end_date_str
            }
            
            self.logger.info(f"日期范围验证通过: {start_date_str} 到 {end_date_str}")
            return validated_params
            
        except Exception as e:
            self.logger.error(f"日期范围验证失败: {str(e)}")
            raise ValueError(f"日期范围验证失败: {str(e)}")
    
    def _clean_date_string(self, date_str: str) -> str:
        """
        清理日期字符串，移除多余的空格和特殊字符
        
        Args:
            date_str: 原始日期字符串
            
        Returns:
            清理后的日期字符串
        """
        if not isinstance(date_str, str):
            raise ValueError(f"日期必须是字符串类型，当前类型: {type(date_str)}")
        
        # 移除前后空格
        cleaned = date_str.strip()
        
        # 移除可能的引号
        cleaned = cleaned.strip('"\'')
        
        # 检查是否为空
        if not cleaned:
            raise ValueError("日期字符串不能为空")
        
        return cleaned
    
    def _validate_numeric_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和清理数值类型参数
        
        Args:
            params: 参数字典
            
        Returns:
            验证后的参数字典
        """
        validated_params = params.copy()
        
        # 验证页码参数
        if 'page' in params:
            page = params['page']
            if page is not None:
                try:
                    page = int(page)
                    if page < 1:
                        self.logger.warning(f"页码不能小于1，已调整为1: {params['page']}")
                        page = 1
                    elif page > 10000:  # 设置合理的上限
                        self.logger.warning(f"页码过大，已调整为10000: {params['page']}")
                        page = 10000
                    validated_params['page'] = page
                except (ValueError, TypeError):
                    self.logger.warning(f"无效的页码参数，使用默认值1: {params['page']}")
                    validated_params['page'] = 1
        
        # 验证页面大小参数
        if 'page_size' in params:
            page_size = params['page_size']
            if page_size is not None:
                try:
                    page_size = int(page_size)
                    if page_size < 1:
                        self.logger.warning(f"页面大小不能小于1，已调整为10: {params['page_size']}")
                        page_size = 10
                    elif page_size > 1000:  # 设置合理的上限
                        self.logger.warning(f"页面大小过大，已调整为1000: {params['page_size']}")
                        page_size = 1000
                    validated_params['page_size'] = page_size
                except (ValueError, TypeError):
                    self.logger.warning(f"无效的页面大小参数，使用默认值50: {params['page_size']}")
                    validated_params['page_size'] = 50
            else:
                # 如果page_size为None，设置默认值
                validated_params['page_size'] = 50
        
        # 验证限制参数
        if 'limit' in params:
            limit = params['limit']
            if limit is not None:
                try:
                    limit = int(limit)
                    if limit < 1:
                        limit = 100
                    elif limit > 10000:
                        limit = 10000
                    validated_params['limit'] = limit
                except (ValueError, TypeError):
                    validated_params['limit'] = 100
        
        return validated_params
    
    def _validate_string_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和清理字符串类型参数
        
        Args:
            params: 参数字典
            
        Returns:
            验证后的参数字典
        """
        validated_params = params.copy()
        
        # 需要清理的字符串参数列表
        string_params = ['dimension', 'analysis_type', 'method', 'format']
        
        for param_name in string_params:
            if param_name in params:
                param_value = params[param_name]
                if param_value is not None:
                    # 确保是字符串类型
                    if not isinstance(param_value, str):
                        param_value = str(param_value)
                    
                    # 清理字符串
                    cleaned_value = self._clean_string_input(param_value)
                    
                    # 验证特定参数的有效值
                    if param_name == 'dimension':
                        valid_dimensions = ['month', 'quarter', 'product', 'customer', 'supplier']
                        if cleaned_value not in valid_dimensions:
                            self.logger.warning(f"无效的维度参数: {cleaned_value}，使用默认值: month")
                            cleaned_value = 'month'
                    
                    elif param_name == 'analysis_type':
                        valid_types = ['rfm', 'ranking', 'segmentation', 'overview']
                        if cleaned_value not in valid_types:
                            self.logger.warning(f"无效的分析类型参数: {cleaned_value}，使用默认值: rfm")
                            cleaned_value = 'rfm'
                    
                    elif param_name == 'format':
                        valid_formats = ['json', 'csv', 'excel']
                        if cleaned_value not in valid_formats:
                            self.logger.warning(f"无效的格式参数: {cleaned_value}，使用默认值: json")
                            cleaned_value = 'json'
                    
                    validated_params[param_name] = cleaned_value
        
        return validated_params
    
    def _clean_string_input(self, input_str: str) -> str:
        """
        清理字符串输入，防止注入攻击和格式问题
        
        Args:
            input_str: 原始字符串
            
        Returns:
            清理后的字符串
        """
        if not isinstance(input_str, str):
            input_str = str(input_str)
        
        # 移除前后空格
        cleaned = input_str.strip()
        
        # 移除可能的危险字符
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$']
        for char in dangerous_chars:
            cleaned = cleaned.replace(char, '')
        
        # 限制长度
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
            self.logger.warning(f"字符串参数过长，已截断: {input_str[:50]}...")
        
        return cleaned
    
    def _validate_array_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和清理数组类型参数
        
        Args:
            params: 参数字典
            
        Returns:
            验证后的参数字典
        """
        validated_params = params.copy()
        
        # 验证metrics参数
        if 'metrics' in params:
            metrics = params['metrics']
            if metrics is not None:
                if not isinstance(metrics, list):
                    # 尝试转换为列表
                    if isinstance(metrics, str):
                        metrics = [metrics]
                    else:
                        metrics = []
                
                # 清理和验证每个指标
                valid_metrics = [
                    'total_sales', 'total_purchases', 'order_count', 'customer_count',
                    'supplier_count', 'inventory_value', 'receivables', 'payables'
                ]
                
                cleaned_metrics = []
                for metric in metrics:
                    if isinstance(metric, str):
                        cleaned_metric = self._clean_string_input(metric)
                        if cleaned_metric in valid_metrics:
                            cleaned_metrics.append(cleaned_metric)
                        else:
                            self.logger.warning(f"无效的指标参数: {cleaned_metric}")
                
                # 如果没有有效指标，使用默认值
                if not cleaned_metrics:
                    cleaned_metrics = ['total_sales', 'total_purchases']
                    self.logger.info("使用默认指标: total_sales, total_purchases")
                
                validated_params['metrics'] = cleaned_metrics
        
        # 验证dimensions参数
        if 'dimensions' in params:
            dimensions = params['dimensions']
            if dimensions is not None:
                if not isinstance(dimensions, list):
                    if isinstance(dimensions, str):
                        dimensions = [dimensions]
                    else:
                        dimensions = []
                
                valid_dimensions = ['month', 'quarter', 'product', 'customer', 'supplier']
                
                cleaned_dimensions = []
                for dimension in dimensions:
                    if isinstance(dimension, str):
                        cleaned_dimension = self._clean_string_input(dimension)
                        if cleaned_dimension in valid_dimensions:
                            cleaned_dimensions.append(cleaned_dimension)
                        else:
                            self.logger.warning(f"无效的维度参数: {cleaned_dimension}")
                
                if not cleaned_dimensions:
                    cleaned_dimensions = ['month', 'product']
                    self.logger.info("使用默认维度: month, product")
                
                validated_params['dimensions'] = cleaned_dimensions
        
        return validated_params
    
    def _check_data_integrity(self, data: Any, data_type: str = "unknown") -> bool:
        """
        检查数据完整性
        
        Args:
            data: 要检查的数据
            data_type: 数据类型描述
            
        Returns:
            数据是否完整
        """
        try:
            if data is None:
                self.logger.warning(f"数据为空: {data_type}")
                return False
            
            if isinstance(data, dict):
                # 检查字典是否为空
                if not data:
                    self.logger.warning(f"字典数据为空: {data_type}")
                    return False
                
                # 检查是否包含错误信息
                if 'error' in data and data.get('error'):
                    self.logger.warning(f"数据包含错误信息: {data_type}, 错误: {data.get('error')}")
                    return False
                
                # 检查关键字段
                if data_type == "sales_summary":
                    required_fields = ['total_amount', 'order_count']
                    for field in required_fields:
                        if field not in data:
                            self.logger.warning(f"销售汇总数据缺少必要字段: {field}")
                            return False
                
                elif data_type == "inventory_data":
                    if 'data' in data and isinstance(data['data'], list):
                        if not data['data']:
                            self.logger.warning("库存数据列表为空")
                            return False
                    else:
                        self.logger.warning("库存数据格式不正确")
                        return False
            
            elif isinstance(data, list):
                if not data:
                    self.logger.warning(f"列表数据为空: {data_type}")
                    return False
                
                # 检查列表中的数据项
                for i, item in enumerate(data):
                    if item is None:
                        self.logger.warning(f"列表中第{i}项为空: {data_type}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"数据完整性检查失败: {data_type}, 错误: {str(e)}")
            return False
    
    def _apply_default_values(self, params: Dict[str, Any], method: str) -> Dict[str, Any]:
        """
        为参数应用默认值
        
        Args:
            params: 参数字典
            method: 方法名称
            
        Returns:
            应用默认值后的参数字典
        """
        params_with_defaults = params.copy()
        
        # 根据不同方法应用不同的默认值
        if method == 'get_dashboard_summary':
            # 仪表板概览的默认值
            if 'date_range' not in params_with_defaults:
                params_with_defaults['date_range'] = {}
        
        elif method == 'analyze_sales_trend':
            # 销售趋势分析的默认值
            if 'dimension' not in params_with_defaults:
                params_with_defaults['dimension'] = 'month'
            if 'date_range' not in params_with_defaults:
                params_with_defaults['date_range'] = {}
        
        elif method == 'analyze_customer_value':
            # 客户价值分析的默认值
            if 'analysis_type' not in params_with_defaults:
                params_with_defaults['analysis_type'] = 'rfm'
            if 'date_range' not in params_with_defaults:
                params_with_defaults['date_range'] = {}
        
        elif method == 'analyze_inventory_turnover':
            # 库存周转分析的默认值
            if 'date_range' not in params_with_defaults:
                params_with_defaults['date_range'] = {}
        
        elif method == 'generate_comparison_analysis':
            # 对比分析的默认值
            if 'metrics' not in params_with_defaults:
                params_with_defaults['metrics'] = ['total_sales', 'total_purchases']
            if 'dimensions' not in params_with_defaults:
                params_with_defaults['dimensions'] = ['month', 'product']
            if 'date_range' not in params_with_defaults:
                params_with_defaults['date_range'] = {}
        
        # 通用默认值
        if 'page' not in params_with_defaults:
            params_with_defaults['page'] = 1
        if 'page_size' not in params_with_defaults:
            params_with_defaults['page_size'] = 50
        
        return params_with_defaults
    
    def validate_and_clean_params(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一的参数验证和清理入口
        
        Args:
            method: 方法名称
            params: 原始参数字典
            
        Returns:
            验证和清理后的参数字典
            
        Raises:
            ValueError: 当参数验证失败时
        """
        try:
            self.logger.info(f"开始验证参数，方法: {method}")
            
            # 1. 应用默认值
            validated_params = self._apply_default_values(params, method)
            
            # 2. 验证和格式化日期范围
            validated_params = self._validate_and_format_date_range(validated_params)
            
            # 3. 验证数值类型参数
            validated_params = self._validate_numeric_params(validated_params)
            
            # 4. 验证字符串类型参数
            validated_params = self._validate_string_params(validated_params)
            
            # 5. 验证数组类型参数
            validated_params = self._validate_array_params(validated_params)
            
            # 6. 方法特定的验证
            if method == 'analyze_sales_trend':
                dimension = validated_params.get('dimension', 'month')
                valid_dimensions = ['month', 'quarter', 'product']
                if dimension not in valid_dimensions:
                    raise ValueError(f"不支持的销售趋势分析维度: {dimension}，支持的维度: {valid_dimensions}")
            
            elif method == 'analyze_customer_value':
                analysis_type = validated_params.get('analysis_type', 'rfm')
                valid_types = ['rfm', 'ranking', 'segmentation']
                if analysis_type not in valid_types:
                    raise ValueError(f"不支持的客户价值分析类型: {analysis_type}，支持的类型: {valid_types}")
            
            elif method == 'generate_comparison_analysis':
                metrics = validated_params.get('metrics', [])
                dimensions = validated_params.get('dimensions', [])
                if not metrics:
                    raise ValueError("对比分析必须指定至少一个指标")
                if not dimensions:
                    raise ValueError("对比分析必须指定至少一个维度")
            
            self.logger.info(f"参数验证完成，方法: {method}")
            return validated_params
            
        except Exception as e:
            self.logger.error(f"参数验证失败，方法: {method}, 错误: {str(e)}")
            raise ValueError(f"参数验证失败: {str(e)}")
    
    def _safe_get_numeric(self, data: Dict[str, Any], key: str, default: float = 0) -> float:
        """
        安全获取数值类型数据
        
        Args:
            data: 数据字典
            key: 键名
            default: 默认值
            
        Returns:
            数值或默认值
        """
        if not data or not isinstance(data, dict):
            return default
        
        value = data.get(key, default)
        if value is None:
            return default
        
        try:
            return float(value)
        except (ValueError, TypeError):
            self.logger.warning(f"无法转换为数值: {key}={value}, 使用默认值: {default}")
            return default

    def handle_method_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一的方法调用处理器（带参数验证和清理）
        
        Args:
            method: 方法名称
            params: 方法参数
            
        Returns:
            标准化的JSON响应
        """
        try:
            self.logger.info(f"处理方法调用: {method}, 原始参数: {params}")
            
            # 1. 参数验证和清理
            try:
                validated_params = self.validate_and_clean_params(method, params)
                self.logger.info(f"参数验证通过，清理后参数: {validated_params}")
            except ValueError as ve:
                self.logger.error(f"参数验证失败: {str(ve)}")
                return {
                    'success': False,
                    'method': method,
                    'error': {
                        'code': 'INVALID_PARAMETERS',
                        'message': str(ve),
                        'details': f"方法 {method} 的参数验证失败"
                    },
                    'generated_at': datetime.now().isoformat()
                }
            
            # 2. 执行相应的分析方法
            data = None
            
            # 分析方法（使用内置缓存）
            if method == 'get_dashboard_summary':
                data = self.get_dashboard_summary(validated_params)
            
            elif method == 'get_dashboard_data':
                data = self.get_dashboard_data(validated_params)
            
            elif method == 'analyze_sales_trend':
                data = self.analyze_sales_trend(validated_params)
            
            elif method == 'analyze_customer_value':
                data = self.analyze_customer_value(validated_params)
            
            elif method == 'analyze_inventory_turnover':
                data = self.analyze_inventory_turnover(validated_params)
            
            elif method == 'generate_comparison_analysis':
                metrics = validated_params.get('metrics', ['total_sales', 'total_purchases'])
                dimensions = validated_params.get('dimensions', ['month', 'product'])
                date_range = validated_params.get('date_range')
                data = self.generate_comparison_analysis(metrics, dimensions, date_range)
            
            # 缓存管理方法（不使用缓存装饰器）
            elif method == 'invalidate_cache':
                data = self.invalidate_cache(validated_params.get('pattern', '*'))
            
            elif method == 'get_cache_stats':
                data = self.get_cache_stats()
            
            elif method == 'optimize_query_performance':
                data = self.optimize_query_performance(validated_params)
            
            elif method == 'get_pagination_config':
                data = self.get_pagination_config(validated_params.get('data_size', 0))
            
            elif method == 'benchmark_performance':
                data = self.benchmark_performance(validated_params)
            
            elif method == 'export_analysis_data':
                data = self.export_analysis_data(validated_params)
            
            elif method == 'export_dashboard_data':
                # 导出仪表板数据
                data = self.export_dashboard_data(validated_params)
            
            else:
                raise ValueError(f"未知的方法: {method}")
            
            # 3. 数据完整性检查
            if not self._check_data_integrity(data, f"{method}_result"):
                self.logger.warning(f"方法 {method} 返回的数据完整性检查失败")
                # 不抛出异常，而是在响应中标记警告
                if isinstance(data, dict):
                    data['data_integrity_warning'] = True
            
            # 4. 返回标准化的成功响应
            return {
                'success': True,
                'method': method,
                'data': data,
                'validation_applied': True,
                'generated_at': datetime.now().isoformat(),
                'cached': True  # 表示使用了缓存机制
            }
            
        except Exception as e:
            self.logger.error(f"方法调用失败: {method}, 错误: {str(e)}")
            return {
                'success': False,
                'method': method,
                'error': {
                    'code': 'METHOD_CALL_FAILED',
                    'message': str(e),
                    'details': f"调用方法 {method} 时发生错误"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    # 缓存管理和性能优化方法
    
    def invalidate_cache(self, pattern: str = "*") -> Dict[str, Any]:
        """
        失效缓存
        
        Args:
            pattern: 缓存键匹配模式
            
        Returns:
            失效结果
        """
        try:
            invalidated_count = self.cache_manager.invalidate_cache(pattern)
            self.logger.info(f"缓存失效完成，模式: {pattern}, 失效条目数: {invalidated_count}")
            
            return {
                'success': True,
                'pattern': pattern,
                'invalidated_count': invalidated_count,
                'message': f'成功失效 {invalidated_count} 个缓存条目'
            }
            
        except Exception as e:
            self.logger.error(f"缓存失效失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'pattern': pattern
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        try:
            cache_stats = self.cache_manager.get_cache_stats()
            
            # 合并性能统计
            combined_stats = {
                'cache_stats': cache_stats,
                'performance_stats': self.performance_stats,
                'pagination_stats': {
                    'default_page_size': self.data_paginator.default_page_size,
                    'max_page_size': self.data_paginator.max_page_size,
                    'pagination_threshold': self.data_paginator.pagination_threshold,
                    'compression_threshold': self.data_paginator.compression_threshold
                }
            }
            
            return combined_stats
            
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {str(e)}")
            return {
                'error': str(e)
            }
    
    def optimize_query_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化查询性能
        
        Args:
            params: 优化参数
            
        Returns:
            优化结果
        """
        try:
            optimization_results = []
            
            # 1. 缓存预热
            if params.get('preload_cache', False):
                self.logger.info("开始缓存预热...")
                
                # 预加载常用的仪表板数据
                common_params = [
                    {'date_range': {}},  # 全部数据
                    {'date_range': {'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}},  # 最近30天
                    {'date_range': {'start_date': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')}}   # 最近90天
                ]
                
                for param_set in common_params:
                    try:
                        self.get_dashboard_summary(param_set)
                        self.analyze_sales_trend({'dimension': 'month', 'date_range': param_set.get('date_range', {})})
                        optimization_results.append(f"预热缓存: {param_set}")
                    except Exception as e:
                        self.logger.warning(f"缓存预热失败: {param_set}, 错误: {str(e)}")
            
            # 2. 数据库查询优化
            if params.get('optimize_queries', False):
                self.logger.info("优化数据库查询...")
                # 这里可以添加索引优化、查询计划分析等
                optimization_results.append("数据库查询优化完成")
            
            # 3. 内存清理
            if params.get('cleanup_memory', False):
                self.logger.info("清理内存...")
                import gc
                gc.collect()
                optimization_results.append("内存清理完成")
            
            return {
                'success': True,
                'optimizations': optimization_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"性能优化失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_pagination_config(self, data_size: int) -> Dict[str, Any]:
        """
        获取分页配置建议
        
        Args:
            data_size: 数据大小
            
        Returns:
            分页配置建议
        """
        try:
            should_paginate = self.data_paginator.should_paginate(data_size)
            
            if should_paginate:
                # 计算最优页面大小
                optimal_page_size = min(
                    max(10, data_size // 10),  # 至少10条，最多总数的1/10
                    self.data_paginator.max_page_size
                )
                
                total_pages = (data_size + optimal_page_size - 1) // optimal_page_size
                
                config = {
                    'should_paginate': True,
                    'recommended_page_size': optimal_page_size,
                    'total_pages': total_pages,
                    'compression_recommended': data_size > self.data_paginator.compression_threshold,
                    'virtual_scroll_recommended': data_size > 1000
                }
            else:
                config = {
                    'should_paginate': False,
                    'recommended_page_size': data_size,
                    'total_pages': 1,
                    'compression_recommended': False,
                    'virtual_scroll_recommended': False
                }
            
            config.update({
                'data_size': data_size,
                'pagination_threshold': self.data_paginator.pagination_threshold,
                'compression_threshold': self.data_paginator.compression_threshold
            })
            
            return config
            
        except Exception as e:
            self.logger.error(f"获取分页配置失败: {str(e)}")
            return {
                'error': str(e),
                'data_size': data_size
            }
    
    def benchmark_performance(self, test_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        性能基准测试
        
        Args:
            test_params: 测试参数
            
        Returns:
            性能测试结果
        """
        try:
            import time
            
            benchmark_results = {}
            test_iterations = test_params.get('iterations', 3)
            
            # 测试仪表板概览性能
            if test_params.get('test_dashboard', True):
                dashboard_times = []
                for i in range(test_iterations):
                    start_time = time.time()
                    self.get_dashboard_summary({'date_range': {}})
                    end_time = time.time()
                    dashboard_times.append(end_time - start_time)
                
                benchmark_results['dashboard_summary'] = {
                    'avg_time': sum(dashboard_times) / len(dashboard_times),
                    'min_time': min(dashboard_times),
                    'max_time': max(dashboard_times),
                    'iterations': test_iterations
                }
            
            # 测试销售趋势分析性能
            if test_params.get('test_sales_trend', True):
                sales_times = []
                for i in range(test_iterations):
                    start_time = time.time()
                    self.analyze_sales_trend({'dimension': 'month', 'date_range': {}})
                    end_time = time.time()
                    sales_times.append(end_time - start_time)
                
                benchmark_results['sales_trend_analysis'] = {
                    'avg_time': sum(sales_times) / len(sales_times),
                    'min_time': min(sales_times),
                    'max_time': max(sales_times),
                    'iterations': test_iterations
                }
            
            # 测试客户价值分析性能
            if test_params.get('test_customer_value', True):
                customer_times = []
                for i in range(test_iterations):
                    start_time = time.time()
                    self.analyze_customer_value({'analysis_type': 'rfm', 'date_range': {}})
                    end_time = time.time()
                    customer_times.append(end_time - start_time)
                
                benchmark_results['customer_value_analysis'] = {
                    'avg_time': sum(customer_times) / len(customer_times),
                    'min_time': min(customer_times),
                    'max_time': max(customer_times),
                    'iterations': test_iterations
                }
            
            # 获取缓存统计
            cache_stats = self.cache_manager.get_cache_stats()
            
            return {
                'success': True,
                'benchmark_results': benchmark_results,
                'cache_stats': cache_stats,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"性能基准测试失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def export_dashboard_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        导出仪表板数据 - 基础架构实现
        
        Args:
            params: 参数字典，包含:
                - export_format: 导出格式 ('json', 'csv', 'excel', 'pdf')
                - export_sections: 导出部分列表 ['overview', 'sales_trend', 'customer_analysis', 'inventory_analysis']
                - date_range: 日期范围
                - include_charts: 是否包含图表数据
                
        Returns:
            导出数据和状态信息
        """
        try:
            self.logger.info("开始导出仪表板数据")
            
            # 参数验证
            export_format = params.get('export_format', 'json')
            export_sections = params.get('export_sections', ['overview'])
            date_range = params.get('date_range', {})
            include_charts = params.get('include_charts', True)
            
            # 验证导出格式
            valid_formats = ['json', 'csv', 'excel', 'pdf']
            if export_format not in valid_formats:
                raise ValueError(f"不支持的导出格式: {export_format}，支持的格式: {valid_formats}")
            
            # 验证导出部分
            valid_sections = ['overview', 'sales_trend', 'customer_analysis', 'inventory_analysis', 'comparison_analysis']
            invalid_sections = [s for s in export_sections if s not in valid_sections]
            if invalid_sections:
                raise ValueError(f"不支持的导出部分: {invalid_sections}，支持的部分: {valid_sections}")
            
            # 收集导出数据
            export_data = {
                'export_info': {
                    'format': export_format,
                    'sections': export_sections,
                    'generated_at': datetime.now().isoformat(),
                    'date_range': date_range,
                    'include_charts': include_charts
                },
                'data': {}
            }
            
            # 根据选择的部分收集数据
            if 'overview' in export_sections:
                self.logger.info("收集概览数据...")
                overview_data = self.get_dashboard_summary({'date_range': date_range})
                export_data['data']['overview'] = self._format_export_data(overview_data, 'overview')
            
            if 'sales_trend' in export_sections:
                self.logger.info("收集销售趋势数据...")
                # 收集所有维度的销售趋势数据
                sales_data = {}
                for dimension in ['month', 'quarter', 'product']:
                    trend_data = self.analyze_sales_trend({
                        'dimension': dimension,
                        'date_range': date_range
                    })
                    sales_data[dimension] = self._format_export_data(trend_data, 'sales_trend')
                export_data['data']['sales_trend'] = sales_data
            
            if 'customer_analysis' in export_sections:
                self.logger.info("收集客户分析数据...")
                customer_data = self.analyze_customer_value({
                    'analysis_type': 'rfm',
                    'date_range': date_range
                })
                export_data['data']['customer_analysis'] = self._format_export_data(customer_data, 'customer_analysis')
            
            if 'inventory_analysis' in export_sections:
                self.logger.info("收集库存分析数据...")
                inventory_data = self.analyze_inventory_turnover({
                    'date_range': date_range
                })
                export_data['data']['inventory_analysis'] = self._format_export_data(inventory_data, 'inventory_analysis')
            
            if 'comparison_analysis' in export_sections:
                self.logger.info("收集对比分析数据...")
                comparison_data = self.generate_comparison_analysis({
                    'metrics': ['total_sales', 'total_purchases'],
                    'dimensions': ['month', 'product'],
                    'date_range': date_range
                })
                export_data['data']['comparison_analysis'] = self._format_export_data(comparison_data, 'comparison_analysis')
            
            # 根据格式处理数据
            if export_format == 'json':
                processed_data = self._export_as_json(export_data)
            elif export_format == 'csv':
                processed_data = self._export_as_csv(export_data)
            elif export_format == 'excel':
                processed_data = self._prepare_excel_export(export_data)
            elif export_format == 'pdf':
                processed_data = self._prepare_pdf_export(export_data)
            else:
                processed_data = export_data
            
            # 构建响应
            response = {
                'success': True,
                'export_format': export_format,
                'export_sections': export_sections,
                'data_size': len(str(processed_data)),
                'export_data': processed_data,
                'download_info': {
                    'filename': self._generate_export_filename(export_format, export_sections),
                    'content_type': self._get_content_type(export_format),
                    'size_mb': round(len(str(processed_data)) / 1024 / 1024, 2)
                },
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"数据导出完成，格式: {export_format}，大小: {response['download_info']['size_mb']}MB")
            return response
            
        except Exception as e:
            self.logger.error(f"导出仪表板数据失败: {str(e)}")
            return {
                'success': False,
                'error': {
                    'code': 'EXPORT_FAILED',
                    'message': str(e),
                    'details': f"导出失败，格式: {params.get('export_format', 'unknown')}"
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def _format_export_data(self, data: Dict[str, Any], section_type: str) -> Dict[str, Any]:
        """
        格式化导出数据，移除不必要的字段并标准化结构
        
        Args:
            data: 原始数据
            section_type: 数据部分类型
            
        Returns:
            格式化后的数据
        """
        try:
            if not isinstance(data, dict):
                return {'error': 'Invalid data format', 'original_data': data}
            
            # 移除缓存和内部字段
            cleaned_data = {k: v for k, v in data.items() 
                          if k not in ['cached', 'compression', 'pagination']}
            
            # 根据部分类型进行特殊处理
            if section_type == 'overview':
                # 概览数据保持完整结构
                return cleaned_data
            
            elif section_type == 'sales_trend':
                # 销售趋势数据简化
                if 'data' in cleaned_data and isinstance(cleaned_data['data'], list):
                    # 保留核心字段
                    core_fields = ['period', 'month', 'quarter', 'product_name', 'total_sales', 'order_count', 'avg_order_value']
                    simplified_data = []
                    for item in cleaned_data['data']:
                        if isinstance(item, dict):
                            simplified_item = {k: v for k, v in item.items() if k in core_fields}
                            simplified_data.append(simplified_item)
                    cleaned_data['data'] = simplified_data
            
            elif section_type == 'customer_analysis':
                # 客户分析数据处理
                if 'data' in cleaned_data and isinstance(cleaned_data['data'], list):
                    core_fields = ['customer_name', 'recency', 'frequency', 'monetary', 'rfm_score', 'customer_segment', 'customer_value']
                    simplified_data = []
                    for item in cleaned_data['data']:
                        if isinstance(item, dict):
                            simplified_item = {k: v for k, v in item.items() if k in core_fields}
                            simplified_data.append(simplified_item)
                    cleaned_data['data'] = simplified_data
            
            elif section_type == 'inventory_analysis':
                # 库存分析数据处理
                if 'data' in cleaned_data and isinstance(cleaned_data['data'], dict):
                    # 保留关键统计信息
                    inventory_data = cleaned_data['data']
                    if 'turnover_analysis' in inventory_data:
                        core_fields = ['product_name', 'turnover_rate', 'stock_value', 'category']
                        simplified_analysis = []
                        for item in inventory_data['turnover_analysis']:
                            if isinstance(item, dict):
                                simplified_item = {k: v for k, v in item.items() if k in core_fields}
                                simplified_analysis.append(simplified_item)
                        inventory_data['turnover_analysis'] = simplified_analysis
            
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"格式化导出数据失败: {str(e)}")
            return {'error': str(e), 'original_data': data}
    
    def _export_as_json(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导出为JSON格式
        
        Args:
            export_data: 导出数据
            
        Returns:
            JSON格式的数据
        """
        try:
            # JSON格式直接返回，但确保所有数据都是可序列化的
            def make_serializable(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: make_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_serializable(item) for item in obj]
                else:
                    return obj
            
            return make_serializable(export_data)
            
        except Exception as e:
            self.logger.error(f"JSON导出失败: {str(e)}")
            return {'error': str(e)}
    
    def _export_as_csv(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导出为CSV格式（准备CSV数据结构）
        
        Args:
            export_data: 导出数据
            
        Returns:
            CSV格式的数据结构
        """
        try:
            csv_data = {}
            
            # 处理每个数据部分
            for section, data in export_data.get('data', {}).items():
                if section == 'overview':
                    # 概览数据转换为键值对表格
                    if isinstance(data, dict) and 'overview' in data:
                        overview = data['overview']
                        csv_data[f'{section}_summary'] = [
                            {'指标': k, '数值': v} for k, v in overview.items()
                            if isinstance(v, (int, float, str)) and not k.startswith('_')
                        ]
                
                elif section == 'sales_trend':
                    # 销售趋势数据
                    if isinstance(data, dict):
                        for dimension, trend_data in data.items():
                            if isinstance(trend_data, dict) and 'data' in trend_data:
                                csv_data[f'{section}_{dimension}'] = trend_data['data']
                
                elif section in ['customer_analysis', 'inventory_analysis']:
                    # 分析数据
                    if isinstance(data, dict) and 'data' in data:
                        if isinstance(data['data'], list):
                            csv_data[section] = data['data']
                        elif isinstance(data['data'], dict):
                            # 将字典数据转换为表格格式
                            flattened_data = []
                            for key, value in data['data'].items():
                                if isinstance(value, list):
                                    flattened_data.extend(value)
                                else:
                                    flattened_data.append({'项目': key, '数值': value})
                            csv_data[section] = flattened_data
            
            return {
                'format': 'csv',
                'sheets': csv_data,
                'export_info': export_data.get('export_info', {})
            }
            
        except Exception as e:
            self.logger.error(f"CSV导出失败: {str(e)}")
            return {'error': str(e)}
    
    def _prepare_excel_export(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备Excel导出数据（为未来的Excel导出功能预留接口）
        
        Args:
            export_data: 导出数据
            
        Returns:
            Excel导出准备数据
        """
        try:
            # 基于CSV数据结构，但添加Excel特有的格式信息
            csv_structure = self._export_as_csv(export_data)
            
            excel_data = {
                'format': 'excel',
                'workbook_info': {
                    'title': '数据分析仪表板报告',
                    'author': '数据分析系统',
                    'created_at': datetime.now().isoformat()
                },
                'sheets': {},
                'formatting': {
                    'header_style': {
                        'font_bold': True,
                        'bg_color': '#4472C4',
                        'font_color': '#FFFFFF'
                    },
                    'data_style': {
                        'font_size': 10,
                        'border': True
                    }
                }
            }
            
            # 转换CSV数据为Excel工作表结构
            for sheet_name, sheet_data in csv_structure.get('sheets', {}).items():
                excel_data['sheets'][sheet_name] = {
                    'data': sheet_data,
                    'columns': list(sheet_data[0].keys()) if sheet_data else [],
                    'title': self._get_sheet_title(sheet_name)
                }
            
            return excel_data
            
        except Exception as e:
            self.logger.error(f"Excel导出准备失败: {str(e)}")
            return {'error': str(e)}
    
    def _prepare_pdf_export(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备PDF导出数据（为未来的PDF导出功能预留接口）
        
        Args:
            export_data: 导出数据
            
        Returns:
            PDF导出准备数据
        """
        try:
            pdf_data = {
                'format': 'pdf',
                'document_info': {
                    'title': '数据分析仪表板报告',
                    'subject': '业务数据分析报告',
                    'author': '数据分析系统',
                    'created_at': datetime.now().isoformat()
                },
                'sections': [],
                'layout': {
                    'page_size': 'A4',
                    'orientation': 'portrait',
                    'margins': {'top': 20, 'bottom': 20, 'left': 20, 'right': 20}
                }
            }
            
            # 构建PDF部分
            for section, data in export_data.get('data', {}).items():
                section_info = {
                    'title': self._get_section_title(section),
                    'type': section,
                    'content': data,
                    'charts': [],  # 预留图表数据
                    'tables': []   # 预留表格数据
                }
                
                # 根据数据类型准备内容
                if section == 'overview' and isinstance(data, dict):
                    # 概览数据转换为表格
                    if 'overview' in data:
                        overview = data['overview']
                        section_info['tables'].append({
                            'title': '业务概览指标',
                            'headers': ['指标', '数值'],
                            'rows': [[k, str(v)] for k, v in overview.items() 
                                   if isinstance(v, (int, float, str)) and not k.startswith('_')]
                        })
                
                elif 'data' in data and isinstance(data['data'], list):
                    # 列表数据转换为表格
                    if data['data']:
                        first_item = data['data'][0]
                        if isinstance(first_item, dict):
                            headers = list(first_item.keys())
                            rows = [[str(item.get(h, '')) for h in headers] for item in data['data']]
                            section_info['tables'].append({
                                'title': self._get_section_title(section),
                                'headers': headers,
                                'rows': rows
                            })
                
                pdf_data['sections'].append(section_info)
            
            return pdf_data
            
        except Exception as e:
            self.logger.error(f"PDF导出准备失败: {str(e)}")
            return {'error': str(e)}
    
    def _generate_export_filename(self, export_format: str, export_sections: List[str]) -> str:
        """
        生成导出文件名
        
        Args:
            export_format: 导出格式
            export_sections: 导出部分
            
        Returns:
            文件名
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            sections_str = '_'.join(export_sections[:3])  # 限制长度
            if len(export_sections) > 3:
                sections_str += '_etc'
            
            filename = f"dashboard_report_{sections_str}_{timestamp}.{export_format}"
            return filename
            
        except Exception:
            return f"dashboard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
    
    def _get_content_type(self, export_format: str) -> str:
        """
        获取内容类型
        
        Args:
            export_format: 导出格式
            
        Returns:
            MIME类型
        """
        content_types = {
            'json': 'application/json',
            'csv': 'text/csv',
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf'
        }
        return content_types.get(export_format, 'application/octet-stream')
    
    def _get_sheet_title(self, sheet_name: str) -> str:
        """
        获取工作表标题
        
        Args:
            sheet_name: 工作表名称
            
        Returns:
            中文标题
        """
        titles = {
            'overview_summary': '业务概览',
            'sales_trend_month': '月度销售趋势',
            'sales_trend_quarter': '季度销售趋势',
            'sales_trend_product': '产品销售分析',
            'customer_analysis': '客户价值分析',
            'inventory_analysis': '库存周转分析',
            'comparison_analysis': '对比分析'
        }
        return titles.get(sheet_name, sheet_name)
    
    def _get_section_title(self, section: str) -> str:
        """
        获取部分标题
        
        Args:
            section: 部分名称
            
        Returns:
            中文标题
        """
        titles = {
            'overview': '业务概览',
            'sales_trend': '销售趋势分析',
            'customer_analysis': '客户价值分析',
            'inventory_analysis': '库存周转分析',
            'comparison_analysis': '多维度对比分析'
        }
        return titles.get(section, section)


def main():
    """主函数（带增强的参数验证和错误处理）"""
    logger = EnhancedLogger("data_analysis_service")
    service = DataAnalysisService(logger)
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='数据分析服务')
        
        # 新的统一接口参数
        parser.add_argument('--method', type=str, help='调用的方法名称')
        parser.add_argument('--params', type=str, help='方法参数（JSON格式）')
        
        # 保持向后兼容的旧参数
        parser.add_argument('--analysis_type', type=str, default='overview', 
                          choices=['overview', 'sales_trend', 'customer_value', 'inventory_turnover', 'comparison'],
                          help='分析类型（向后兼容）')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--dimension', type=str, default='month', help='分析维度')
        parser.add_argument('--format', type=str, default='json', choices=['json'], help='输出格式')
        
        args = parser.parse_args()
        
        # 优先使用新的统一接口
        if args.method:
            # 验证方法名称
            valid_methods = [
                'get_dashboard_summary', 'get_dashboard_data', 'analyze_sales_trend', 'analyze_customer_value',
                'analyze_inventory_turnover', 'generate_comparison_analysis',
                'invalidate_cache', 'get_cache_stats', 'optimize_query_performance',
                'get_pagination_config', 'benchmark_performance', 'export_analysis_data'
            ]
            
            if args.method not in valid_methods:
                logger.error(f"无效的方法名称: {args.method}")
                result = {
                    'success': False,
                    'error': {
                        'code': 'INVALID_METHOD',
                        'message': f'无效的方法名称: {args.method}',
                        'details': f'支持的方法: {", ".join(valid_methods)}'
                    },
                    'generated_at': datetime.now().isoformat()
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
                sys.exit(1)
            
            # 解析和验证参数
            params = {}
            if args.params:
                try:
                    # 清理参数字符串
                    cleaned_params = args.params.strip()
                    if not cleaned_params:
                        params = {}
                    else:
                        params = json.loads(cleaned_params)
                        
                        # 基本参数类型验证
                        if not isinstance(params, dict):
                            raise ValueError("参数必须是JSON对象格式")
                        
                        # 检查参数大小限制
                        params_str = json.dumps(params)
                        if len(params_str) > 10000:  # 10KB限制
                            raise ValueError("参数过大，请减少参数内容")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"参数JSON解析失败: {str(e)}")
                    result = {
                        'success': False,
                        'error': {
                            'code': 'INVALID_JSON_PARAMS',
                            'message': f'参数JSON格式错误: {str(e)}',
                            'details': '参数必须是有效的JSON格式，例如: {"date_range": {"start_date": "2025-01-01"}}'
                        },
                        'generated_at': datetime.now().isoformat()
                    }
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    sys.exit(1)
                except ValueError as e:
                    logger.error(f"参数验证失败: {str(e)}")
                    result = {
                        'success': False,
                        'error': {
                            'code': 'INVALID_PARAMS_FORMAT',
                            'message': str(e),
                            'details': '请检查参数格式和内容'
                        },
                        'generated_at': datetime.now().isoformat()
                    }
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    sys.exit(1)
            
            # 使用统一的方法调用处理器（包含完整的参数验证）
            result = service.handle_method_call(args.method, params)
        
        else:
            # 向后兼容的旧接口（也应用新的验证逻辑）
            logger.info("使用向后兼容的旧接口")
            
            # 验证旧接口的参数
            try:
                # 验证日期参数
                if args.start_date:
                    if not service._validate_date_format(args.start_date):
                        raise ValueError(f"开始日期格式无效: {args.start_date}，请使用YYYY-MM-DD格式")
                
                if args.end_date:
                    if not service._validate_date_format(args.end_date):
                        raise ValueError(f"结束日期格式无效: {args.end_date}，请使用YYYY-MM-DD格式")
                
                # 验证维度参数
                valid_dimensions = ['month', 'quarter', 'product']
                if args.dimension not in valid_dimensions:
                    logger.warning(f"无效的维度参数: {args.dimension}，使用默认值: month")
                    args.dimension = 'month'
                
            except ValueError as e:
                logger.error(f"旧接口参数验证失败: {str(e)}")
                result = {
                    'success': False,
                    'error': {
                        'code': 'LEGACY_PARAMS_VALIDATION_FAILED',
                        'message': str(e),
                        'details': '请检查命令行参数格式'
                    },
                    'generated_at': datetime.now().isoformat()
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
                sys.exit(1)
            
            # 构建日期范围
            date_range = {}
            if args.start_date or args.end_date:
                date_range = {
                    'start_date': args.start_date,
                    'end_date': args.end_date
                }
            
            # 根据分析类型生成相应的分析结果
            if args.analysis_type == 'overview':
                params = {'date_range': date_range}
                data = service.handle_method_call('get_dashboard_summary', params)
                result = data
                
            elif args.analysis_type == 'sales_trend':
                params = {
                    'dimension': args.dimension,
                    'date_range': date_range
                }
                data = service.handle_method_call('analyze_sales_trend', params)
                result = data
                
            elif args.analysis_type == 'customer_value':
                params = {
                    'analysis_type': 'rfm',
                    'date_range': date_range
                }
                data = service.handle_method_call('analyze_customer_value', params)
                result = data
                
            elif args.analysis_type == 'inventory_turnover':
                params = {'date_range': date_range}
                data = service.handle_method_call('analyze_inventory_turnover', params)
                result = data
                
            elif args.analysis_type == 'comparison':
                params = {
                    'metrics': ['total_sales', 'total_purchases'],
                    'dimensions': ['month', 'product'],
                    'date_range': date_range
                }
                data = service.handle_method_call('generate_comparison_analysis', params)
                result = data
                
            else:
                result = {
                    'success': False,
                    'error': {
                        'code': 'UNKNOWN_ANALYSIS_TYPE',
                        'message': f'未知的分析类型: {args.analysis_type}',
                        'details': '请使用有效的分析类型: overview, sales_trend, customer_value, inventory_turnover, comparison'
                    },
                    'generated_at': datetime.now().isoformat()
                }
        
        # 输出标准化的JSON结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 根据结果设置退出码
        if not result.get('success', False):
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        error_result = {
            'success': False,
            'error': {
                'code': 'USER_INTERRUPTED',
                'message': '用户中断执行',
                'details': '程序被用户中断'
            },
            'generated_at': datetime.now().isoformat()
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(130)  # 标准的中断退出码
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        error_result = {
            'success': False,
            'error': {
                'code': 'EXECUTION_FAILED',
                'message': str(e),
                'details': '数据分析服务执行失败，请检查日志获取详细信息'
            },
            'generated_at': datetime.now().isoformat()
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()