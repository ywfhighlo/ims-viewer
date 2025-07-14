#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from vscode_config_reader import get_data_directory
"""
收款明细表解析脚本
使用统一的字段映射词典进行数据转换
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any
from field_mapping_utils import field_mapper, translate_dict_to_english

def parse_receipt_details(excel_file_path: str, sheet_name: str = "收款明细表") -> List[Dict[str, Any]]:
    """
    解析收款明细表
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
        field_mapper.create_mapping_for_excel(excel_headers, "receipt_details")
        data = [translate_dict_to_english(row.dropna().to_dict()) for _, row in df.iterrows()]
        
        print(f"成功解析 {len(data)} 条收款明细")
        return data
    except Exception as e:
        print(f"解析收款明细时出错: {str(e)}")
        raise

def save_receipt_details_data(receipt_details_data: List[Dict[str, Any]], output_file: str = None):
    """
    保存收款明细数据为JSON文件
    """
    try:
        if output_file is None:
            data_dir = get_data_directory()
            output_file = os.path.join(data_dir, "receipt_details.json")
        output_data = {
            "metadata": {
                "table_name": "receipt_details",
                "table_chinese_name": "收款明细表",
                "total_records": len(receipt_details_data),
                "field_mapping": field_mapper.get_table_schema("receipt_details"),
                "generated_by": "parse7_receipt_details.py",
                "dictionary_version": field_mapper._dictionary.get("metadata", {}).get("version", "unknown")
            },
            "data": receipt_details_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"收款明细数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存收款明细数据时出错: {str(e)}")
        raise

def main():
    """主函数"""
    data_dir = get_data_directory()
    excel_file = os.path.join(data_dir, "imsviewer.xlsx")
    if not os.path.exists(excel_file):
        print(f"Excel文件不存在: {excel_file}")
        return
    
    try:
        print("=== 开始解析收款明细表 ===")
        data = parse_receipt_details(excel_file)
        
        print("\n=== 保存收款明细数据到docs目录 ===")
        save_receipt_details_data(data)
        
        print("\n=== 显示前2条数据示例 ===")
        print(json.dumps(data[:2], ensure_ascii=False, indent=2))
        print("\n收款明细表解析完成")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()