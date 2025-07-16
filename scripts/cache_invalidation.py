#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存失效机制
监听数据变更事件，自动失效相关缓存
"""

import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.cache_manager import get_cache_manager


class CacheInvalidationManager:
    """缓存失效管理器"""
    
    def __init__(self, logger: Optional[EnhancedLogger] = None):
        """
        初始化缓存失效管理器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or EnhancedLogger("cache_invalidation")
        self.cache_manager = get_cache_manager()
        
        # 定义数据变更与缓存视图的映射关系
        self.invalidation_rules = {
            'purchase_inbound': [
                'supplier_reconciliation',
                'purchase_report',
                'inventory_report'
            ],
            'payment_details': [
                'supplier_reconciliation'
            ],
            'sales_outbound': [
                'customer_reconciliation',
                'sales_report',
                'inventory_report'
            ],
            'receipt_details': [
                'customer_reconciliation'
            ],
            'inventory_stats': [
                'inventory_report'
            ],
            'suppliers': [
                'supplier_reconciliation',
                'purchase_report'
            ],
            'customers': [
                'customer_reconciliation',
                'sales_report'
            ]
        }
        
        self.logger.info("缓存失效管理器初始化完成")
    
    def invalidate_by_collection(self, collection_name: str, operation: str = 'update') -> int:
        """
        根据集合名称失效相关缓存
        
        Args:
            collection_name: 数据库集合名称
            operation: 操作类型 ('insert', 'update', 'delete')
            
        Returns:
            失效的缓存条目数量
        """
        try:
            self.logger.info(f"开始处理数据变更事件: {collection_name} - {operation}")
            
            # 获取需要失效的视图列表
            affected_views = self.invalidation_rules.get(collection_name, [])
            
            if not affected_views:
                self.logger.debug(f"集合 {collection_name} 没有关联的缓存视图")
                return 0
            
            total_invalidated = 0
            
            # 失效每个相关视图的缓存
            for view_name in affected_views:
                pattern = f"{view_name}*"
                invalidated_count = self.cache_manager.invalidate_cache(pattern)
                total_invalidated += invalidated_count
                
                self.logger.debug(f"视图 {view_name} 失效缓存 {invalidated_count} 个条目")
            
            self.logger.info(f"数据变更处理完成: {collection_name}, 总计失效缓存 {total_invalidated} 个条目")
            return total_invalidated
            
        except Exception as e:
            self.logger.error(f"处理数据变更失效缓存失败: {collection_name}, 错误: {str(e)}")
            return 0
    
    def invalidate_by_view(self, view_name: str) -> int:
        """
        根据视图名称失效缓存
        
        Args:
            view_name: 视图名称
            
        Returns:
            失效的缓存条目数量
        """
        try:
            pattern = f"{view_name}*"
            invalidated_count = self.cache_manager.invalidate_cache(pattern)
            
            self.logger.info(f"手动失效视图缓存: {view_name}, 失效条目数: {invalidated_count}")
            return invalidated_count
            
        except Exception as e:
            self.logger.error(f"手动失效视图缓存失败: {view_name}, 错误: {str(e)}")
            return 0
    
    def invalidate_by_supplier(self, supplier_name: str) -> int:
        """
        根据供应商名称失效相关缓存
        
        Args:
            supplier_name: 供应商名称
            
        Returns:
            失效的缓存条目数量
        """
        try:
            # 失效包含该供应商的所有缓存
            total_invalidated = 0
            
            # 获取所有缓存信息
            cache_info = self.cache_manager.get_cache_info(limit=1000)
            
            for info in cache_info:
                params = info.get('params', {})
                
                # 检查是否包含该供应商
                if (params.get('supplier_name') == supplier_name or
                    info.get('view_name') in ['supplier_reconciliation', 'purchase_report']):
                    
                    cache_key = info.get('cache_key')
                    if cache_key:
                        invalidated = self.cache_manager.invalidate_cache(cache_key)
                        total_invalidated += invalidated
            
            self.logger.info(f"供应商相关缓存失效完成: {supplier_name}, 失效条目数: {total_invalidated}")
            return total_invalidated
            
        except Exception as e:
            self.logger.error(f"供应商缓存失效失败: {supplier_name}, 错误: {str(e)}")
            return 0
    
    def invalidate_by_customer(self, customer_name: str) -> int:
        """
        根据客户名称失效相关缓存
        
        Args:
            customer_name: 客户名称
            
        Returns:
            失效的缓存条目数量
        """
        try:
            # 失效包含该客户的所有缓存
            total_invalidated = 0
            
            # 获取所有缓存信息
            cache_info = self.cache_manager.get_cache_info(limit=1000)
            
            for info in cache_info:
                params = info.get('params', {})
                
                # 检查是否包含该客户
                if (params.get('customer_name') == customer_name or
                    info.get('view_name') in ['customer_reconciliation', 'sales_report']):
                    
                    cache_key = info.get('cache_key')
                    if cache_key:
                        invalidated = self.cache_manager.invalidate_cache(cache_key)
                        total_invalidated += invalidated
            
            self.logger.info(f"客户相关缓存失效完成: {customer_name}, 失效条目数: {total_invalidated}")
            return total_invalidated
            
        except Exception as e:
            self.logger.error(f"客户缓存失效失败: {customer_name}, 错误: {str(e)}")
            return 0
    
    def invalidate_by_date_range(self, start_date: str, end_date: str) -> int:
        """
        根据日期范围失效相关缓存
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            失效的缓存条目数量
        """
        try:
            # 失效包含该日期范围的所有缓存
            total_invalidated = 0
            
            # 获取所有缓存信息
            cache_info = self.cache_manager.get_cache_info(limit=1000)
            
            for info in cache_info:
                params = info.get('params', {})
                
                # 检查日期范围是否重叠
                cache_start = params.get('start_date')
                cache_end = params.get('end_date')
                
                if self._date_ranges_overlap(start_date, end_date, cache_start, cache_end):
                    cache_key = info.get('cache_key')
                    if cache_key:
                        invalidated = self.cache_manager.invalidate_cache(cache_key)
                        total_invalidated += invalidated
            
            self.logger.info(f"日期范围相关缓存失效完成: {start_date} - {end_date}, 失效条目数: {total_invalidated}")
            return total_invalidated
            
        except Exception as e:
            self.logger.error(f"日期范围缓存失效失败: {start_date} - {end_date}, 错误: {str(e)}")
            return 0
    
    def _date_ranges_overlap(self, start1: str, end1: str, start2: Optional[str], end2: Optional[str]) -> bool:
        """
        检查两个日期范围是否重叠
        
        Args:
            start1, end1: 第一个日期范围
            start2, end2: 第二个日期范围
            
        Returns:
            是否重叠
        """
        try:
            # 如果缓存中没有日期限制，则认为重叠
            if not start2 and not end2:
                return True
            
            # 转换为日期对象进行比较
            from datetime import datetime
            
            date1_start = datetime.strptime(start1, '%Y-%m-%d') if start1 else datetime.min
            date1_end = datetime.strptime(end1, '%Y-%m-%d') if end1 else datetime.max
            date2_start = datetime.strptime(start2, '%Y-%m-%d') if start2 else datetime.min
            date2_end = datetime.strptime(end2, '%Y-%m-%d') if end2 else datetime.max
            
            # 检查是否重叠
            return not (date1_end < date2_start or date2_end < date1_start)
            
        except Exception:
            # 日期格式错误时，保守地认为重叠
            return True
    
    def get_invalidation_stats(self) -> Dict[str, Any]:
        """
        获取缓存失效统计信息
        
        Returns:
            失效统计信息
        """
        try:
            cache_stats = self.cache_manager.get_cache_stats()
            
            return {
                'cache_stats': cache_stats,
                'invalidation_rules': self.invalidation_rules,
                'total_rules': len(self.invalidation_rules),
                'total_views': len(set(view for views in self.invalidation_rules.values() for view in views))
            }
            
        except Exception as e:
            self.logger.error(f"获取失效统计信息失败: {str(e)}")
            return {}


# 全局缓存失效管理器实例
_global_invalidation_manager: Optional[CacheInvalidationManager] = None


def get_invalidation_manager() -> CacheInvalidationManager:
    """
    获取全局缓存失效管理器实例（单例模式）
    
    Returns:
        缓存失效管理器实例
    """
    global _global_invalidation_manager
    
    if _global_invalidation_manager is None:
        _global_invalidation_manager = CacheInvalidationManager()
    
    return _global_invalidation_manager


def invalidate_cache_on_data_change(collection_name: str, operation: str = 'update') -> int:
    """
    数据变更时失效缓存的便捷函数
    
    Args:
        collection_name: 数据库集合名称
        operation: 操作类型
        
    Returns:
        失效的缓存条目数量
    """
    invalidation_manager = get_invalidation_manager()
    return invalidation_manager.invalidate_by_collection(collection_name, operation)


def main():
    """测试缓存失效管理器功能"""
    logger = EnhancedLogger("cache_invalidation_test")
    
    try:
        # 创建缓存失效管理器
        invalidation_manager = CacheInvalidationManager(logger)
        
        print("=== 缓存失效管理器测试 ===")
        
        # 测试集合变更失效
        print("\n1. 测试集合变更失效")
        invalidated = invalidation_manager.invalidate_by_collection('purchase_inbound', 'insert')
        print(f"采购入库数据变更失效缓存: {invalidated} 个条目")
        
        # 测试视图失效
        print("\n2. 测试视图失效")
        invalidated = invalidation_manager.invalidate_by_view('supplier_reconciliation')
        print(f"供应商对账表视图失效缓存: {invalidated} 个条目")
        
        # 测试供应商失效
        print("\n3. 测试供应商失效")
        invalidated = invalidation_manager.invalidate_by_supplier('测试供应商')
        print(f"测试供应商相关缓存失效: {invalidated} 个条目")
        
        # 测试日期范围失效
        print("\n4. 测试日期范围失效")
        invalidated = invalidation_manager.invalidate_by_date_range('2024-01-01', '2024-12-31')
        print(f"2024年数据相关缓存失效: {invalidated} 个条目")
        
        # 获取统计信息
        print("\n5. 获取失效统计信息")
        stats = invalidation_manager.get_invalidation_stats()
        print(f"失效规则数: {stats.get('total_rules', 0)}")
        print(f"涉及视图数: {stats.get('total_views', 0)}")
        
        print("\n缓存失效管理器测试完成！")
        
    except Exception as e:
        logger.error(f"缓存失效管理器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()