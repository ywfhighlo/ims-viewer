#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟滚动管理器
为前端提供虚拟滚动支持，优化大数据集的显示性能
"""

import sys
import os
import json
import math
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
import threading

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.data_paginator import DataPaginator


class VirtualScrollManager:
    """虚拟滚动管理器类"""
    
    def __init__(self, 
                 default_item_height: int = 40,
                 default_container_height: int = 400,
                 buffer_size: int = 5,
                 cache_size: int = 1000,
                 logger: Optional[EnhancedLogger] = None):
        """
        初始化虚拟滚动管理器
        
        Args:
            default_item_height: 默认项目高度（像素）
            default_container_height: 默认容器高度（像素）
            buffer_size: 缓冲区大小（额外渲染的项目数）
            cache_size: 缓存大小
            logger: 日志记录器
        """
        self.default_item_height = default_item_height
        self.default_container_height = default_container_height
        self.buffer_size = buffer_size
        self.cache_size = cache_size
        self.logger = logger or EnhancedLogger("virtual_scroll_manager")
        
        # 数据缓存
        self._data_cache = {}
        self._cache_lock = threading.RLock()
        
        # 数据分页器
        self.paginator = DataPaginator(logger=self.logger)
        
        self.logger.info(f"虚拟滚动管理器初始化完成，默认项目高度: {default_item_height}px, "
                        f"容器高度: {default_container_height}px")
    
    def create_virtual_scroll_config(self, 
                                   data_source: str,
                                   total_count: int,
                                   item_height: Optional[int] = None,
                                   container_height: Optional[int] = None,
                                   enable_dynamic_height: bool = False) -> Dict[str, Any]:
        """
        创建虚拟滚动配置
        
        Args:
            data_source: 数据源标识
            total_count: 总项目数
            item_height: 项目高度
            container_height: 容器高度
            enable_dynamic_height: 是否启用动态高度
            
        Returns:
            虚拟滚动配置
        """
        try:
            if item_height is None:
                item_height = self.default_item_height
            if container_height is None:
                container_height = self.default_container_height
            
            # 计算可见项目数
            visible_count = math.ceil(container_height / item_height)
            
            # 计算渲染项目数（包含缓冲区）
            render_count = visible_count + (self.buffer_size * 2)
            render_count = min(render_count, total_count)
            
            # 计算总高度
            total_height = total_count * item_height
            
            # 判断是否需要启用虚拟滚动
            enable_virtual_scroll = total_count > visible_count * 2
            
            # 计算滚动条配置
            scrollbar_config = self._calculate_scrollbar_config(
                total_height, container_height, item_height
            )
            
            config = {
                'data_source': data_source,
                'total_count': total_count,
                'item_height': item_height,
                'container_height': container_height,
                'visible_count': visible_count,
                'render_count': render_count,
                'buffer_size': self.buffer_size,
                'total_height': total_height,
                'enable_virtual_scroll': enable_virtual_scroll,
                'enable_dynamic_height': enable_dynamic_height,
                'scrollbar': scrollbar_config,
                'performance': {
                    'estimated_dom_nodes': render_count,
                    'memory_usage_estimate_kb': render_count * 0.5,  # 假设每个DOM节点约0.5KB
                    'render_optimization_ratio': round((1 - render_count / total_count) * 100, 2) if total_count > 0 else 0
                },
                'created_at': datetime.now().isoformat()
            }
            
            self.logger.debug(f"虚拟滚动配置创建完成，数据源: {data_source}, "
                            f"总项目: {total_count}, 渲染项目: {render_count}, "
                            f"启用虚拟滚动: {enable_virtual_scroll}")
            
            return config
            
        except Exception as e:
            self.logger.error(f"创建虚拟滚动配置失败: {str(e)}")
            return {
                'data_source': data_source,
                'total_count': total_count,
                'enable_virtual_scroll': False,
                'error': str(e)
            }
    
    def get_visible_range(self, 
                         scroll_top: int,
                         container_height: int,
                         item_height: int,
                         total_count: int,
                         buffer_size: Optional[int] = None) -> Dict[str, Any]:
        """
        获取可见范围
        
        Args:
            scroll_top: 滚动位置
            container_height: 容器高度
            item_height: 项目高度
            total_count: 总项目数
            buffer_size: 缓冲区大小
            
        Returns:
            可见范围信息
        """
        try:
            if buffer_size is None:
                buffer_size = self.buffer_size
            
            # 计算可见项目范围
            visible_start = math.floor(scroll_top / item_height)
            visible_end = math.ceil((scroll_top + container_height) / item_height)
            
            # 添加缓冲区
            render_start = max(0, visible_start - buffer_size)
            render_end = min(total_count, visible_end + buffer_size)
            
            # 计算偏移量
            offset_y = render_start * item_height
            
            # 计算可见项目数
            visible_count = visible_end - visible_start
            render_count = render_end - render_start
            
            range_info = {
                'visible_start': visible_start,
                'visible_end': visible_end,
                'render_start': render_start,
                'render_end': render_end,
                'visible_count': visible_count,
                'render_count': render_count,
                'offset_y': offset_y,
                'scroll_top': scroll_top,
                'is_at_top': scroll_top <= 0,
                'is_at_bottom': scroll_top + container_height >= total_count * item_height,
                'scroll_percentage': round((scroll_top / (total_count * item_height - container_height)) * 100, 2) if total_count * item_height > container_height else 0
            }
            
            return range_info
            
        except Exception as e:
            self.logger.error(f"获取可见范围失败: {str(e)}")
            return {
                'visible_start': 0,
                'visible_end': 0,
                'render_start': 0,
                'render_end': 0,
                'error': str(e)
            }
    
    def get_virtual_data(self, 
                        data_source: str,
                        data: List[Dict[str, Any]],
                        start_index: int,
                        end_index: int,
                        enable_cache: bool = True) -> Dict[str, Any]:
        """
        获取虚拟滚动数据
        
        Args:
            data_source: 数据源标识
            data: 完整数据列表
            start_index: 开始索引
            end_index: 结束索引
            enable_cache: 是否启用缓存
            
        Returns:
            虚拟滚动数据
        """
        try:
            total_count = len(data)
            
            # 确保索引范围有效
            start_index = max(0, min(start_index, total_count))
            end_index = max(start_index, min(end_index, total_count))
            
            # 生成缓存键
            cache_key = f"{data_source}_{start_index}_{end_index}" if enable_cache else None
            
            # 检查缓存
            if enable_cache and cache_key:
                with self._cache_lock:
                    cached_data = self._data_cache.get(cache_key)
                    if cached_data:
                        cached_data['cache_hit'] = True
                        cached_data['retrieved_at'] = datetime.now().isoformat()
                        return cached_data
            
            # 获取数据切片
            slice_data = data[start_index:end_index]
            
            # 构建返回数据
            virtual_data = {
                'data_source': data_source,
                'data': slice_data,
                'start_index': start_index,
                'end_index': end_index,
                'count': len(slice_data),
                'total_count': total_count,
                'has_more_before': start_index > 0,
                'has_more_after': end_index < total_count,
                'cache_hit': False,
                'retrieved_at': datetime.now().isoformat()
            }
            
            # 缓存数据
            if enable_cache and cache_key:
                with self._cache_lock:
                    # 限制缓存大小
                    if len(self._data_cache) >= self.cache_size:
                        # 删除最旧的缓存项
                        oldest_key = next(iter(self._data_cache))
                        del self._data_cache[oldest_key]
                    
                    self._data_cache[cache_key] = virtual_data.copy()
            
            return virtual_data
            
        except Exception as e:
            self.logger.error(f"获取虚拟滚动数据失败: {str(e)}")
            return {
                'data_source': data_source,
                'data': [],
                'start_index': start_index,
                'end_index': start_index,
                'count': 0,
                'total_count': 0,
                'error': str(e)
            }
    
    def calculate_scroll_position(self, 
                                target_index: int,
                                item_height: int,
                                container_height: int,
                                position: str = 'top') -> Dict[str, Any]:
        """
        计算滚动位置
        
        Args:
            target_index: 目标索引
            item_height: 项目高度
            container_height: 容器高度
            position: 位置 ('top', 'center', 'bottom')
            
        Returns:
            滚动位置信息
        """
        try:
            target_y = target_index * item_height
            
            if position == 'center':
                scroll_top = target_y - (container_height / 2) + (item_height / 2)
            elif position == 'bottom':
                scroll_top = target_y - container_height + item_height
            else:  # 'top'
                scroll_top = target_y
            
            # 确保滚动位置有效
            scroll_top = max(0, scroll_top)
            
            return {
                'target_index': target_index,
                'target_y': target_y,
                'scroll_top': scroll_top,
                'position': position,
                'is_valid': True
            }
            
        except Exception as e:
            self.logger.error(f"计算滚动位置失败: {str(e)}")
            return {
                'target_index': target_index,
                'scroll_top': 0,
                'is_valid': False,
                'error': str(e)
            }
    
    def create_dynamic_height_config(self, 
                                   data: List[Dict[str, Any]],
                                   height_calculator: Callable[[Dict[str, Any]], int]) -> Dict[str, Any]:
        """
        创建动态高度配置
        
        Args:
            data: 数据列表
            height_calculator: 高度计算函数
            
        Returns:
            动态高度配置
        """
        try:
            heights = []
            total_height = 0
            
            # 计算每个项目的高度
            for i, item in enumerate(data):
                try:
                    height = height_calculator(item)
                    heights.append(height)
                    total_height += height
                except Exception as e:
                    self.logger.warning(f"计算项目高度失败，索引: {i}, 错误: {str(e)}")
                    heights.append(self.default_item_height)
                    total_height += self.default_item_height
            
            # 计算累积高度（用于快速定位）
            cumulative_heights = [0]
            for height in heights:
                cumulative_heights.append(cumulative_heights[-1] + height)
            
            # 计算统计信息
            avg_height = total_height / len(heights) if heights else self.default_item_height
            min_height = min(heights) if heights else self.default_item_height
            max_height = max(heights) if heights else self.default_item_height
            
            config = {
                'total_count': len(data),
                'heights': heights,
                'cumulative_heights': cumulative_heights,
                'total_height': total_height,
                'statistics': {
                    'avg_height': round(avg_height, 2),
                    'min_height': min_height,
                    'max_height': max_height,
                    'height_variance': round(max_height - min_height, 2)
                },
                'enable_dynamic_height': True,
                'created_at': datetime.now().isoformat()
            }
            
            self.logger.debug(f"动态高度配置创建完成，总项目: {len(data)}, "
                            f"平均高度: {avg_height:.2f}px, 总高度: {total_height}px")
            
            return config
            
        except Exception as e:
            self.logger.error(f"创建动态高度配置失败: {str(e)}")
            return {
                'total_count': len(data) if data else 0,
                'enable_dynamic_height': False,
                'error': str(e)
            }
    
    def get_dynamic_visible_range(self, 
                                scroll_top: int,
                                container_height: int,
                                cumulative_heights: List[int],
                                buffer_size: Optional[int] = None) -> Dict[str, Any]:
        """
        获取动态高度的可见范围
        
        Args:
            scroll_top: 滚动位置
            container_height: 容器高度
            cumulative_heights: 累积高度列表
            buffer_size: 缓冲区大小
            
        Returns:
            可见范围信息
        """
        try:
            if buffer_size is None:
                buffer_size = self.buffer_size
            
            total_count = len(cumulative_heights) - 1
            
            # 使用二分查找找到可见范围
            visible_start = self._binary_search_index(cumulative_heights, scroll_top)
            visible_end = self._binary_search_index(cumulative_heights, scroll_top + container_height)
            
            # 添加缓冲区
            render_start = max(0, visible_start - buffer_size)
            render_end = min(total_count, visible_end + buffer_size)
            
            # 计算偏移量
            offset_y = cumulative_heights[render_start] if render_start < len(cumulative_heights) else 0
            
            range_info = {
                'visible_start': visible_start,
                'visible_end': visible_end,
                'render_start': render_start,
                'render_end': render_end,
                'visible_count': visible_end - visible_start,
                'render_count': render_end - render_start,
                'offset_y': offset_y,
                'scroll_top': scroll_top,
                'is_at_top': scroll_top <= 0,
                'is_at_bottom': scroll_top + container_height >= cumulative_heights[-1],
                'total_height': cumulative_heights[-1] if cumulative_heights else 0
            }
            
            return range_info
            
        except Exception as e:
            self.logger.error(f"获取动态可见范围失败: {str(e)}")
            return {
                'visible_start': 0,
                'visible_end': 0,
                'render_start': 0,
                'render_end': 0,
                'error': str(e)
            }
    
    def _binary_search_index(self, cumulative_heights: List[int], target: int) -> int:
        """
        二分查找索引
        
        Args:
            cumulative_heights: 累积高度列表
            target: 目标值
            
        Returns:
            索引
        """
        left, right = 0, len(cumulative_heights) - 1
        
        while left < right:
            mid = (left + right) // 2
            if cumulative_heights[mid] < target:
                left = mid + 1
            else:
                right = mid
        
        return max(0, left - 1)
    
    def _calculate_scrollbar_config(self, 
                                  total_height: int,
                                  container_height: int,
                                  item_height: int) -> Dict[str, Any]:
        """
        计算滚动条配置
        
        Args:
            total_height: 总高度
            container_height: 容器高度
            item_height: 项目高度
            
        Returns:
            滚动条配置
        """
        try:
            # 计算滚动条高度比例
            scrollbar_height_ratio = container_height / total_height if total_height > 0 else 1
            scrollbar_height_ratio = min(1, scrollbar_height_ratio)
            
            # 计算滚动条高度（像素）
            scrollbar_height = container_height * scrollbar_height_ratio
            
            # 计算滚动步长
            scroll_step = item_height
            page_scroll_step = container_height - item_height
            
            return {
                'height_ratio': round(scrollbar_height_ratio, 4),
                'height_px': round(scrollbar_height, 2),
                'scroll_step': scroll_step,
                'page_scroll_step': page_scroll_step,
                'total_height': total_height,
                'container_height': container_height,
                'is_scrollable': total_height > container_height
            }
            
        except Exception as e:
            self.logger.error(f"计算滚动条配置失败: {str(e)}")
            return {
                'height_ratio': 1,
                'height_px': container_height,
                'is_scrollable': False,
                'error': str(e)
            }
    
    def clear_cache(self, data_source: Optional[str] = None):
        """
        清理缓存
        
        Args:
            data_source: 数据源标识，为None时清理所有缓存
        """
        try:
            with self._cache_lock:
                if data_source:
                    # 清理特定数据源的缓存
                    keys_to_remove = [key for key in self._data_cache.keys() if key.startswith(data_source)]
                    for key in keys_to_remove:
                        del self._data_cache[key]
                    self.logger.info(f"清理数据源缓存: {data_source}, 清理项目数: {len(keys_to_remove)}")
                else:
                    # 清理所有缓存
                    cache_count = len(self._data_cache)
                    self._data_cache.clear()
                    self.logger.info(f"清理所有缓存，清理项目数: {cache_count}")
                    
        except Exception as e:
            self.logger.error(f"清理缓存失败: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        try:
            with self._cache_lock:
                cache_count = len(self._data_cache)
                
                # 按数据源分组统计
                source_stats = {}
                for key in self._data_cache.keys():
                    source = key.split('_')[0] if '_' in key else 'unknown'
                    if source not in source_stats:
                        source_stats[source] = 0
                    source_stats[source] += 1
                
                return {
                    'total_cached_items': cache_count,
                    'cache_size_limit': self.cache_size,
                    'cache_usage_ratio': round(cache_count / self.cache_size, 4) if self.cache_size > 0 else 0,
                    'source_distribution': source_stats,
                    'memory_estimate_kb': cache_count * 2,  # 假设每个缓存项约2KB
                    'updated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"获取缓存统计信息失败: {str(e)}")
            return {
                'total_cached_items': 0,
                'error': str(e)
            }


def main():
    """测试虚拟滚动管理器功能"""
    logger = EnhancedLogger("virtual_scroll_manager_test")
    
    try:
        print("=== 虚拟滚动管理器测试 ===")
        
        # 创建测试数据
        test_data = []
        for i in range(1000):
            test_data.append({
                'id': i + 1,
                'name': f'项目_{i + 1}',
                'description': f'这是第{i + 1}个项目的描述' + ('，内容较长' * (i % 3)),
                'category': f'分类_{i % 10}',
                'value': i * 10
            })
        
        # 创建虚拟滚动管理器
        scroll_manager = VirtualScrollManager(
            default_item_height=50,
            default_container_height=500,
            buffer_size=3,
            logger=logger
        )
        
        # 测试创建虚拟滚动配置
        print(f"\n1. 测试创建虚拟滚动配置（总数据: {len(test_data)} 条）")
        config = scroll_manager.create_virtual_scroll_config(
            data_source='test_data',
            total_count=len(test_data),
            item_height=50,
            container_height=500
        )
        print(f"配置信息: 启用虚拟滚动={config['enable_virtual_scroll']}, "
              f"可见项目={config['visible_count']}, 渲染项目={config['render_count']}")
        print(f"性能优化: {config['performance']}")
        
        # 测试获取可见范围
        print(f"\n2. 测试获取可见范围")
        scroll_positions = [0, 1000, 5000, 10000]
        for scroll_top in scroll_positions:
            range_info = scroll_manager.get_visible_range(
                scroll_top=scroll_top,
                container_height=500,
                item_height=50,
                total_count=len(test_data)
            )
            print(f"滚动位置 {scroll_top}: 渲染范围 {range_info['render_start']}-{range_info['render_end']}, "
                  f"滚动百分比 {range_info['scroll_percentage']}%")
        
        # 测试获取虚拟数据
        print(f"\n3. 测试获取虚拟数据")
        virtual_data = scroll_manager.get_virtual_data(
            data_source='test_data',
            data=test_data,
            start_index=100,
            end_index=120
        )
        print(f"虚拟数据: 起始索引={virtual_data['start_index']}, "
              f"数据量={virtual_data['count']}, 缓存命中={virtual_data['cache_hit']}")
        
        # 测试缓存功能
        print(f"\n4. 测试缓存功能")
        # 再次获取相同数据
        virtual_data2 = scroll_manager.get_virtual_data(
            data_source='test_data',
            data=test_data,
            start_index=100,
            end_index=120
        )
        print(f"第二次获取: 缓存命中={virtual_data2['cache_hit']}")
        
        # 测试计算滚动位置
        print(f"\n5. 测试计算滚动位置")
        positions = ['top', 'center', 'bottom']
        target_index = 500
        for position in positions:
            scroll_pos = scroll_manager.calculate_scroll_position(
                target_index=target_index,
                item_height=50,
                container_height=500,
                position=position
            )
            print(f"滚动到索引 {target_index} ({position}): 滚动位置={scroll_pos['scroll_top']}")
        
        # 测试动态高度配置
        print(f"\n6. 测试动态高度配置")
        
        def height_calculator(item):
            # 根据描述长度计算高度
            base_height = 50
            extra_height = len(item.get('description', '')) // 20 * 10
            return base_height + extra_height
        
        dynamic_config = scroll_manager.create_dynamic_height_config(
            data=test_data[:100],  # 只测试前100项
            height_calculator=height_calculator
        )
        print(f"动态高度统计: {dynamic_config['statistics']}")
        
        # 测试动态可见范围
        print(f"\n7. 测试动态可见范围")
        if 'cumulative_heights' in dynamic_config:
            dynamic_range = scroll_manager.get_dynamic_visible_range(
                scroll_top=1000,
                container_height=500,
                cumulative_heights=dynamic_config['cumulative_heights']
            )
            print(f"动态可见范围: {dynamic_range['render_start']}-{dynamic_range['render_end']}, "
                  f"偏移量={dynamic_range['offset_y']}")
        
        # 测试缓存统计
        print(f"\n8. 测试缓存统计")
        cache_stats = scroll_manager.get_cache_stats()
        print(f"缓存统计: {cache_stats}")
        
        # 测试清理缓存
        print(f"\n9. 测试清理缓存")
        scroll_manager.clear_cache('test_data')
        cache_stats_after = scroll_manager.get_cache_stats()
        print(f"清理后缓存统计: {cache_stats_after}")
        
        print("\n虚拟滚动管理器测试完成！")
        
    except Exception as e:
        logger.error(f"虚拟滚动管理器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()