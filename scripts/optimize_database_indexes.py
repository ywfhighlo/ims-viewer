#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库索引优化脚本
为业务报表查询创建复合索引，提升查询性能
"""

import sys
import os
from typing import Dict, List, Tuple

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.db_connection import get_database_connection

def create_optimized_indexes():
    """
    创建优化的数据库索引，特别针对业务报表查询
    """
    logger = EnhancedLogger("index_optimizer")
    
    try:
        db = get_database_connection()
        logger.info("开始创建优化索引...")
        
        # 定义索引配置
        # 格式: {集合名: [(字段列表, 索引选项), ...]}
        index_configs = {
            # 供应商表
            'suppliers': [
                (['supplier_name'], {'unique': False}),
                (['supplier_code'], {'unique': True, 'sparse': True}),
            ],
            
            # 客户表
            'customers': [
                (['customer_name'], {'unique': False}),
                (['customer_code'], {'unique': True, 'sparse': True}),
            ],
            
            # 物料表
            'materials': [
                (['material_code'], {'unique': True}),
                (['material_name'], {'unique': False}),
            ],
            
            # 采购入库表 - 供应商对账表的关键查询
            'purchase_inbound': [
                # 单字段索引
                (['supplier_name'], {'unique': False}),
                (['inbound_date'], {'unique': False}),
                (['material_code'], {'unique': False}),
                
                # 复合索引 - 供应商对账表优化
                (['supplier_name', 'inbound_date'], {'unique': False}),
                (['supplier_name', 'amount'], {'unique': False}),
                
                # 采购报表优化
                (['material_code', 'inbound_date'], {'unique': False}),
                (['material_name', 'inbound_date'], {'unique': False}),
            ],
            
            # 付款明细表 - 供应商对账表的关键查询
            'payment_details': [
                # 单字段索引
                (['supplier_name'], {'unique': False}),
                (['payment_date'], {'unique': False}),
                
                # 复合索引 - 供应商对账表优化
                (['supplier_name', 'payment_date'], {'unique': False}),
                (['supplier_name', 'amount'], {'unique': False}),
            ],
            
            # 销售出库表 - 客户对账表和销售报表优化
            'sales_outbound': [
                # 单字段索引
                (['customer_name'], {'unique': False}),
                (['outbound_date'], {'unique': False}),
                (['material_code'], {'unique': False}),
                
                # 复合索引 - 客户对账表优化
                (['customer_name', 'outbound_date'], {'unique': False}),
                (['customer_name', 'outbound_amount'], {'unique': False}),
                
                # 销售报表优化
                (['material_code', 'outbound_date'], {'unique': False}),
                (['material_name', 'outbound_date'], {'unique': False}),
            ],
            
            # 收款明细表 - 客户对账表优化
            'receipt_details': [
                # 单字段索引
                (['customer_name'], {'unique': False}),
                (['receipt_date'], {'unique': False}),
                
                # 复合索引 - 客户对账表优化
                (['customer_name', 'receipt_date'], {'unique': False}),
                (['customer_name', 'amount'], {'unique': False}),
            ],
            
            # 库存统计表 - 库存报表优化
            'inventory_stats': [
                (['material_code'], {'unique': False}),
                (['material_name'], {'unique': False}),
                (['material_code', 'current_stock'], {'unique': False}),
            ],
        }
        
        # 创建索引
        total_created = 0
        total_failed = 0
        
        for collection_name, indexes in index_configs.items():
            if collection_name not in db.list_collection_names():
                logger.warning(f"集合 {collection_name} 不存在，跳过索引创建")
                continue
                
            collection = db[collection_name]
            logger.info(f"\n为集合 {collection_name} 创建索引...")
            
            for fields, options in indexes:
                try:
                    # 构建索引规范
                    if len(fields) == 1:
                        index_spec = fields[0]
                        index_name = f"{fields[0]}_1"
                    else:
                        index_spec = [(field, 1) for field in fields]
                        index_name = "_".join(fields) + "_compound"
                    
                    # 检查索引是否已存在
                    existing_indexes = collection.list_indexes()
                    index_exists = False
                    
                    for existing_index in existing_indexes:
                        if existing_index.get('name') == index_name:
                            index_exists = True
                            break
                    
                    if index_exists:
                        logger.info(f"  ✓ 索引 {index_name} 已存在")
                        continue
                    
                    # 创建索引
                    collection.create_index(
                        index_spec,
                        name=index_name,
                        background=True,  # 后台创建，不阻塞其他操作
                        **options
                    )
                    
                    logger.info(f"  ✓ 创建索引: {index_name}")
                    total_created += 1
                    
                except Exception as e:
                    logger.error(f"  ✗ 创建索引失败 {fields}: {str(e)}")
                    total_failed += 1
        
        # 输出统计信息
        logger.info(f"\n索引创建完成:")
        logger.info(f"  成功创建: {total_created} 个")
        logger.info(f"  创建失败: {total_failed} 个")
        
        # 显示所有集合的索引信息
        logger.info("\n当前数据库索引概览:")
        for collection_name in db.list_collection_names():
            if collection_name.startswith('system.'):
                continue
                
            collection = db[collection_name]
            indexes = list(collection.list_indexes())
            logger.info(f"  {collection_name}: {len(indexes)} 个索引")
            
            for index in indexes:
                index_name = index.get('name', 'unknown')
                if index_name != '_id_':  # 跳过默认的_id索引
                    logger.info(f"    - {index_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"创建索引失败: {str(e)}")
        return False

def analyze_query_performance():
    """
    分析查询性能，提供优化建议
    """
    logger = EnhancedLogger("query_analyzer")
    
    try:
        db = get_database_connection()
        logger.info("分析查询性能...")
        
        # 分析供应商对账表相关的查询
        performance_tests = [
            {
                'name': '供应商对账表 - 采购数据聚合',
                'collection': 'purchase_inbound',
                'pipeline': [
                    {'$match': {'supplier_name': {'$exists': True}}},
                    {'$group': {
                        '_id': '$supplier_name',
                        'total_amount': {'$sum': '$amount'},
                        'count': {'$sum': 1}
                    }}
                ]
            },
            {
                'name': '供应商对账表 - 付款数据聚合',
                'collection': 'payment_details',
                'pipeline': [
                    {'$match': {'supplier_name': {'$exists': True}}},
                    {'$group': {
                        '_id': '$supplier_name',
                        'total_amount': {'$sum': '$amount'},
                        'count': {'$sum': 1}
                    }}
                ]
            }
        ]
        
        for test in performance_tests:
            collection = db[test['collection']]
            
            # 执行explain来分析查询计划
            try:
                explain_result = collection.aggregate(
                    test['pipeline'],
                    explain=True
                )
                
                logger.info(f"\n查询: {test['name']}")
                logger.info(f"集合: {test['collection']}")
                
                # 简化的性能分析
                stages = explain_result.get('stages', [])
                if stages:
                    for i, stage in enumerate(stages):
                        stage_name = list(stage.keys())[0] if stage else 'unknown'
                        logger.info(f"  阶段 {i+1}: {stage_name}")
                        
                        # 检查是否使用了索引
                        if '$cursor' in stage:
                            cursor_info = stage['$cursor']
                            query_planner = cursor_info.get('queryPlanner', {})
                            winning_plan = query_planner.get('winningPlan', {})
                            
                            if 'IXSCAN' in str(winning_plan):
                                logger.info(f"    ✓ 使用索引扫描")
                            elif 'COLLSCAN' in str(winning_plan):
                                logger.warning(f"    ⚠ 使用集合扫描（可能需要优化）")
                
            except Exception as e:
                logger.warning(f"分析查询 {test['name']} 失败: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"性能分析失败: {str(e)}")
        return False

def main():
    """
    主函数
    """
    logger = EnhancedLogger("index_optimizer")
    
    try:
        logger.info("开始数据库索引优化...")
        
        # 创建优化索引
        if create_optimized_indexes():
            logger.info("索引创建成功")
        else:
            logger.error("索引创建失败")
            return False
        
        # 分析查询性能
        if analyze_query_performance():
            logger.info("性能分析完成")
        else:
            logger.warning("性能分析失败")
        
        logger.info("\n优化建议:")
        logger.info("1. 定期监控慢查询日志")
        logger.info("2. 根据实际查询模式调整索引")
        logger.info("3. 考虑对大集合进行分片")
        logger.info("4. 定期维护和重建索引")
        
        return True
        
    except Exception as e:
        logger.error(f"优化过程失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)