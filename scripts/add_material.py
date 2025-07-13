#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加物料脚本
用于通过VS Code扩展添加新物料到数据库
"""

import sys
import json
from material_manager import get_db_client, add_material, DATABASE_NAME

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("❌ 用法: python add_material.py '<material_info_json>' 或 python add_material.py <json_file_path>")
        sys.exit(1)
    
    try:
        # 解析物料信息
        material_info_str = sys.argv[1]
        
        # 检查是否是文件路径
        if material_info_str.endswith('.json'):
            with open(material_info_str, 'r', encoding='utf-8') as f:
                material_info = json.load(f)
        else:
            material_info = json.loads(material_info_str)
        
        print(f"📦 准备添加物料: {material_info.get('material_name', '未知')}")
        print(f"📋 物料信息: {material_info}")
        
        # 连接数据库
        client = get_db_client()
        if not client:
            print("❌ 数据库连接失败")
            sys.exit(1)
        
        db = client[DATABASE_NAME]
        
        # 添加物料
        result = add_material(db, material_info)
        
        if result:
            print(f"✅ 物料添加成功，ID: {result}")
        else:
            print("❌ 物料添加失败")
            sys.exit(1)
        
        client.close()
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 添加物料时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()