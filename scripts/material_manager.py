#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料管理模块
负责物料编码的生成和新物料的添加。
"""

import sys
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime

# 导入数据库配置模块
from database_config import get_db_client, get_database_name

# 集合名称
MATERIALS_COLLECTION = "materials"

# 为了向后兼容，保留这些变量
DATABASE_NAME = get_database_name()

def generate_material_code(db, platform, type1, type2, supplier_code):
    """
    根据规则生成唯一的物料编码。
    编码格式: P-XX-XX-XXXX-XXX
    
    Args:
        platform: 物料平台 (P=采购, R=自研)
        type1: 物料类型2 (1=国产, 2=非国产)
        type2: 物料类型3 (1=纯软件, 2=服务器, 3=工控机, 4=配件)
        supplier_code: 供应商编码 (01-99)
    """
    # 验证输入参数
    if platform not in ['P', 'R']:
        raise ValueError("平台代码必须是P或R")
    
    if not (type1.isdigit() and 0 <= int(type1) <= 9):
        raise ValueError("物料类型2必须是0-9的数字")
        
    if not (type2.isdigit() and 0 <= int(type2) <= 9):
        raise ValueError("物料类型3必须是0-9的数字")
        
    if not (isinstance(supplier_code, (int, str)) and 1 <= int(supplier_code) <= 99):
        raise ValueError("供应商编码必须是01-99")
    
    collection = db[MATERIALS_COLLECTION]
    
    # 查找该类别下的最大序号
    supplier_code_str = f"{int(supplier_code):02d}"
    prefix = f"{platform.upper()}-{type1}{type2}-{supplier_code_str}-0000"
    pattern = f"^{prefix}-"
    
    last_material = collection.find_one(
        {"material_code": {"$regex": pattern}},
        sort=[("sequence", -1)]
    )
    
    new_sequence = 1
    if last_material and "sequence" in last_material:
        new_sequence = last_material["sequence"] + 1
        
    # 格式化编码: P-XX-XX-XXXX-XXX
    material_code = f"{prefix}-{new_sequence:03d}"
    
    return material_code, new_sequence

def add_material(db, material_info):
    """
    添加一个新物料到数据库。
    material_info 应该是一个包含物料信息的字典，例如：
    {
        "platform": "P",
        "type1": "1",
        "type2": "3",
        "supplier_code": "05",
        "supplier_name": "深圳市创实科技有限公司",
        "material_name": "工控机",
        "material_model": "1U-C3558-4电2光-128G",
        "hardware_platform": "x86",
        "unit": "台"
    }
    """
    from datetime import datetime
    
    collection = db[MATERIALS_COLLECTION]
    
    # 从物料信息中提取编码所需参数
    platform = material_info.get("platform", "P")
    type1 = material_info.get("type1", "0")
    type2 = material_info.get("type2", "0")
    supplier_code = material_info.get("supplier_code", "01")

    # 1. 验证供应商信息
    supplier_name = material_info.get("supplier_name")
    supplier_id = None
    if supplier_name:
        supplier = db.suppliers.find_one({"supplier_name": supplier_name})
        if supplier:
            supplier_id = supplier["_id"]
            # 如果供应商有编码，使用供应商的编码
            if "supplier_code" in supplier:
                supplier_code = supplier["supplier_code"]
        else:
            print(f"⚠️ 警告: 供应商 '{supplier_name}' 不存在于数据库中")

    # 2. 生成物料编码
    try:
        material_code, sequence = generate_material_code(db, platform, type1, type2, supplier_code)
    except ValueError as e:
        print(f"❌ 编码生成失败: {e}", file=sys.stderr)
        return None
    
    # 检查编码是否已存在 (以防万一)
    if collection.find_one({"material_code": material_code}):
        print(f"⚠️ 警告: 生成的物料编码 {material_code} 已存在，请检查逻辑。")
        return None
        
    # 3. 准备完整的物料文档
    current_time = datetime.utcnow()
    new_material_doc = {
        "material_code": material_code,
        "sequence": sequence,
        "platform": platform,
        "type1": type1,
        "type2": type2,
        "supplier_code": supplier_code,
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "material_name": material_info.get("material_name", ""),
        "material_model": material_info.get("material_model", ""),
        "hardware_platform": material_info.get("hardware_platform", ""),
        "unit": material_info.get("unit", "个"),
        "status": "active",
        "created_at": current_time,
        "updated_at": current_time
    }
    
    # 4. 插入数据库
    try:
        result = collection.insert_one(new_material_doc)
        print(f"✅ 物料添加成功: {material_code} (ID: {result.inserted_id})")
        return result.inserted_id
    except Exception as e:
        print(f"❌ 添加物料失败: {e}", file=sys.stderr)
        return None

class MaterialManager:
    """物料管理器类"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """连接数据库"""
        self.client = get_db_client()
        if self.client is not None:
            self.db = self.client[DATABASE_NAME]
    
    def generate_material_code(self, platform, type1, type2, supplier_code):
        """生成物料编码"""
        if self.db is None:
            raise Exception("数据库连接失败")
        return generate_material_code(self.db, platform, type1, type2, supplier_code)
    
    def add_material(self, material_info):
        """添加物料"""
        if self.db is None:
            return {
                'success': False,
                'error': '数据库连接失败'
            }
        
        try:
            result_id = add_material(self.db, material_info)
            if result_id:
                # 获取生成的物料编码
                material = self.db[MATERIALS_COLLECTION].find_one({'_id': result_id})
                return {
                    'success': True,
                    'material_code': material['material_code'] if material else 'Unknown',
                    'id': str(result_id)
                }
            else:
                return {
                    'success': False,
                    'error': '添加物料失败'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def close(self):
        """关闭数据库连接"""
        if self.client:
            self.client.close()

def main():
    """
    主函数，用于测试模块功能
    """
    print("--- 物料管理模块测试 ---")
    client = get_db_client()
    if not client:
        sys.exit(1)
        
    db = client[DATABASE_NAME]
    
    # 模拟添加一个新物料
    print("\n[测试] 准备添加一个新物料...")
    sample_material = {
        "platform": "P",
        "type1": "2", # 非国产
        "type2": "4", # 配件
        "supplier_code": "08", # 假设的供应商编码
        "material_name": "工业级内存条",
        "material_model": "DDR4 16GB ECC",
        "unit": "条"
    }
    print(f"物料信息: {sample_material}")
    
    add_material(db, sample_material)
    
    client.close()
    print("\n--- 测试结束 ---")

if __name__ == "__main__":
    main()