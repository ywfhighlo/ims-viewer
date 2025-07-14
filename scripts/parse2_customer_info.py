#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from vscode_config_reader import get_data_directory
"""
客户信息表解析脚本
使用统一的字段映射词典进行数据转换
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any
from field_mapping_utils import field_mapper, translate_dict_to_english

def parse_customer_info(excel_file_path: str, sheet_name: str = "客户信息表") -> List[Dict[str, Any]]:
    """
    解析客户信息表
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
        field_mapping = field_mapper.create_mapping_for_excel(excel_headers, "customers")
        
        # 保留所有字段，包括空值，但将NaN转换为None
        customers_data = []
        for _, row in df.iterrows():
            row_dict = {}
            for col in excel_headers:
                value = row[col]
                # 将NaN和空字符串转换为None，保留其他值
                if pd.isna(value) or value == '':
                    row_dict[col] = None
                else:
                    row_dict[col] = value
            # 翻译字段名
            english_row = translate_dict_to_english(row_dict)
            customers_data.append(english_row)
        
        print(f"成功解析 {len(customers_data)} 条客户信息")
        return customers_data
    except Exception as e:
        print(f"解析客户信息时出错: {str(e)}")
        raise

def save_customers_data(customers_data: List[Dict[str, Any]], output_file: str = None):
    """
    保存解析后的客户数据为JSON文件
    """
    try:
        if output_file is None:
            data_dir = get_data_directory()
            output_file = os.path.join(data_dir, "customers.json")
        output_data = {
            "metadata": {
                "table_name": "customers",
                "table_chinese_name": "客户信息表",
                "total_records": len(customers_data),
                "field_mapping": field_mapper.get_table_schema("customers"),
                "generated_by": "parse2_customer_info.py",
                "dictionary_version": field_mapper._dictionary.get("metadata", {}).get("version", "unknown")
            },
            "data": customers_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"客户数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存客户数据时出错: {str(e)}")
        raise

def main():
    """主函数"""
    data_dir = get_data_directory()
    excel_file = os.path.join(data_dir, "imsviewer.xlsx")
    if not os.path.exists(excel_file):
        print(f"Excel文件不存在: {excel_file}")
        return
    
    try:
        print("=== 开始解析客户信息表 ===")
        customers_data = parse_customer_info(excel_file)
        
        print("\n=== 保存客户数据到docs目录 ===")
        save_customers_data(customers_data)
        
        print("\n=== 显示前2条数据示例 ===")
        print(json.dumps(customers_data[:2], ensure_ascii=False, indent=2))
        print("\n客户信息表解析完成")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()