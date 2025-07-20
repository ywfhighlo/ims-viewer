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
    
    def analyze_sales_trend(self, dimension: str = 'month', date_range: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        分析销售趋势
        
        Args:
            dimension: 分析维度 ('month', 'quarter', 'product', 'customer')
            date_range: 日期范围
            
        Returns:
            销售趋势数据
        """
        try:
            self.logger.info(f"开始分析销售趋势，维度: {dimension}")
            
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            # 获取销售汇总数据
            sales_summary = generate_sales_summary(start_date, end_date, self.logger)
            
            if dimension == 'month' or dimension == 'quarter':
                # 返回月度趋势数据
                trend_data = sales_summary.get('monthly_trend', [])
                
                if dimension == 'quarter':
                    # 将月度数据聚合为季度数据
                    quarterly_data = {}
                    for item in trend_data:
                        month = item.get('month', '')
                        if month:
                            year, month_num = month.split('-')
                            quarter = f"{year}-Q{(int(month_num) - 1) // 3 + 1}"
                            
                            if quarter not in quarterly_data:
                                quarterly_data[quarter] = {
                                    'quarter': quarter,
                                    'total_amount': 0,
                                    'total_quantity': 0,
                                    'order_count': 0
                                }
                            
                            quarterly_data[quarter]['total_amount'] += item.get('total_amount', 0)
                            quarterly_data[quarter]['total_quantity'] += item.get('total_quantity', 0)
                            quarterly_data[quarter]['order_count'] += item.get('order_count', 0)
                    
                    trend_data = sorted(quarterly_data.values(), key=lambda x: x['quarter'])
                
                return trend_data
            
            elif dimension == 'product':
                # 返回产品销售排名
                return sales_summary.get('top_products', [])
            
            elif dimension == 'customer':
                # 返回客户销售排名
                return sales_summary.get('top_customers', [])
            
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"分析销售趋势失败: {str(e)}")
            raise
    
    def analyze_customer_value(self, analysis_type: str = 'rfm') -> List[Dict[str, Any]]:
        """
        分析客户价值
        
        Args:
            analysis_type: 分析类型 ('rfm', 'ranking', 'segmentation')
            
        Returns:
            客户价值分析数据
        """
        try:
            self.logger.info(f"开始分析客户价值，类型: {analysis_type}")
            
            # 获取应收账款数据（包含客户交易信息）
            receivables_data = generate_receivables_summary(logger=self.logger)
            
            if analysis_type == 'rfm':
                # RFM分析（最近购买时间、购买频率、购买金额）
                rfm_data = []
                for customer in receivables_data.get('top_receivables', []):
                    # 简化的RFM评分
                    recency_score = 5 if customer.get('age_days', 999) <= 30 else (3 if customer.get('age_days', 999) <= 90 else 1)
                    frequency_score = 5 if customer.get('receivable_balance', 0) > 10000 else 3
                    monetary_score = 5 if customer.get('receivable_balance', 0) > 50000 else (3 if customer.get('receivable_balance', 0) > 10000 else 1)
                    
                    # 客户分类
                    total_score = recency_score + frequency_score + monetary_score
                    if total_score >= 12:
                        segment = '冠军客户'
                    elif total_score >= 9:
                        segment = '忠诚客户'
                    elif total_score >= 6:
                        segment = '潜力客户'
                    else:
                        segment = '风险客户'
                    
                    rfm_data.append({
                        'customer_name': customer.get('customer_name', ''),
                        'recency': recency_score,
                        'frequency': frequency_score,
                        'monetary': monetary_score,
                        'rfm_score': total_score,
                        'customer_segment': segment,
                        'customer_value': customer.get('receivable_balance', 0)
                    })
                
                return rfm_data
            
            elif analysis_type == 'ranking':
                # 客户排名分析
                return receivables_data.get('top_receivables', [])
            
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"分析客户价值失败: {str(e)}")
            raise
    
    def analyze_inventory_turnover(self, date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        分析库存周转情况
        
        Args:
            date_range: 日期范围
            
        Returns:
            库存周转分析数据
        """
        try:
            self.logger.info("开始分析库存周转情况")
            
            # 获取库存数据
            inventory_result = generate_inventory_report(
                enable_pagination=False,
                enable_compression=False
            )
            inventory_data = inventory_result.get('data', []) if inventory_result.get('success') else []
            
            # 获取销售和采购数据
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            sales_summary = generate_sales_summary(start_date, end_date, self.logger)
            purchase_summary = generate_purchase_summary(start_date, end_date, self.logger)
            
            # 计算库存周转分析
            total_inventory_value = sum(item.get('stock_value', 0) for item in inventory_data)
            total_sales_amount = sales_summary.get('total_amount', 0)
            
            # 估算整体周转率
            overall_turnover_rate = (total_sales_amount / total_inventory_value) if total_inventory_value > 0 else 0
            
            # 分析各产品的周转情况
            turnover_analysis = []
            for item in inventory_data:
                stock_value = item.get('stock_value', 0)
                if stock_value > 0:
                    # 简化的周转率计算（基于库存价值和销售情况）
                    estimated_turnover = (stock_value / total_inventory_value * total_sales_amount / stock_value) if stock_value > 0 else 0
                    
                    turnover_analysis.append({
                        'product_name': item.get('product_name', ''),
                        'product_code': item.get('product_code', ''),
                        'current_stock': item.get('current_stock', 0),
                        'stock_value': stock_value,
                        'turnover_rate': round(estimated_turnover, 2),
                        'stock_status': item.get('stock_status', ''),
                        'category': 'fast_moving' if estimated_turnover > 2 else ('slow_moving' if estimated_turnover < 0.5 else 'normal')
                    })
            
            # 按周转率排序
            turnover_analysis.sort(key=lambda x: x['turnover_rate'], reverse=True)
            
            # 统计各类别数量
            fast_moving_items = len([item for item in turnover_analysis if item['category'] == 'fast_moving'])
            slow_moving_items = len([item for item in turnover_analysis if item['category'] == 'slow_moving'])
            dead_stock_items = len([item for item in inventory_data if item.get('stock_status') == '缺货'])
            
            analysis_result = {
                'overall_turnover_rate': round(overall_turnover_rate, 2),
                'fast_moving_items': fast_moving_items,
                'slow_moving_items': slow_moving_items,
                'dead_stock_count': dead_stock_items,
                'total_inventory_value': total_inventory_value,
                'turnover_analysis': turnover_analysis,
                'dead_stock_items': [item for item in inventory_data if item.get('stock_status') == '缺货'][:10],  # 前10个缺货商品
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"库存周转分析完成，整体周转率: {overall_turnover_rate:.2f}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"分析库存周转失败: {str(e)}")
            raise
    
    def generate_comparison_analysis(self, metrics: List[str], dimensions: List[str], 
                                   date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        生成多维度对比分析
        
        Args:
            metrics: 指标列表 ['total_sales', 'sales_count', 'total_purchases', 'purchase_count']
            dimensions: 维度列表 ['month', 'product', 'customer', 'supplier']
            date_range: 日期范围
            
        Returns:
            对比分析数据
        """
        try:
            self.logger.info(f"开始生成对比分析，指标: {metrics}, 维度: {dimensions}")
            
            start_date = date_range.get('start_date') if date_range else None
            end_date = date_range.get('end_date') if date_range else None
            
            comparison_data = {}
            
            # 获取基础数据
            if 'total_sales' in metrics or 'sales_count' in metrics:
                sales_summary = generate_sales_summary(start_date, end_date, self.logger)
                comparison_data['sales'] = sales_summary
            
            if 'total_purchases' in metrics or 'purchase_count' in metrics:
                purchase_summary = generate_purchase_summary(start_date, end_date, self.logger)
                comparison_data['purchases'] = purchase_summary
            
            # 按维度组织对比数据
            comparison_result = {
                'metrics': metrics,
                'dimensions': dimensions,
                'data': {},
                'summary': {},
                'generated_at': datetime.now().isoformat()
            }
            
            # 月度对比
            if 'month' in dimensions:
                monthly_comparison = {}
                
                if 'sales' in comparison_data:
                    monthly_comparison['sales_trend'] = comparison_data['sales'].get('monthly_trend', [])
                
                if 'purchases' in comparison_data:
                    monthly_comparison['purchase_trend'] = comparison_data['purchases'].get('monthly_trend', [])
                
                comparison_result['data']['monthly'] = monthly_comparison
            
            # 产品对比
            if 'product' in dimensions:
                product_comparison = {}
                
                if 'sales' in comparison_data:
                    product_comparison['top_selling_products'] = comparison_data['sales'].get('top_products', [])
                
                if 'purchases' in comparison_data:
                    product_comparison['top_purchased_products'] = comparison_data['purchases'].get('top_products', [])
                
                comparison_result['data']['products'] = product_comparison
            
            # 生成汇总统计
            comparison_result['summary'] = {
                'total_sales': comparison_data.get('sales', {}).get('total_amount', 0),
                'total_purchases': comparison_data.get('purchases', {}).get('total_amount', 0),
                'sales_vs_purchases_ratio': (comparison_data.get('sales', {}).get('total_amount', 0) / 
                                           max(1, comparison_data.get('purchases', {}).get('total_amount', 1))),
                'profit_margin': comparison_data.get('sales', {}).get('total_amount', 0) - comparison_data.get('purchases', {}).get('total_amount', 0)
            }
            
            self.logger.info("对比分析生成完成")
            return comparison_result
            
        except Exception as e:
            self.logger.error(f"生成对比分析失败: {str(e)}")
            raise
    
    def handle_method_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一的方法调用处理器
        
        Args:
            method: 方法名称
            params: 方法参数
            
        Returns:
            标准化的JSON响应
        """
        try:
            self.logger.info(f"处理方法调用: {method}, 参数: {params}")
            
            # 使用缓存装饰器包装数据生成
            cache_key_params = {'method': method, **params}
            
            def data_generator():
                if method == 'get_dashboard_summary':
                    date_range = params.get('date_range')
                    return self.get_business_overview(date_range)
                
                elif method == 'analyze_sales_trend':
                    dimension = params.get('dimension', 'month')
                    date_range = params.get('date_range')
                    return self.analyze_sales_trend(dimension, date_range)
                
                elif method == 'analyze_customer_value':
                    analysis_type = params.get('analysis_type', 'rfm')
                    return self.analyze_customer_value(analysis_type)
                
                elif method == 'analyze_inventory_turnover':
                    date_range = params.get('date_range')
                    return self.analyze_inventory_turnover(date_range)
                
                elif method == 'generate_comparison_analysis':
                    metrics = params.get('metrics', ['total_sales', 'total_purchases'])
                    dimensions = params.get('dimensions', ['month', 'product'])
                    date_range = params.get('date_range')
                    return self.generate_comparison_analysis(metrics, dimensions, date_range)
                
                else:
                    raise ValueError(f"未知的方法: {method}")
            
            # 使用缓存装饰器获取数据
            data = cache_report_data(
                view_name=f"data_analysis_{method}",
                params=cache_key_params,
                data_generator=data_generator,
                ttl=300,  # 5分钟缓存
                cache_manager=self.cache_manager
            )
            
            # 返回标准化的成功响应
            return {
                'success': True,
                'method': method,
                'data': data,
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

def main():
    """主函数"""
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
            # 解析参数
            params = {}
            if args.params:
                try:
                    params = json.loads(args.params)
                except json.JSONDecodeError as e:
                    logger.error(f"参数解析失败: {str(e)}")
                    result = {
                        'success': False,
                        'error': {
                            'code': 'INVALID_PARAMS',
                            'message': f'参数格式错误: {str(e)}',
                            'details': '参数必须是有效的JSON格式'
                        },
                        'generated_at': datetime.now().isoformat()
                    }
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    sys.exit(1)
            
            # 使用统一的方法调用处理器
            result = service.handle_method_call(args.method, params)
        
        else:
            # 向后兼容的旧接口
            logger.info("使用向后兼容的旧接口")
            
            # 构建日期范围
            date_range = None
            if args.start_date or args.end_date:
                date_range = {
                    'start_date': args.start_date,
                    'end_date': args.end_date
                }
            
            # 根据分析类型生成相应的分析结果
            if args.analysis_type == 'overview':
                data = service.get_business_overview(date_range)
                result = {
                    'success': True,
                    'method': 'get_dashboard_summary',
                    'data': data,
                    'generated_at': datetime.now().isoformat()
                }
            elif args.analysis_type == 'sales_trend':
                data = service.analyze_sales_trend(args.dimension, date_range)
                result = {
                    'success': True,
                    'method': 'analyze_sales_trend',
                    'data': data,
                    'generated_at': datetime.now().isoformat()
                }
            elif args.analysis_type == 'customer_value':
                data = service.analyze_customer_value('rfm')
                result = {
                    'success': True,
                    'method': 'analyze_customer_value',
                    'data': data,
                    'generated_at': datetime.now().isoformat()
                }
            elif args.analysis_type == 'inventory_turnover':
                data = service.analyze_inventory_turnover(date_range)
                result = {
                    'success': True,
                    'method': 'analyze_inventory_turnover',
                    'data': data,
                    'generated_at': datetime.now().isoformat()
                }
            elif args.analysis_type == 'comparison':
                data = service.generate_comparison_analysis(
                    ['total_sales', 'total_purchases'],
                    ['month', 'product'],
                    date_range
                )
                result = {
                    'success': True,
                    'method': 'generate_comparison_analysis',
                    'data': data,
                    'generated_at': datetime.now().isoformat()
                }
            else:
                result = {
                    'success': False,
                    'error': {
                        'code': 'UNKNOWN_ANALYSIS_TYPE',
                        'message': f'未知的分析类型: {args.analysis_type}',
                        'details': '请使用有效的分析类型'
                    },
                    'generated_at': datetime.now().isoformat()
                }
        
        # 输出标准化的JSON结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        error_result = {
            'success': False,
            'error': {
                'code': 'EXECUTION_FAILED',
                'message': str(e),
                'details': '数据分析服务执行失败'
            },
            'generated_at': datetime.now().isoformat()
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()