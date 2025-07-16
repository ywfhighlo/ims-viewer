#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据操作包装器
在数据变更操作时自动触发缓存失效
"""

import sys
import os
from typing import Dict, Any, List, Optional, Callable
from functools import wraps

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.cache_invalidation import get_invalidation_manager


def invalidate_cache_on_change(collection_name: str, operation: str = 'update'):
    """
    装饰器：在数据操作后自动失效相关缓存
    
    Args:
        collection_name: 数据库集合名称
        operation: 操作类型 ('insert', 'update', 'delete')
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行原始函数
            result = func(*args, **kwargs)
            
            try:
                # 获取缓存失效管理器
                invalidation_manager = get_invalidation_manager()
                
                # 失效相关缓存
                invalidated_count = invalidation_manager.invalidate_by_collection(
                    collection_name, operation
                )
                
                # 记录日志
                logger = EnhancedLogger("data_operation_wrapper")
                logger.info(f"数据操作完成，自动失效缓存: {collection_name} - {operation}, 失效条目数: {invalidated_count}")
                
            except Exception as e:
                # 缓存失效失败不应影响主要业务逻辑
                logger = EnhancedLogger("data_operation_wrapper")
                logger.error(f"自动缓存失效失败: {collection_name} - {operation}, 错误: {str(e)}")
            
            return result
        
        return wrapper
    return decorator


class DataOperationWrapper:
    """数据操作包装器类"""
    
    def __init__(self, logger: Optional[EnhancedLogger] = None):
        """
        初始化数据操作包装器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or EnhancedLogger("data_operation_wrapper")
        self.invalidation_manager = get_invalidation_manager()
    
    def execute_with_cache_invalidation(self, 
                                      operation_func: Callable,
                                      collection_name: str,
                                      operation_type: str = 'update',
                                      *args, **kwargs) -> Any:
        """
        执行数据操作并自动失效缓存
        
        Args:
            operation_func: 数据操作函数
            collection_name: 数据库集合名称
            operation_type: 操作类型
            *args, **kwargs: 传递给操作函数的参数
            
        Returns:
            操作函数的返回值
        """
        try:
            # 执行数据操作
            result = operation_func(*args, **kwargs)
            
            # 失效相关缓存
            invalidated_count = self.invalidation_manager.invalidate_by_collection(
                collection_name, operation_type
            )
            
            self.logger.info(f"数据操作完成，自动失效缓存: {collection_name} - {operation_type}, 失效条目数: {invalidated_count}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"数据操作失败: {collection_name} - {operation_type}, 错误: {str(e)}")
            raise
    
    def batch_execute_with_cache_invalidation(self, 
                                            operations: List[Dict[str, Any]]) -> List[Any]:
        """
        批量执行数据操作并自动失效缓存
        
        Args:
            operations: 操作列表，每个操作包含:
                - func: 操作函数
                - collection: 集合名称
                - operation_type: 操作类型
                - args: 位置参数
                - kwargs: 关键字参数
                
        Returns:
            操作结果列表
        """
        results = []
        affected_collections = set()
        
        try:
            # 执行所有操作
            for operation in operations:
                func = operation['func']
                args = operation.get('args', ())
                kwargs = operation.get('kwargs', {})
                
                result = func(*args, **kwargs)
                results.append(result)
                
                # 记录受影响的集合
                collection = operation.get('collection')
                if collection:
                    affected_collections.add(collection)
            
            # 批量失效缓存
            total_invalidated = 0
            for collection in affected_collections:
                invalidated_count = self.invalidation_manager.invalidate_by_collection(
                    collection, 'batch_update'
                )
                total_invalidated += invalidated_count
            
            self.logger.info(f"批量数据操作完成，失效缓存: {len(affected_collections)} 个集合, 总计失效条目数: {total_invalidated}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"批量数据操作失败: {str(e)}")
            raise


# 示例数据操作函数（模拟）
def insert_purchase_record(supplier_name: str, amount: float, date: str) -> Dict[str, Any]:
    """
    模拟插入采购记录
    
    Args:
        supplier_name: 供应商名称
        amount: 采购金额
        date: 采购日期
        
    Returns:
        插入结果
    """
    # 这里应该是实际的数据库插入操作
    record = {
        'supplier_name': supplier_name,
        'amount': amount,
        'inbound_date': date,
        'created_at': '2025-07-16 10:20:00'
    }
    
    print(f"模拟插入采购记录: {record}")
    return record


def update_supplier_info(supplier_name: str, contact_person: str) -> Dict[str, Any]:
    """
    模拟更新供应商信息
    
    Args:
        supplier_name: 供应商名称
        contact_person: 联系人
        
    Returns:
        更新结果
    """
    # 这里应该是实际的数据库更新操作
    update_info = {
        'supplier_name': supplier_name,
        'contact_person': contact_person,
        'updated_at': '2025-07-16 10:20:00'
    }
    
    print(f"模拟更新供应商信息: {update_info}")
    return update_info


def main():
    """测试数据操作包装器功能"""
    logger = EnhancedLogger("data_operation_wrapper_test")
    
    try:
        print("=== 数据操作包装器测试 ===")
        
        # 创建数据操作包装器
        wrapper = DataOperationWrapper(logger)
        
        # 测试单个操作
        print("\n1. 测试单个数据操作")
        result = wrapper.execute_with_cache_invalidation(
            insert_purchase_record,
            'purchase_inbound',
            'insert',
            '测试供应商',
            1000.0,
            '2025-07-16'
        )
        print(f"操作结果: {result}")
        
        # 测试装饰器方式
        print("\n2. 测试装饰器方式")
        
        @invalidate_cache_on_change('suppliers', 'update')
        def decorated_update_supplier(name: str, contact: str):
            return update_supplier_info(name, contact)
        
        result = decorated_update_supplier('测试供应商', '张三')
        print(f"装饰器操作结果: {result}")
        
        # 测试批量操作
        print("\n3. 测试批量数据操作")
        batch_operations = [
            {
                'func': insert_purchase_record,
                'collection': 'purchase_inbound',
                'operation_type': 'insert',
                'args': ('供应商A', 500.0, '2025-07-16'),
                'kwargs': {}
            },
            {
                'func': insert_purchase_record,
                'collection': 'purchase_inbound',
                'operation_type': 'insert',
                'args': ('供应商B', 800.0, '2025-07-16'),
                'kwargs': {}
            },
            {
                'func': update_supplier_info,
                'collection': 'suppliers',
                'operation_type': 'update',
                'args': ('供应商A', '李四'),
                'kwargs': {}
            }
        ]
        
        batch_results = wrapper.batch_execute_with_cache_invalidation(batch_operations)
        print(f"批量操作结果数量: {len(batch_results)}")
        
        print("\n数据操作包装器测试完成！")
        
    except Exception as e:
        logger.error(f"数据操作包装器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()