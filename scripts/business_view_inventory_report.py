#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库存盘点报表业务视图脚本（优化版）
根据库存统计数据生成库存盘点报表，支持分页、数据压缩和虚拟滚动
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.db_connection import get_database_connection
from scripts.error_handler import error_handler_decorator, safe_execute, global_error_handler
from scripts.enhanced_logger import get_logger
from scripts.data_utils import DataValidator, DataFormatter, ReportDataProcessor
from scripts.query_optimizer import QueryOptimizer
from scripts.cache_manager import cache_report_data, get_cache_manager
from scripts.data_paginator import DataPaginator
from scripts.data_transfer_optimizer import DataTransferOptimizer
from scripts.virtual_scroll_manager import VirtualScrollManager

# 数据库连接函数已移至 db_connection 模块

def generate_inventory_report(start_date: Optional[str] = None, 
                            end_date: Optional[str] = None,
                            product_name: Optional[str] = None,
                            page: int = 1,
                            page_size: Optional[int] = None,
                            enable_pagination: bool = True,
                            enable_compression: bool = True) -> Dict[str, Any]:
    """
    生成库存盘点报表（使用查询优化引擎、缓存系统和分页优化）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期  
        product_name: 产品名称
        page: 页码（从1开始）
        page_size: 页面大小
        enable_pagination: 是否启用分页
        enable_compression: 是否启用数据压缩
        
    Returns:
        包含分页信息和数据的字典
    """
    logger = EnhancedLogger("inventory_report")
    
    try:
        logger.info("开始生成库存盘点报表（使用查询优化引擎、缓存系统和分页优化）")
        
        # 构建查询参数
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'product_name': product_name
        }
        
        # 使用缓存装饰器，自动处理缓存逻辑
        def data_generator():
            optimizer = QueryOptimizer(logger)
            return optimizer.optimize_inventory_report_query(params)
        
        # 使用缓存系统，TTL设置为3分钟（180秒），库存数据变化相对较快
        report_data = cache_report_data(
            view_name='inventory_report',
            params=params,
            data_generator=data_generator,
            ttl=180
        )
        
        logger.info(f"库存盘点报表数据获取完成，共 {len(report_data)} 条记录")
        
        # 创建数据分页器和传输优化器
        paginator = DataPaginator(
            default_page_size=50,
            pagination_threshold=100,
            compression_threshold=200,
            logger=logger
        )
        
        transfer_optimizer = DataTransferOptimizer(logger=logger)
        
        # 优化数据传输
        optimization_result = transfer_optimizer.optimize_data_for_transfer(report_data)
        optimized_data = optimization_result['optimized_data']
        optimization_info = optimization_result['optimization_info']
        
        # 判断是否需要分页
        should_paginate = enable_pagination and paginator.should_paginate(len(optimized_data))
        
        if should_paginate:
            # 执行分页处理
            paginated_result = paginator.paginate_results(
                data=optimized_data,
                page=page,
                page_size=page_size,
                enable_compression=enable_compression
            )
            
            # 构建返回结果
            result = {
                'success': True,
                'data': paginated_result['data'],
                'compressed_data': paginated_result.get('compressed_data'),
                'pagination': paginated_result['pagination'],
                'compression': paginated_result['compression'],
                'optimization': optimization_info,
                'report_type': 'inventory_report',
                'generated_at': datetime.now().isoformat(),
                'query_params': params
            }
            
            # 添加统计信息
            if paginated_result['data']:
                result['statistics'] = calculate_inventory_statistics(paginated_result['data'])
            
            logger.info(f"库存盘点报表分页处理完成，页码: {page}, "
                       f"当前页数据: {len(paginated_result['data'])}, "
                       f"总数据: {paginated_result['pagination']['total_count']}")
        else:
            # 不分页，返回所有数据
            result = {
                'success': True,
                'data': optimized_data,
                'pagination': {
                    'current_page': 1,
                    'page_size': len(optimized_data),
                    'total_count': len(optimized_data),
                    'total_pages': 1,
                    'has_previous': False,
                    'has_next': False,
                    'is_paginated': False
                },
                'compression': {'enabled': False},
                'optimization': optimization_info,
                'report_type': 'inventory_report',
                'generated_at': datetime.now().isoformat(),
                'query_params': params
            }
            
            # 添加统计信息
            if optimized_data:
                result['statistics'] = calculate_inventory_statistics(optimized_data)
            
            logger.info(f"库存盘点报表生成完成（无分页），共 {len(optimized_data)} 条记录")
        
        return result
        
    except Exception as e:
        logger.error(f"生成库存盘点报表失败: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'pagination': {
                'current_page': page,
                'page_size': page_size or 50,
                'total_count': 0,
                'total_pages': 1,
                'has_previous': False,
                'has_next': False,
                'is_paginated': False
            },
            'generated_at': datetime.now().isoformat()
        }


def calculate_inventory_statistics(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算库存统计信息
    
    Args:
        data: 库存数据列表
        
    Returns:
        统计信息字典
    """
    try:
        if not data:
            return {
                'total_items': 0,
                'total_value': 0,
                'status_distribution': {},
                'supplier_distribution': {}
            }
        
        total_items = len(data)
        total_value = sum(item.get('stock_value', 0) for item in data)
        
        # 状态分布统计
        status_distribution = {}
        for item in data:
            status = item.get('stock_status', '未知')
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        # 供应商分布统计
        supplier_distribution = {}
        for item in data:
            supplier = item.get('supplier_name', '未知')
            supplier_distribution[supplier] = supplier_distribution.get(supplier, 0) + 1
        
        # 库存价值分布
        value_ranges = {
            '0-1000': 0,
            '1000-5000': 0,
            '5000-10000': 0,
            '10000+': 0
        }
        
        for item in data:
            value = item.get('stock_value', 0)
            if value < 1000:
                value_ranges['0-1000'] += 1
            elif value < 5000:
                value_ranges['1000-5000'] += 1
            elif value < 10000:
                value_ranges['5000-10000'] += 1
            else:
                value_ranges['10000+'] += 1
        
        return {
            'total_items': total_items,
            'total_value': round(total_value, 2),
            'average_value': round(total_value / total_items, 2) if total_items > 0 else 0,
            'status_distribution': status_distribution,
            'supplier_distribution': supplier_distribution,
            'value_distribution': value_ranges
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'total_items': len(data) if data else 0
        }


def generate_inventory_report_chunked(start_date: Optional[str] = None,
                                    end_date: Optional[str] = None,
                                    product_name: Optional[str] = None,
                                    enable_compression: bool = True) -> Dict[str, Any]:
    """
    生成分块传输的库存盘点报表
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        product_name: 产品名称
        enable_compression: 是否启用压缩
        
    Returns:
        分块传输准备信息
    """
    logger = EnhancedLogger("inventory_report_chunked")
    
    try:
        logger.info("开始生成分块传输的库存盘点报表")
        
        # 获取完整数据
        full_result = generate_inventory_report(
            start_date=start_date,
            end_date=end_date,
            product_name=product_name,
            enable_pagination=False,
            enable_compression=False
        )
        
        if not full_result['success']:
            return full_result
        
        # 创建数据传输优化器
        transfer_optimizer = DataTransferOptimizer(
            chunk_size=100,  # 每块100条记录
            compression_threshold=50,
            logger=logger
        )
        
        # 准备分块传输
        transfer_info = transfer_optimizer.prepare_chunked_transfer(
            data=full_result['data'],
            enable_compression=enable_compression
        )
        
        if 'error' in transfer_info:
            return {
                'success': False,
                'error': transfer_info['error'],
                'report_type': 'inventory_report_chunked'
            }
        
        # 添加报表特定信息
        transfer_info.update({
            'success': True,
            'report_type': 'inventory_report_chunked',
            'query_params': {
                'start_date': start_date,
                'end_date': end_date,
                'product_name': product_name
            },
            'statistics': full_result.get('statistics', {}),
            'optimization': full_result.get('optimization', {})
        })
        
        logger.info(f"分块传输准备完成，会话ID: {transfer_info['session_id']}, "
                   f"总数据: {transfer_info['total_count']}, "
                   f"分块数: {transfer_info['total_chunks']}")
        
        return transfer_info
        
    except Exception as e:
        logger.error(f"生成分块传输的库存盘点报表失败: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'report_type': 'inventory_report_chunked'
        }


def create_virtual_scroll_config_for_inventory(total_count: int,
                                             container_height: int = 400,
                                             item_height: int = 60) -> Dict[str, Any]:
    """
    为库存报表创建虚拟滚动配置
    
    Args:
        total_count: 总记录数
        container_height: 容器高度
        item_height: 项目高度
        
    Returns:
        虚拟滚动配置
    """
    logger = EnhancedLogger("inventory_virtual_scroll")
    
    try:
        scroll_manager = VirtualScrollManager(
            default_item_height=item_height,
            default_container_height=container_height,
            logger=logger
        )
        
        config = scroll_manager.create_virtual_scroll_config(
            data_source='inventory_report',
            total_count=total_count,
            item_height=item_height,
            container_height=container_height
        )
        
        # 添加库存报表特定的配置
        config.update({
            'report_type': 'inventory_report',
            'item_template': {
                'height': item_height,
                'fields': [
                    'product_code', 'product_name', 'product_model',
                    'current_stock', 'unit_price', 'stock_value',
                    'stock_status', 'supplier_name'
                ]
            }
        })
        
        return config
        
    except Exception as e:
        logger.error(f"创建库存报表虚拟滚动配置失败: {str(e)}")
        return {
            'error': str(e),
            'enable_virtual_scroll': False
        }

def format_table_output(data: List[Dict[str, Any]]) -> str:
    """格式化表格输出"""
    if not data:
        return "暂无库存数据"
    
    # 表头
    headers = ['产品编码', '产品名称', '型号', '单位', '当前库存', '单价', '库存价值', '库存状态', '供应商']
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for item in data:
        col_widths[0] = max(col_widths[0], len(str(item.get('product_code', ''))))
        col_widths[1] = max(col_widths[1], len(str(item.get('product_name', ''))))
        col_widths[2] = max(col_widths[2], len(str(item.get('product_model', ''))))
        col_widths[3] = max(col_widths[3], len(str(item.get('unit', ''))))
        col_widths[4] = max(col_widths[4], len(str(item.get('current_stock', ''))))
        col_widths[5] = max(col_widths[5], len(f"{item.get('unit_price', 0):.2f}"))
        col_widths[6] = max(col_widths[6], len(f"{item.get('stock_value', 0):.2f}"))
        col_widths[7] = max(col_widths[7], len(str(item.get('stock_status', ''))))
        col_widths[8] = max(col_widths[8], len(str(item.get('supplier_name', ''))))
    
    # 构建表格
    result = []
    
    # 表头
    header_row = '|'.join(h.ljust(w) for h, w in zip(headers, col_widths))
    result.append(header_row)
    result.append('-' * len(header_row))
    
    # 数据行
    for item in data:
        row = [
            str(item.get('product_code', '')).ljust(col_widths[0]),
            str(item.get('product_name', '')).ljust(col_widths[1]),
            str(item.get('product_model', '')).ljust(col_widths[2]),
            str(item.get('unit', '')).ljust(col_widths[3]),
            str(item.get('current_stock', '')).ljust(col_widths[4]),
            f"{item.get('unit_price', 0):.2f}".ljust(col_widths[5]),
            f"{item.get('stock_value', 0):.2f}".ljust(col_widths[6]),
            str(item.get('stock_status', '')).ljust(col_widths[7]),
            str(item.get('supplier_name', '')).ljust(col_widths[8])
        ]
        result.append('|'.join(row))
    
    # 统计信息
    total_items = len(data)
    total_value = sum(item.get('stock_value', 0) for item in data)
    normal_count = sum(1 for item in data if item.get('stock_status') == '正常')
    low_stock_count = sum(1 for item in data if item.get('stock_status') == '低库存')
    out_of_stock_count = sum(1 for item in data if item.get('stock_status') == '缺货')
    
    result.append('')
    result.append(f"总计: {total_items} 个产品")
    result.append(f"库存总价值: ¥{total_value:.2f}")
    result.append(f"正常库存: {normal_count} 个")
    result.append(f"低库存: {low_stock_count} 个")
    result.append(f"缺货: {out_of_stock_count} 个")
    
    return '\n'.join(result)

@error_handler_decorator(context="库存盘点报表主函数", reraise=False)
def main():
    """主函数"""
    logger = get_logger("inventory_report")
    validator = DataValidator()
    formatter = DataFormatter()
    processor = ReportDataProcessor()
    
    logger.set_context(module="inventory_report", operation="main")
    op_index = logger.start_operation("生成库存盘点报表")
    
    output_format = 'json'  # 默认格式
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成库存盘点报表（支持分页和数据优化）')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--product_name', type=str, help='产品名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        parser.add_argument('--page', type=int, default=1, help='页码（从1开始）')
        parser.add_argument('--page_size', type=int, help='页面大小')
        parser.add_argument('--no_pagination', action='store_true', help='禁用分页')
        parser.add_argument('--no_compression', action='store_true', help='禁用数据压缩')
        parser.add_argument('--chunked', action='store_true', help='使用分块传输模式')
        parser.add_argument('--virtual_scroll', action='store_true', help='生成虚拟滚动配置')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        product_name = args.product_name
        output_format = args.format
        page = args.page
        page_size = args.page_size
        enable_pagination = not args.no_pagination
        enable_compression = not args.no_compression
        use_chunked = args.chunked
        generate_virtual_scroll = args.virtual_scroll
        
        logger.info("开始生成库存盘点报表", 
                   start_date=start_date,
                   end_date=end_date,
                   product_name=product_name,
                   output_format=output_format)
        
        # 验证输入参数
        if start_date and not validator.validate_date_format(start_date):
            raise ValueError(f"开始日期格式无效: {start_date}")
        
        if end_date and not validator.validate_date_format(end_date):
            raise ValueError(f"结束日期格式无效: {end_date}")
        
        # 根据模式生成不同类型的报表
        if use_chunked:
            # 分块传输模式
            logger.info("使用分块传输模式生成报表")
            report_result = safe_execute(
                generate_inventory_report_chunked,
                (start_date, end_date, product_name, enable_compression),
                default_return={'success': False, 'error': '分块传输失败'},
                context="生成分块传输库存盘点报表"
            )
        elif generate_virtual_scroll:
            # 虚拟滚动配置模式
            logger.info("生成虚拟滚动配置")
            # 先获取总数据量
            temp_result = safe_execute(
                generate_inventory_report,
                (start_date, end_date, product_name, 1, None, False, False),
                default_return={'success': False, 'data': []},
                context="获取数据总量"
            )
            
            if temp_result.get('success'):
                total_count = temp_result['pagination']['total_count']
                virtual_config = create_virtual_scroll_config_for_inventory(total_count)
                report_result = {
                    'success': True,
                    'virtual_scroll_config': virtual_config,
                    'total_count': total_count,
                    'report_type': 'inventory_report_virtual_scroll'
                }
            else:
                report_result = temp_result
        else:
            # 标准模式（支持分页）
            logger.info(f"使用标准模式生成报表，页码: {page}, 分页: {enable_pagination}")
            report_result = safe_execute(
                generate_inventory_report,
                (start_date, end_date, product_name, page, page_size, enable_pagination, enable_compression),
                default_return={'success': False, 'error': '报表生成失败', 'data': []},
                context="生成库存盘点报表"
            )
        
        # 检查结果
        if not report_result.get('success'):
            logger.warning(f"报表生成失败: {report_result.get('error', '未知错误')}")
        else:
            data_count = len(report_result.get('data', []))
            logger.info(f"库存盘点报表生成完成", record_count=data_count)
        
        # 输出结果
        if output_format == 'table' and not use_chunked and not generate_virtual_scroll:
            try:
                # 表格格式只适用于标准模式
                data = report_result.get('data', [])
                if data:
                    formatted_output = format_table_output(data)
                    print(formatted_output)
                    
                    # 显示分页信息
                    pagination = report_result.get('pagination', {})
                    if pagination.get('is_paginated'):
                        print(f"\n分页信息: 第 {pagination['current_page']} 页，共 {pagination['total_pages']} 页")
                        print(f"显示 {pagination['start_index']}-{pagination['end_index']} 条，共 {pagination['total_count']} 条记录")
                        
                        if pagination.get('has_previous'):
                            print(f"上一页: --page {pagination['previous_page']}")
                        if pagination.get('has_next'):
                            print(f"下一页: --page {pagination['next_page']}")
                    
                    # 显示统计信息
                    statistics = report_result.get('statistics', {})
                    if statistics:
                        print(f"\n当前页统计:")
                        print(f"项目数: {statistics.get('total_items', 0)}")
                        print(f"总价值: ¥{statistics.get('total_value', 0):.2f}")
                        print(f"平均价值: ¥{statistics.get('average_value', 0):.2f}")
                else:
                    print("暂无库存数据")
            except Exception as e:
                logger.error(f"格式化表格输出失败: {e}")
                print("报表格式化失败")
        else:
            # JSON格式输出
            print(json.dumps(report_result, ensure_ascii=False, indent=2))
        
        logger.end_operation(op_index, success=True, record_count=len(report_result.get('data', [])))
            
    except Exception as e:
        logger.error(f"库存盘点报表生成失败", error=str(e), include_traceback=True)
        logger.end_operation(op_index, success=False, error=str(e))
        
        if output_format == 'json':
            print(json.dumps({'error': str(e)}, ensure_ascii=False))
        else:
            print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()