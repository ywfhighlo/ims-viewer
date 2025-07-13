#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进货参数表解析脚本
使用统一的字段映射词典进行数据转换
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any
from field_mapping_utils import field_mapper, translate_dict_to_english

def parse_purchase_params(excel_file_path: str, sheet_name: str = "进货参数表") -> List[Dict[str, Any]]:
    """
    解析进货参数表
    """
    try:
        # 读取Excel文件，跳过第0行（表名），使用第1行作为列名
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=1)
        excel_headers = df.columns.tolist()
        
        # 过滤掉空列名和Unnamed列
        excel_headers = [col for col in excel_headers if col and not str(col).startswith('Unnamed')]
        print(f"过滤后的表头: {excel_headers}")
        
        # 只保留有效列的数据
        df = df[excel_headers]
        
        # 使用统一词典翻译和验证
        field_mapping = field_mapper.create_mapping_for_excel(excel_headers, "purchase_params")
        data = [translate_dict_to_english(row.dropna().to_dict()) for _, row in df.iterrows()]
        
        print(f"成功解析 {len(data)} 条进货参数")
        return data
    except Exception as e:
        print(f"解析进货参数时出错: {str(e)}")
        raise

def save_purchase_params_json(data: List[Dict[str, Any]], output_file: str = "docs/purchase_params.json"):
    """
    保存进货参数数据为JSON文件
    """
    try:
        output_data = {
            "metadata": {
                "table_name": "purchase_params",
                "table_chinese_name": "进货参数表",
                "total_records": len(data),
                "field_mapping": field_mapper.get_table_schema("purchase_params"),
                "generated_by": "parse3_purchase_params.py",
                "dictionary_version": field_mapper._dictionary.get("metadata", {}).get("version", "unknown")
            },
            "data": data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"进货参数数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存进货参数数据时出错: {str(e)}")
        raise

def generate_material_code_mapping(data: List[Dict[str, Any]], output_file: str = "docs/material_code_mapping_from_purchase.json"):
    """
    从进货参数数据生成物料编码映射
    
    Args:
        data: 进货参数数据列表
        output_file: 输出文件路径
    """
    try:
        from datetime import datetime
        
        mappings = []
        
        for item in data:
            # 提取物料编码和名称
            material_code = item.get('material_code', '').strip() if item.get('material_code') else ''
            material_name = item.get('material_name', '').strip() if item.get('material_name') else ''
            specification = item.get('specification', '').strip() if item.get('specification') else ''
            supplier_name = item.get('supplier_name', '').strip() if item.get('supplier_name') else ''
            
            if material_code and material_name:
                mapping = {
                    "material_code": material_code,
                    "material_name": material_name,
                    "specification": specification,
                    "supplier_name": supplier_name,
                    "full_description": f"{material_name} {specification}" if specification else material_name,
                    "source": "purchase_params"
                }
                mappings.append(mapping)
        
        # 创建输出数据
        output_data = {
            "metadata": {
                "source_table": "purchase_params",
                "total_mappings": len(mappings),
                "generated_by": "parse3_purchase_params.py",
                "generation_time": datetime.now().isoformat()
            },
            "mappings": mappings
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"物料编码映射已保存到: {output_file}，共 {len(mappings)} 条映射")
        
    except Exception as e:
        print(f"生成物料编码映射时出错: {str(e)}")
        raise

def main():
    """主函数"""
    excel_file = "docs/imsviewer.xlsx"
    if not os.path.exists(excel_file):
        print(f"Excel文件不存在: {excel_file}")
        return
    
    try:
        print("=== 开始解析进货参数表 ===")
        data = parse_purchase_params(excel_file)
        
        print("\n=== 保存进货参数JSON ===")
        save_purchase_params_json(data)
        
        print("\n=== 生成物料编码映射 ===")
        generate_material_code_mapping(data)
        
        print("\n=== 显示前2条数据示例 ===")
        print(json.dumps(data[:2], ensure_ascii=False, indent=2))
        print("\n进货参数表解析完成")
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()