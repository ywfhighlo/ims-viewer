#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建进销存管理所需的数据库集合和索引
"""

import sys
import logging
from datetime import datetime
import traceback

# 添加项目根目录到Python路径
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from scripts.db_connection import get_database_connection
from scripts.enhanced_logger import get_logger

# 设置日志
logger = get_logger('create_inventory_tables')

def create_inventory_collections():
    """创建进销存管理所需的MongoDB集合和索引"""
    try:
        # 使用MongoDB连接
        db = get_database_connection()
        
        logger.info("开始创建进销存管理数据库集合和索引...")
        
        # 1. 采购订单集合
        purchase_orders = db['purchase_orders']
        purchase_orders.create_index('order_no', unique=True)
        purchase_orders.create_index('supplier_name')
        purchase_orders.create_index('order_date')
        purchase_orders.create_index('status')
        logger.info("✓ 采购订单集合索引创建完成")
        
        # 2. 采购订单明细集合
        purchase_order_details = db['purchase_order_details']
        purchase_order_details.create_index('order_id')
        purchase_order_details.create_index('material_code')
        logger.info("✓ 采购订单明细集合索引创建完成")
        
        # 3. 销售订单集合
        sales_orders = db['sales_orders']
        sales_orders.create_index('order_no', unique=True)
        sales_orders.create_index('customer_name')
        sales_orders.create_index('order_date')
        sales_orders.create_index('status')
        logger.info("✓ 销售订单集合索引创建完成")
        
        # 4. 销售订单明细集合
        sales_order_details = db['sales_order_details']
        sales_order_details.create_index('order_id')
        sales_order_details.create_index('material_code')
        logger.info("✓ 销售订单明细集合索引创建完成")
        
        # 5. 库存汇总集合
        inventory_summary = db['inventory_summary']
        inventory_summary.create_index([('material_code', 1), ('warehouse', 1)], unique=True)
        inventory_summary.create_index('material_code')
        inventory_summary.create_index('warehouse')
        inventory_summary.create_index('current_stock')
        logger.info("✓ 库存汇总集合索引创建完成")
        
        # 6. 库存调整记录集合
        inventory_adjustments = db['inventory_adjustments']
        inventory_adjustments.create_index('material_code')
        inventory_adjustments.create_index('warehouse')
        inventory_adjustments.create_index('created_at')
        logger.info("✓ 库存调整记录集合索引创建完成")
        
        # 7. 库存转移记录集合
        inventory_transfers = db['inventory_transfers']
        inventory_transfers.create_index('material_code')
        inventory_transfers.create_index('from_warehouse')
        inventory_transfers.create_index('to_warehouse')
        inventory_transfers.create_index('created_at')
        logger.info("✓ 库存转移记录集合索引创建完成")
        
        # 8. 库存盘点记录集合
        inventory_counts = db['inventory_counts']
        inventory_counts.create_index('material_code')
        inventory_counts.create_index('warehouse')
        inventory_counts.create_index('created_at')
        logger.info("✓ 库存盘点记录集合索引创建完成")
        
        # 9. 入库记录集合
        inbound_records = db['inbound_records']
        inbound_records.create_index('record_no', unique=True)
        inbound_records.create_index('material_code')
        inbound_records.create_index('warehouse')
        inbound_records.create_index('inbound_date')
        logger.info("✓ 入库记录集合索引创建完成")
        
        # 10. 出库记录集合
        outbound_records = db['outbound_records']
        outbound_records.create_index('record_no', unique=True)
        outbound_records.create_index('material_code')
        outbound_records.create_index('warehouse')
        outbound_records.create_index('outbound_date')
        logger.info("✓ 出库记录集合索引创建完成")
        
        logger.info("所有进销存管理集合和索引创建完成！")
        
        # 初始化示例数据
        init_sample_data(db)
        
        return True
        
    except Exception as e:
        logger.error(f"创建进销存管理集合失败: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

def init_sample_data(db):
    """初始化示例数据"""
    try:
        logger.info("开始初始化示例数据...")
        
        # 检查是否已有数据
        if db['purchase_orders'].count_documents({}) > 0:
            logger.info("数据库中已有数据，跳过示例数据初始化")
            return
        
        # 示例供应商数据
        suppliers = [
            {"name": "北京科技有限公司", "contact": "张经理", "phone": "010-12345678"},
            {"name": "上海工业集团", "contact": "李总", "phone": "021-87654321"},
            {"name": "深圳电子科技", "contact": "王主管", "phone": "0755-11223344"}
        ]
        
        # 示例客户数据
        customers = [
            {"name": "广州制造公司", "contact": "陈经理", "phone": "020-55667788"},
            {"name": "杭州贸易有限公司", "contact": "刘总", "phone": "0571-99887766"},
            {"name": "成都技术开发", "contact": "赵主任", "phone": "028-33445566"}
        ]
        
        # 示例库存数据
        sample_inventory = [
            {
                "material_code": "MAT001",
                "material_name": "钢材",
                "specification": "Q235 20*30mm",
                "unit": "吨",
                "warehouse": "主仓库",
                "current_stock": 100.5,
                "safety_stock": 20.0,
                "unit_price": 4500.00,
                "last_updated": datetime.now()
            },
            {
                "material_code": "MAT002",
                "material_name": "铝合金",
                "specification": "6061-T6 15*25mm",
                "unit": "公斤",
                "warehouse": "主仓库",
                "current_stock": 500.0,
                "safety_stock": 100.0,
                "unit_price": 25.50,
                "last_updated": datetime.now()
            },
            {
                "material_code": "MAT003",
                "material_name": "电子元件",
                "specification": "电阻 1KΩ",
                "unit": "个",
                "warehouse": "电子仓库",
                "current_stock": 10000.0,
                "safety_stock": 2000.0,
                "unit_price": 0.05,
                "last_updated": datetime.now()
            }
        ]
        
        # 插入示例数据
        if sample_inventory:
            db['inventory_summary'].insert_many(sample_inventory)
            logger.info(f"✓ 插入了 {len(sample_inventory)} 条库存示例数据")
        
        logger.info("示例数据初始化完成！")
        
    except Exception as e:
        logger.error(f"初始化示例数据失败: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")

def main():
    """主函数"""
    try:
        print("IMS Viewer - 进销存管理数据库初始化")
        print("=" * 50)
        
        success = create_inventory_collections()
        
        if success:
            print("\n✅ 进销存管理数据库初始化成功！")
            print("\n已创建的集合:")
            print("  - purchase_orders (采购订单)")
            print("  - purchase_order_details (采购订单明细)")
            print("  - sales_orders (销售订单)")
            print("  - sales_order_details (销售订单明细)")
            print("  - inventory_summary (库存汇总)")
            print("  - inventory_adjustments (库存调整记录)")
            print("  - inventory_transfers (库存转移记录)")
            print("  - inventory_counts (库存盘点记录)")
            print("  - inbound_records (入库记录)")
            print("  - outbound_records (出库记录)")
            print("\n现在可以开始使用进销存管理功能了！")
        else:
            print("\n❌ 进销存管理数据库初始化失败！")
            print("请检查日志文件获取详细错误信息。")
            
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        logger.error(f"主函数执行失败: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")

if __name__ == "__main__":
    main()