#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from vscode_config_reader import get_data_directory
"""
库存统计表解析脚本
使用统一的字段映射词典进行数据转换
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any
from field_mapping_utils import field_mapper, translate_dict_to_english

def parse_inventory_stats(excel_file_path: str, sheet_name: str = "库存统计表") -> List[Dict[str, Any]]:
    """
    解析库存统计表 - 处理多级表头
    """
    try:
        # 读取Excel文件，不跳过任何行，先获取多级表头信息
        df_raw = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=None)
        
        # 获取第1行(主表头)和第2行(子表头)
        main_headers = df_raw.iloc[1].tolist()  # 第1行是主表头
        sub_headers = df_raw.iloc[2].tolist()   # 第2行是子表头
        
        # 构建完整的列名映射
        final_headers = []
        for i, (main, sub) in enumerate(zip(main_headers, sub_headers)):
            if pd.notna(sub) and sub.strip():  # 如果子表头不为空，使用子表头
                final_headers.append(sub.strip())
            elif pd.notna(main) and main.strip():  # 否则使用主表头
                final_headers.append(main.strip())
            else:
                final_headers.append(f"未命名列{i}")
        
        print(f"解析的表头: {final_headers}")
        
        # 读取数据，跳过前3行（表名+两级表头）
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=None, skiprows=3)
        df.columns = final_headers
        
        # 过滤掉无效的列
        valid_columns = [col for col in final_headers if not col.startswith('未命名列')]
        df = df[valid_columns]
        
        # 删除全为空的行
        df = df.dropna(how='all')
        
        print(f"有效表头: {valid_columns}")
        
        # 保留所有字段，包括空值，但将NaN转换为None
        data = []
        for _, row in df.iterrows():
            row_dict = {}
            for col in valid_columns:
                value = row[col]
                # 将NaN和空字符串转换为None，保留其他值
                if pd.isna(value) or value == '':
                    row_dict[col] = None
                else:
                    row_dict[col] = value
            # 翻译字段名
            english_row = translate_dict_to_english(row_dict)
            data.append(english_row)
        
        print(f"成功解析 {len(data)} 条库存统计")
        return data
    except Exception as e:
        print(f"解析库存统计时出错: {str(e)}")
        raise

def save_inventory_stats_data(inventory_stats_data: List[Dict[str, Any]], output_file: str = None):
    """
    保存库存统计数据为JSON文件
    """
    try:
        if output_file is None:
            data_dir = get_data_directory()
            output_file = os.path.join(data_dir, "inventory_stats.json")
        output_data = {
            "metadata": {
                "table_name": "inventory_stats",
                "table_chinese_name": "库存统计表",
                "total_records": len(inventory_stats_data),
                "field_mapping": field_mapper.get_table_schema("inventory_stats"),
                "generated_by": "parse8_inventory_stats.py",
                "dictionary_version": field_mapper._dictionary.get("metadata", {}).get("version", "unknown")
            },
            "data": inventory_stats_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"库存统计数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存库存统计数据时出错: {str(e)}")
        raise

def main():
    """主函数"""
    data_dir = get_data_directory()
    excel_file = os.path.join(data_dir, "imsviewer.xlsx")
    if not os.path.exists(excel_file):
        print(f"Excel文件不存在: {excel_file}")
        return
    
    try:
        print("=== 开始解析库存统计表 ===")
        data = parse_inventory_stats(excel_file)
        
        print("\n=== 保存库存统计数据到docs目录 ===")
        save_inventory_stats_data(data)
        
        print("\n=== 显示前2条数据示例 ===")
        print(json.dumps(data[:2], ensure_ascii=False, indent=2))
        print("\n库存统计表解析完成")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()