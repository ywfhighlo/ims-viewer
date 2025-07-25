#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
销售出库明细表解析脚本 - 增强版
集成了增强的日期解析器、日志系统、物料编码匹配和改进的字段映射处理
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any, Optional
from field_mapping_utils import FieldMappingUtils
from enhanced_date_parser import EnhancedDateParser
from enhanced_logger import EnhancedLogger
from material_manager import get_db_client

def parse_sales_outbound(excel_file_path: str, 
                         sheet_name: str = "销售出库明细表",
                         logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    解析销售出库明细表 - 增强版
    """
    if logger is None:
        logger = EnhancedLogger("Parse_Sales_Outbound")

    operation_index = logger.start_operation(f"解析{sheet_name}", 
                                           excel_file=excel_file_path,
                                           sheet=sheet_name,
                                           table="sales_outbound")

    db_client = get_db_client()
    db = None
    if db_client:
        db_name = os.environ.get('IMS_DB_NAME', 'ims_database')
        db = db_client.get_database(db_name)
        logger.info("数据库连接成功", database=db_name)
    else:
        logger.error("无法连接到数据库，物料编码匹配功能将受限")

    try:
        logger.set_context(sheet=sheet_name, table="sales_outbound")

        if not os.path.exists(excel_file_path):
            logger.error(f"Excel文件不存在", file_path=excel_file_path)
            raise FileNotFoundError(f"Excel文件不存在: {excel_file_path}")

        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=1)
        
        original_columns = df.columns.tolist()
        columns = [col for col in original_columns if col and not str(col).startswith('Unnamed')]
        df = df[columns]

        field_utils = FieldMappingUtils()
        missing_mappings = [h for h in columns if not field_utils.get_english_field(h)]
        if missing_mappings:
            logger.warning("发现缺失的字段映射", missing_fields=missing_mappings)

        data = []
        for index, row in df.iterrows():
            row_dict = row.dropna().to_dict()
            if row_dict:
                english_dict = field_utils.translate_dict(row_dict)
                
                if db is not None and english_dict:
                    # 修正：应根据基础物料信息进行匹配，而不是销售产品信息
                    material_name = english_dict.get("material_name")
                    material_model = english_dict.get("specification") # 与采购脚本保持一致

                    if material_name and material_model:
                        found_material = db.materials.find_one({
                            "material_name": material_name,
                            "material_model": material_model
                        })
                        if found_material:
                            english_dict["material_code"] = found_material["material_code"]
                        else:
                            logger.warning(f"物料未在数据库中定义",
                                           row_index=index,
                                           material_name=material_name,
                                           material_model=material_model)
                
                if english_dict:
                    data.append(english_dict)

        date_parser = EnhancedDateParser()
        date_fields = ['outbound_date'] 
        for record in data:
            for field in date_fields:
                if field in record and record[field]:
                    parsed_date = date_parser.parse_date(str(record[field]))
                    if parsed_date:
                        record[field] = parsed_date.isoformat()
        
        logger.end_operation(operation_index, success=True, records=len(data))
        return data

    except Exception as e:
        logger.error(f"销售出库明细表解析失败", error=str(e), include_traceback=True)
        logger.end_operation(operation_index, success=False, error=str(e))
        raise
    finally:
        if db_client:
            db_client.close()
            logger.info("数据库连接已关闭")


def save_sales_outbound_data(sales_outbound_data: List[Dict[str, Any]], output_file: str = "docs/sales_outbound.json"):
    """
    保存销售出库明细数据为JSON文件
    
    Args:
        sales_outbound_data: 销售出库明细数据列表
        output_file: 输出文件路径
    """
    try:
        # 添加元数据
        output_data = {
            "metadata": {
                "table_name": "sales_outbound",
                "table_chinese_name": "销售出库明细表",
                "total_records": len(sales_outbound_data),
                "generated_by": "parse5_sales_outbound.py"
            },
            "data": sales_outbound_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"销售出库明细数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存销售出库明细数据时出错: {str(e)}")
        raise

def main():
    """主函数 - 测试"""
    logger = EnhancedLogger("Parse_Sales_Outbound_Test", "DEBUG")
    excel_file = "docs/imsviewer.xlsx"
    
    logger.info(f"--- 开始销售出库明细表解析测试 ---")
    if not os.path.exists(excel_file):
        logger.error(f"测试文件不存在", file_path=excel_file)
        return
    
    try:
        print("=== 开始解析销售出库明细表 ===")
        data = parse_sales_outbound(excel_file, logger=logger)
        
        print("\n=== 保存销售出库明细数据到docs目录 ===")
        save_sales_outbound_data(data)
        
        logger.info(f"解析测试完成", records=len(data))
        
        print(f"\n解析到 {len(data)} 条记录")
        if data:
            print("\n=== 前两条记录 ===")
            print(json.dumps(data[:2], ensure_ascii=False, indent=2, default=str))
            
    except Exception as e:
        logger.error(f"测试过程中发生错误", error=str(e), include_traceback=True)

if __name__ == "__main__":
    main()