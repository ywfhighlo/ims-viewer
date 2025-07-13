#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料管理系统测试脚本
测试新的物料编码生成和添加功能
"""

import sys
from material_manager import get_db_client, add_material, DATABASE_NAME

def test_material_system():
    """
    测试物料管理系统
    """
    print("=== 物料管理系统测试 ===")
    
    # 连接数据库
    client = get_db_client()
    if not client:
        print("❌ 数据库连接失败")
        return False
        
    db = client[DATABASE_NAME]
    
    # 首先为一个供应商手动分配编码进行测试
    print("\n1. 为测试供应商分配编码...")
    supplier = db.suppliers.find_one({"supplier_name": "福州创实讯联信息技术有限公司"})
    if supplier:
        # 为这个供应商分配编码05
        db.suppliers.update_one(
            {"_id": supplier["_id"]},
            {"$set": {"supplier_code": "05"}}
        )
        print(f"✅ 已为供应商 '{supplier['supplier_name']}' 分配编码: 05")
    else:
        print("❌ 未找到测试供应商")
        client.close()
        return False
    
    # 测试物料添加
    print("\n2. 测试添加新物料...")
    
    test_materials = [
        {
            "platform": "P",
            "type1": "1",  # 国产
            "type2": "3",  # 工控机
            "supplier_code": "05",
            "supplier_name": "福州创实讯联信息技术有限公司",
            "material_name": "工控机",
            "material_model": "1U-C3558-4电2光-128G MSATA盘-单电源",
            "hardware_platform": "x86",
            "unit": "台"
        },
        {
            "platform": "P",
            "type1": "2",  # 非国产
            "type2": "4",  # 配件
            "supplier_code": "05",
            "supplier_name": "福州创实讯联信息技术有限公司",
            "material_name": "高速SSD卡",
            "material_model": "SanDisk Extreme Pro 128GB",
            "hardware_platform": "通用",
            "unit": "张"
        },
        {
            "platform": "R",
            "type1": "1",  # 国产
            "type2": "1",  # 纯软件
            "supplier_code": "05",
            "supplier_name": "福州创实讯联信息技术有限公司",
            "material_name": "库存管理软件",
            "material_model": "IMS Viewer v1.0",
            "hardware_platform": "跨平台",
            "unit": "套"
        }
    ]
    
    success_count = 0
    for i, material in enumerate(test_materials, 1):
        print(f"\n  测试物料 {i}:")
        print(f"  平台: {material['platform']} ({'采购' if material['platform'] == 'P' else '自研'})")
        print(f"  类型: {material['type1']}-{material['type2']} ({'国产' if material['type1'] == '1' else '非国产'}-{'纯软件' if material['type2'] == '1' else '服务器' if material['type2'] == '2' else '工控机' if material['type2'] == '3' else '配件'})")
        print(f"  物料: {material['material_name']} - {material['material_model']}")
        
        result = add_material(db, material)
        if result:
            success_count += 1
            print(f"  ✅ 添加成功")
        else:
            print(f"  ❌ 添加失败")
    
    print(f"\n📊 测试结果: 成功添加 {success_count}/{len(test_materials)} 个物料")
    
    # 查看生成的物料编码
    print("\n3. 查看生成的物料编码...")
    materials = list(db.materials.find(
        {"supplier_code": "05"},
        {"material_code": 1, "material_name": 1, "material_model": 1, "platform": 1, "type1": 1, "type2": 1}
    ).sort("material_code", 1))
    
    if materials:
        print("生成的物料编码:")
        print("-" * 80)
        for material in materials:
            code = material.get("material_code", "--")
            name = material.get("material_name", "未知")
            model = material.get("material_model", "未知")
            platform = material.get("platform", "--")
            type1 = material.get("type1", "--")
            type2 = material.get("type2", "--")
            print(f"{code} | {name} | {model} | {platform}-{type1}{type2}")
    else:
        print("❌ 没有找到生成的物料")
    
    client.close()
    print("\n=== 测试完成 ===")
    return success_count > 0

def main():
    """
    主函数
    """
    success = test_material_system()
    if success:
        print("\n🎉 物料管理系统测试成功！")
    else:
        print("\n❌ 物料管理系统测试失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()