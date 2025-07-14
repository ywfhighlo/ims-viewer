#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from vscode_config_reader import get_data_directory
"""
付款明细表解析脚本
使用统一的字段映射词典进行数据转换
"""

import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from field_mapping_utils import field_mapper, translate_dict_to_english
from data_filter import DataFilter

def parse_payment_details(excel_file_path: str, sheet_name: str = "付款明细表") -> List[Dict[str, Any]]:
    """
    解析付款明细表
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
        field_mapper.create_mapping_for_excel(excel_headers, "payment_details")
        data = [translate_dict_to_english(row.dropna().to_dict()) for _, row in df.iterrows()]
        
        # 数据过滤
        print(f"开始数据过滤，原始记录数: {len(data)}")
        
        # 第一步：过滤空记录
        filtered_data, filtered_count = DataFilter.filter_empty_records(data)
        print(f"过滤空记录后: {len(filtered_data)} 条记录，过滤掉 {filtered_count} 条")
        
        # 第二步：进一步过滤，确保记录包含关键字段
        final_data = []
        for record in filtered_data:
            # 付款明细记录应至少包含付款单号或供应商名称
            if (record.get('payment_order_number') and str(record.get('payment_order_number')).strip()) or \
               (record.get('supplier_name') and str(record.get('supplier_name')).strip()):
                final_data.append(record)
        
        additional_filtered = len(filtered_data) - len(final_data)
        print(f"进一步过滤后: {len(final_data)} 条记录，额外过滤掉 {additional_filtered} 条")
        
        # 打印过滤摘要
        DataFilter.print_filter_summary(
            original_count=len(data),
            filtered_count=len(data) - len(final_data),
            data_type="付款明细记录"
        )
        
        data = final_data
        
        # 处理日期字段，确保可以序列化
        for record in data:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif hasattr(value, 'isoformat'):  # 处理日期时间对象
                    record[key] = value.isoformat()
                elif isinstance(value, pd.Timestamp):
                    record[key] = value.isoformat()
        
        print(f"成功解析 {len(data)} 条付款明细")
        return data
    except Exception as e:
        print(f"解析付款明细时出错: {str(e)}")
        raise

def save_payment_details_data(payment_details_data: List[Dict[str, Any]], output_file: str = None):
    """
    保存付款明细数据为JSON文件
    """
    try:
        if output_file is None:
            data_dir = get_data_directory()
            output_file = os.path.join(data_dir, "payment_details.json")
        output_data = {
            "metadata": {
                "table_name": "payment_details",
                "table_chinese_name": "付款明细表",
                "total_records": len(payment_details_data),
                "source": "imsviewer.xlsx - 付款明细表",
                "field_mapping": field_mapper.get_table_schema("payment_details"),
                "generated_by": "parse6_payment_details.py",
                "generated_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "description": "付款明细数据，包含付款单号、供应商信息、付款金额等",
                "data_filtering": {
                    "applied": True,
                    "filters": [
                        "移除空记录",
                        "确保记录包含付款单号或供应商名称"
                    ]
                },
                "dictionary_version": field_mapper._dictionary.get("metadata", {}).get("version", "unknown")
            },
            "data": payment_details_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"付款明细数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存付款明细数据时出错: {str(e)}")
        raise

def main():
    """主函数"""
    data_dir = get_data_directory()
    excel_file = os.path.join(data_dir, "imsviewer.xlsx")
    if not os.path.exists(excel_file):
        print(f"Excel文件不存在: {excel_file}")
        return
    
    try:
        print("=== 开始解析付款明细表 ===")
        data = parse_payment_details(excel_file)
        
        print("\n=== 保存付款明细数据到docs目录 ===")
        save_payment_details_data(data)
        
        print("\n=== 显示前2条数据示例 ===")
        print(json.dumps(data[:2], ensure_ascii=False, indent=2))
        print("\n付款明细表解析完成")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()