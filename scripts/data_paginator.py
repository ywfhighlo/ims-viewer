#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分页器
实现服务端分页功能，限制单次数据传输量，支持数据压缩和虚拟滚动
"""

import sys
import os
import json
import gzip
import zlib
import math
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import threading

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger


class DataPaginator:
    """数据分页器类"""
    
    def __init__(self, 
                 default_page_size: int = 50,
                 max_page_size: int = 500,
                 pagination_threshold: int = 100,
                 compression_threshold: int = 1000,
                 logger: Optional[EnhancedLogger] = None):
        """
        初始化数据分页器
        
        Args:
            default_page_size: 默认页面大小
            max_page_size: 最大页面大小
            pagination_threshold: 分页阈值，超过此数量自动启用分页
            compression_threshold: 压缩阈值，超过此数量启用数据压缩
            logger: 日志记录器
        """
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size
        self.pagination_threshold = pagination_threshold
        self.compression_threshold = compression_threshold
        self.logger = logger or EnhancedLogger("data_paginator")
        
        # 分页缓存
        self._pagination_cache = {}
        self._cache_lock = threading.RLock()
        
        self.logger.info(f"数据分页器初始化完成，默认页面大小: {default_page_size}, 分页阈值: {pagination_threshold}")
    
    def should_paginate(self, record_count: int) -> bool:
        """
        判断是否需要分页
        
        Args:
            record_count: 记录数量
            
        Returns:
            是否需要分页
        """
        return record_count > self.pagination_threshold
    
    def paginate_results(self, 
                        data: List[Dict[str, Any]], 
                        page: int = 1, 
                        page_size: Optional[int] = None,
                        enable_compression: bool = True) -> Dict[str, Any]:
        """
        对结果进行分页处理
        
        Args:
            data: 原始数据列表
            page: 页码（从1开始）
            page_size: 页面大小
            enable_compression: 是否启用压缩
            
        Returns:
            分页结果
        """
        try:
            # 验证参数
            if not isinstance(data, list):
                raise ValueError("数据必须是列表类型")
            
            if page < 1:
                page = 1
            
            if page_size is None:
                page_size = self.default_page_size
            else:
                page_size = min(page_size, self.max_page_size)
            
            total_count = len(data)
            total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
            
            # 计算分页范围
            start_index = (page - 1) * page_size
            end_index = min(start_index + page_size, total_count)
            
            # 获取当前页数据
            page_data = data[start_index:end_index]
            
            # 构建分页信息
            pagination_info = {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_previous': page > 1,
                'has_next': page < total_pages,
                'previous_page': page - 1 if page > 1 else None,
                'next_page': page + 1 if page < total_pages else None,
                'start_index': start_index + 1,  # 显示用，从1开始
                'end_index': end_index,
                'is_paginated': self.should_paginate(total_count)
            }
            
            # 数据压缩处理
            compressed_data = None
            compression_info = None
            
            if enable_compression and len(page_data) >= self.compression_threshold:
                try:
                    compressed_data = self.compress_data(page_data)
                    original_size = len(json.dumps(page_data, ensure_ascii=False).encode('utf-8'))
                    compressed_size = len(compressed_data)
                    
                    compression_info = {
                        'enabled': True,
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'compression_ratio': round((1 - compressed_size / original_size) * 100, 2),
                        'algorithm': 'gzip'
                    }
                    
                    self.logger.debug(f"数据压缩完成，原始大小: {original_size} bytes, "
                                    f"压缩后: {compressed_size} bytes, "
                                    f"压缩率: {compression_info['compression_ratio']}%")
                    
                except Exception as e:
                    self.logger.warning(f"数据压缩失败: {str(e)}")
                    compressed_data = None
                    compression_info = {'enabled': False, 'error': str(e)}
            else:
                compression_info = {'enabled': False, 'reason': '数据量未达到压缩阈值'}
            
            # 构建返回结果
            result = {
                'data': page_data if compressed_data is None else None,
                'compressed_data': compressed_data,
                'pagination': pagination_info,
                'compression': compression_info,
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.debug(f"分页处理完成，页码: {page}/{total_pages}, "
                            f"数据量: {len(page_data)}/{total_count}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"分页处理失败: {str(e)}")
            return {
                'error': str(e),
                'data': [],
                'pagination': {
                    'current_page': 1,
                    'page_size': page_size or self.default_page_size,
                    'total_count': 0,
                    'total_pages': 1,
                    'has_previous': False,
                    'has_next': False,
                    'is_paginated': False
                },
                'compression': {'enabled': False},
                'generated_at': datetime.now().isoformat()
            }
    
    def get_page_info(self, total_count: int, page: int = 1, page_size: Optional[int] = None) -> Dict[str, Any]:
        """
        获取分页信息（不包含实际数据）
        
        Args:
            total_count: 总记录数
            page: 页码
            page_size: 页面大小
            
        Returns:
            分页信息
        """
        try:
            if page_size is None:
                page_size = self.default_page_size
            else:
                page_size = min(page_size, self.max_page_size)
            
            if page < 1:
                page = 1
            
            total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
            
            # 确保页码不超过总页数
            if page > total_pages:
                page = total_pages
            
            start_index = (page - 1) * page_size
            end_index = min(start_index + page_size, total_count)
            
            return {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_previous': page > 1,
                'has_next': page < total_pages,
                'previous_page': page - 1 if page > 1 else None,
                'next_page': page + 1 if page < total_pages else None,
                'start_index': start_index + 1,
                'end_index': end_index,
                'is_paginated': self.should_paginate(total_count)
            }
            
        except Exception as e:
            self.logger.error(f"获取分页信息失败: {str(e)}")
            return {
                'current_page': 1,
                'page_size': page_size or self.default_page_size,
                'total_count': 0,
                'total_pages': 1,
                'has_previous': False,
                'has_next': False,
                'is_paginated': False,
                'error': str(e)
            }
    
    def compress_data(self, data: List[Dict[str, Any]]) -> bytes:
        """
        压缩数据
        
        Args:
            data: 要压缩的数据
            
        Returns:
            压缩后的字节数据
        """
        try:
            # 将数据转换为JSON字符串
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            json_bytes = json_str.encode('utf-8')
            
            # 使用gzip压缩
            compressed_data = gzip.compress(json_bytes, compresslevel=6)
            
            return compressed_data
            
        except Exception as e:
            self.logger.error(f"数据压缩失败: {str(e)}")
            raise
    
    def decompress_data(self, compressed_data: bytes) -> List[Dict[str, Any]]:
        """
        解压缩数据
        
        Args:
            compressed_data: 压缩的字节数据
            
        Returns:
            解压缩后的数据列表
        """
        try:
            # 使用gzip解压缩
            json_bytes = gzip.decompress(compressed_data)
            json_str = json_bytes.decode('utf-8')
            
            # 解析JSON
            data = json.loads(json_str)
            
            if not isinstance(data, list):
                raise ValueError("解压缩后的数据不是列表类型")
            
            return data
            
        except Exception as e:
            self.logger.error(f"数据解压缩失败: {str(e)}")
            raise
    
    def create_virtual_scroll_config(self, 
                                   total_count: int, 
                                   item_height: int = 40,
                                   container_height: int = 400,
                                   buffer_size: int = 5) -> Dict[str, Any]:
        """
        创建虚拟滚动配置
        
        Args:
            total_count: 总项目数
            item_height: 单个项目高度（像素）
            container_height: 容器高度（像素）
            buffer_size: 缓冲区大小（额外渲染的项目数）
            
        Returns:
            虚拟滚动配置
        """
        try:
            visible_count = math.ceil(container_height / item_height)
            render_count = visible_count + (buffer_size * 2)
            
            config = {
                'total_count': total_count,
                'item_height': item_height,
                'container_height': container_height,
                'visible_count': visible_count,
                'render_count': min(render_count, total_count),
                'buffer_size': buffer_size,
                'total_height': total_count * item_height,
                'enable_virtual_scroll': total_count > visible_count * 2  # 当项目数超过可见数量的2倍时启用
            }
            
            self.logger.debug(f"虚拟滚动配置创建完成，总项目: {total_count}, "
                            f"可见项目: {visible_count}, 渲染项目: {render_count}")
            
            return config
            
        except Exception as e:
            self.logger.error(f"创建虚拟滚动配置失败: {str(e)}")
            return {
                'total_count': total_count,
                'enable_virtual_scroll': False,
                'error': str(e)
            }
    
    def get_virtual_scroll_data(self, 
                              data: List[Dict[str, Any]], 
                              start_index: int, 
                              count: int) -> Dict[str, Any]:
        """
        获取虚拟滚动数据
        
        Args:
            data: 完整数据列表
            start_index: 开始索引
            count: 需要的数据数量
            
        Returns:
            虚拟滚动数据
        """
        try:
            total_count = len(data)
            
            # 确保索引范围有效
            start_index = max(0, min(start_index, total_count - 1))
            end_index = min(start_index + count, total_count)
            
            # 获取数据切片
            slice_data = data[start_index:end_index]
            
            return {
                'data': slice_data,
                'start_index': start_index,
                'end_index': end_index,
                'count': len(slice_data),
                'total_count': total_count,
                'has_more': end_index < total_count
            }
            
        except Exception as e:
            self.logger.error(f"获取虚拟滚动数据失败: {str(e)}")
            return {
                'data': [],
                'start_index': 0,
                'end_index': 0,
                'count': 0,
                'total_count': 0,
                'has_more': False,
                'error': str(e)
            }
    
    def export_full_dataset(self, 
                          data: List[Dict[str, Any]], 
                          format_type: str = 'json',
                          compress: bool = True) -> Union[bytes, str]:
        """
        导出完整数据集
        
        Args:
            data: 要导出的数据
            format_type: 导出格式 ('json', 'csv')
            compress: 是否压缩
            
        Returns:
            导出的数据（字节或字符串）
        """
        try:
            if format_type.lower() == 'json':
                # JSON格式导出
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                
                if compress:
                    return gzip.compress(json_str.encode('utf-8'))
                else:
                    return json_str
                    
            elif format_type.lower() == 'csv':
                # CSV格式导出
                if not data:
                    csv_str = ""
                else:
                    # 获取所有字段名
                    fieldnames = set()
                    for item in data:
                        if isinstance(item, dict):
                            fieldnames.update(item.keys())
                    
                    fieldnames = sorted(list(fieldnames))
                    
                    # 构建CSV内容
                    csv_lines = [','.join(f'"{field}"' for field in fieldnames)]
                    
                    for item in data:
                        if isinstance(item, dict):
                            row = []
                            for field in fieldnames:
                                value = item.get(field, '')
                                # 处理特殊字符
                                if isinstance(value, str):
                                    value = value.replace('"', '""')
                                row.append(f'"{value}"')
                            csv_lines.append(','.join(row))
                    
                    csv_str = '\n'.join(csv_lines)
                
                if compress:
                    return gzip.compress(csv_str.encode('utf-8-sig'))  # 使用UTF-8 BOM for Excel
                else:
                    return csv_str
            
            else:
                raise ValueError(f"不支持的导出格式: {format_type}")
                
        except Exception as e:
            self.logger.error(f"导出完整数据集失败: {str(e)}")
            raise
    
    def calculate_optimal_page_size(self, 
                                  data_sample: List[Dict[str, Any]], 
                                  target_size_kb: int = 100) -> int:
        """
        计算最优页面大小
        
        Args:
            data_sample: 数据样本
            target_size_kb: 目标大小（KB）
            
        Returns:
            建议的页面大小
        """
        try:
            if not data_sample:
                return self.default_page_size
            
            # 计算单个记录的平均大小
            sample_json = json.dumps(data_sample[:min(10, len(data_sample))], ensure_ascii=False)
            sample_size_bytes = len(sample_json.encode('utf-8'))
            avg_record_size = sample_size_bytes / min(10, len(data_sample))
            
            # 计算目标页面大小
            target_size_bytes = target_size_kb * 1024
            optimal_page_size = int(target_size_bytes / avg_record_size)
            
            # 限制在合理范围内
            optimal_page_size = max(10, min(optimal_page_size, self.max_page_size))
            
            self.logger.debug(f"计算最优页面大小: {optimal_page_size}, "
                            f"平均记录大小: {avg_record_size:.2f} bytes")
            
            return optimal_page_size
            
        except Exception as e:
            self.logger.error(f"计算最优页面大小失败: {str(e)}")
            return self.default_page_size
    
    def get_pagination_summary(self, total_count: int, page_size: Optional[int] = None) -> Dict[str, Any]:
        """
        获取分页摘要信息
        
        Args:
            total_count: 总记录数
            page_size: 页面大小
            
        Returns:
            分页摘要
        """
        try:
            if page_size is None:
                page_size = self.default_page_size
            
            total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
            is_paginated = self.should_paginate(total_count)
            
            # 计算数据传输估算
            estimated_full_size_mb = (total_count * 0.5) / 1024  # 假设每条记录约0.5KB
            estimated_page_size_mb = (page_size * 0.5) / 1024
            
            return {
                'total_count': total_count,
                'page_size': page_size,
                'total_pages': total_pages,
                'is_paginated': is_paginated,
                'pagination_threshold': self.pagination_threshold,
                'estimated_full_size_mb': round(estimated_full_size_mb, 2),
                'estimated_page_size_mb': round(estimated_page_size_mb, 2),
                'data_reduction_ratio': round((1 - estimated_page_size_mb / estimated_full_size_mb) * 100, 2) if estimated_full_size_mb > 0 else 0,
                'recommended_page_size': min(page_size, self.max_page_size)
            }
            
        except Exception as e:
            self.logger.error(f"获取分页摘要失败: {str(e)}")
            return {
                'total_count': total_count,
                'is_paginated': False,
                'error': str(e)
            }


def main():
    """测试数据分页器功能"""
    logger = EnhancedLogger("data_paginator_test")
    
    try:
        print("=== 数据分页器测试 ===")
        
        # 创建测试数据
        test_data = []
        for i in range(250):
            test_data.append({
                'id': i + 1,
                'name': f'测试项目_{i + 1}',
                'value': i * 10,
                'category': f'分类_{i % 5}',
                'description': f'这是第{i + 1}个测试项目的描述信息'
            })
        
        # 创建数据分页器
        paginator = DataPaginator(
            default_page_size=20,
            pagination_threshold=50,
            compression_threshold=30,
            logger=logger
        )
        
        # 测试分页功能
        print(f"\n1. 测试分页功能（总数据: {len(test_data)} 条）")
        
        # 第一页
        page1_result = paginator.paginate_results(test_data, page=1, page_size=20)
        print(f"第1页数据量: {len(page1_result['data'])}")
        print(f"分页信息: {page1_result['pagination']}")
        print(f"压缩信息: {page1_result['compression']}")
        
        # 测试是否需要分页
        print(f"\n2. 测试分页判断")
        print(f"50条数据是否需要分页: {paginator.should_paginate(50)}")
        print(f"150条数据是否需要分页: {paginator.should_paginate(150)}")
        
        # 测试数据压缩
        print(f"\n3. 测试数据压缩")
        large_data = test_data[:100]  # 取100条数据测试压缩
        compressed = paginator.compress_data(large_data)
        decompressed = paginator.decompress_data(compressed)
        
        original_size = len(json.dumps(large_data, ensure_ascii=False).encode('utf-8'))
        compressed_size = len(compressed)
        
        print(f"原始数据大小: {original_size} bytes")
        print(f"压缩后大小: {compressed_size} bytes")
        print(f"压缩率: {((1 - compressed_size / original_size) * 100):.2f}%")
        print(f"解压缩后数据量: {len(decompressed)}")
        
        # 测试虚拟滚动配置
        print(f"\n4. 测试虚拟滚动配置")
        virtual_config = paginator.create_virtual_scroll_config(
            total_count=len(test_data),
            item_height=40,
            container_height=400
        )
        print(f"虚拟滚动配置: {virtual_config}")
        
        # 测试数据导出
        print(f"\n5. 测试数据导出")
        export_data = test_data[:10]  # 导出前10条数据
        
        # JSON导出
        json_export = paginator.export_full_dataset(export_data, format_type='json', compress=False)
        print(f"JSON导出大小: {len(json_export)} 字符")
        
        # CSV导出
        csv_export = paginator.export_full_dataset(export_data, format_type='csv', compress=False)
        print(f"CSV导出大小: {len(csv_export)} 字符")
        
        # 测试最优页面大小计算
        print(f"\n6. 测试最优页面大小计算")
        optimal_size = paginator.calculate_optimal_page_size(test_data[:20], target_size_kb=50)
        print(f"建议的页面大小: {optimal_size}")
        
        # 测试分页摘要
        print(f"\n7. 测试分页摘要")
        summary = paginator.get_pagination_summary(len(test_data), page_size=20)
        print(f"分页摘要: {json.dumps(summary, indent=2, ensure_ascii=False)}")
        
        print("\n数据分页器测试完成！")
        
    except Exception as e:
        logger.error(f"数据分页器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()