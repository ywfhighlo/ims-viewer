#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带标准编码的MongoDB数据导入脚本
根据生成的标准物料编码映射，将JSON数据导入到MongoDB数据库中
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from vscode_config_reader import get_vscode_config, get_data_directory, get_mongo_config

class StandardCodeImporter:
    """标准编码数据导入器"""
    
    def __init__(self):
        """初始化导入器"""
        # 获取VS Code配置
        self.vscode_config = get_vscode_config()
        # 使用动态获取的数据目录
        self.data_directory = get_data_directory()
        print(f"使用数据目录: {self.data_directory}")
        
        # 获取MongoDB配置
        mongo_config = get_mongo_config()
        
        # 构建MongoDB连接URI
        if mongo_config['username'] and mongo_config['password']:
            auth_part = f"{mongo_config['username']}:{mongo_config['password']}@"
            auth_db_part = f"?authSource={mongo_config['auth_database']}"
        else:
            auth_part = ""
            auth_db_part = ""
        
        # 从URI中提取主机和端口
        uri_base = mongo_config['uri'].rstrip('/')
        if not uri_base.startswith('mongodb://'):
            uri_base = f"mongodb://{uri_base}"
        
        mongo_uri = f"{uri_base.replace('mongodb://', f'mongodb://{auth_part}')}{auth_db_part}"
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_config['database_name']]
        
        self.mapping = self._load_standard_code_mapping()
        
        print(f"使用数据目录: {self.data_directory}")
        print(f"连接数据库: {mongo_config['database_name']}")
        
    def _load_standard_code_mapping(self) -> Dict[str, str]:
        """从标准物料表中加载编码映射"""
        table_file = os.path.join(self.data_directory, 'standard_material_table.json')
        
        if not os.path.exists(table_file):
            print(f"警告: 标准物料表文件不存在: {table_file}")
            return {}
        
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                table_data = json.load(f)
            
            # 从materials数组中提取old_code到new_code的映射
            mapping = {}
            materials = table_data.get('materials', [])
            
            for material in materials:
                old_code = material.get('old_code')
                new_code = material.get('new_code')
                if old_code and new_code:
                    mapping[old_code] = new_code
            
            print(f"成功从标准物料表加载编码映射，共 {len(mapping)} 条记录")
            return mapping
        except Exception as e:
            print(f"加载标准编码映射失败: {e}")
            return {}
    
    def _apply_standard_codes(self, records: List[Dict[str, Any]], table_name: str) -> List[Dict[str, Any]]:
        """为记录应用标准编码"""
        updated_records = []
        
        for record in records:
            updated_record = record.copy()
            
            # 根据表类型处理不同的物料编码字段
            material_code_field = self._get_material_code_field(table_name)
            
            if material_code_field and material_code_field in record:
                old_code = record[material_code_field]
                if old_code in self.mapping:
                    # 保留原编码，添加标准编码
                    updated_record[f'original_{material_code_field}'] = old_code
                    updated_record[material_code_field] = self.mapping[old_code]
                    updated_record['standard_code_applied'] = True
                    updated_record['code_mapping_time'] = datetime.now().isoformat()
                else:
                    updated_record['standard_code_applied'] = False
                    updated_record['unmapped_code'] = old_code
            
            updated_records.append(updated_record)
        
        return updated_records
    
    def _get_material_code_field(self, table_name: str) -> Optional[str]:
        """获取表对应的物料编码字段名"""
        field_mapping = {
            'materials': 'material_code',
            'purchase_params': 'material_code',
            'purchase_inbound': 'material_code',
            'sales_outbound': 'material_code',
            'inventory_stats': 'material_code',
            'receipt_details': 'material_code'
        }
        return field_mapping.get(table_name)
    
    def import_table_data(self, json_file: str, table_name: str) -> bool:
        """导入单个表的数据"""
        try:
            if not os.path.exists(json_file):
                print(f"文件不存在: {json_file}")
                return False
            
            with open(json_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            # 获取数据记录
            records = file_data.get('data', [])
            if not records:
                print(f"表 {table_name} 没有数据记录")
                return True
            
            # 应用标准编码
            updated_records = self._apply_standard_codes(records, table_name)
            
            # 清空现有集合
            collection = self.db[table_name]
            collection.drop()
            
            # 插入更新后的数据
            if updated_records:
                result = collection.insert_many(updated_records)
                print(f"✓ 表 {table_name}: 成功导入 {len(result.inserted_ids)} 条记录")
                
                # 统计标准编码应用情况
                mapped_count = sum(1 for r in updated_records if r.get('standard_code_applied', False))
                unmapped_count = len(updated_records) - mapped_count
                
                if mapped_count > 0:
                    print(f"  - 应用标准编码: {mapped_count} 条")
                if unmapped_count > 0:
                    print(f"  - 未映射编码: {unmapped_count} 条")
            
            return True
            
        except Exception as e:
            print(f"导入表 {table_name} 时出错: {str(e)}")
            return False
    
    def import_all_tables(self) -> Dict[str, bool]:
        """导入所有表数据"""
        tables = [
            'suppliers', 'customers', 'materials', 'purchase_params',
            'purchase_inbound', 'sales_outbound', 'inventory_stats',
            'receipt_details', 'payment_details'
        ]
        
        results = {}
        
        print("开始导入所有表数据...")
        print(f"使用标准编码映射: {len(self.mapping)} 个映射")
        print("=" * 60)
        
        for table in tables:
            json_file = os.path.join(self.data_directory, f"{table}.json")
            print(f"\n导入表: {table}")
            results[table] = self.import_table_data(json_file, table)
        
        return results
    
    def create_indexes(self):
        """创建数据库索引"""
        print("\n创建数据库索引...")
        
        # 为各表创建常用索引
        indexes = {
            'materials': ['material_code', 'material_name'],
            'suppliers': ['supplier_code', 'supplier_name'],
            'customers': ['customer_code', 'customer_name'],
            'purchase_params': ['material_code', 'supplier_name'],
            'purchase_inbound': ['material_code', 'supplier_name', 'inbound_date'],
            'sales_outbound': ['material_code', 'customer_name', 'outbound_date'],
            'inventory_stats': ['material_code'],
            'receipt_details': ['material_code'],
            'payment_details': ['supplier_name', 'payment_date']
        }
        
        for table, fields in indexes.items():
            collection = self.db[table]
            for field in fields:
                try:
                    collection.create_index(field)
                    print(f"✓ 为 {table}.{field} 创建索引")
                except Exception as e:
                    print(f"✗ 为 {table}.{field} 创建索引失败: {str(e)}")
    
    def generate_import_report(self, results: Dict[str, bool]):
        """生成导入报告"""
        print("\n" + "=" * 60)
        print("数据导入完成报告")
        print("=" * 60)
        
        successful_tables = [table for table, success in results.items() if success]
        failed_tables = [table for table, success in results.items() if not success]
        
        print(f"成功导入: {len(successful_tables)} 个表")
        for table in successful_tables:
            count = self.db[table].count_documents({})
            print(f"  ✓ {table}: {count} 条记录")
        
        if failed_tables:
            print(f"\n导入失败: {len(failed_tables)} 个表")
            for table in failed_tables:
                print(f"  ✗ {table}")
        
        # 统计标准编码应用情况
        print("\n标准编码应用统计:")
        for table in successful_tables:
            if self._get_material_code_field(table):
                collection = self.db[table]
                total = collection.count_documents({})
                mapped = collection.count_documents({'standard_code_applied': True})
                unmapped = collection.count_documents({'standard_code_applied': False})
                
                if total > 0:
                    print(f"  {table}: 总计 {total}, 已映射 {mapped}, 未映射 {unmapped}")
        
        print(f"\n数据库: {self.db.name}")
        print(f"总集合数: {len(self.db.list_collection_names())}")
        print("导入完成!")
    
    def close(self):
        """关闭数据库连接"""
        self.client.close()

def main():
    """主函数"""
    importer = StandardCodeImporter()
    
    try:
        # 导入所有表数据
        results = importer.import_all_tables()
        
        # 创建索引
        importer.create_indexes()
        
        # 生成报告
        importer.generate_import_report(results)
        
    except Exception as e:
        print(f"导入过程中出错: {str(e)}")
    finally:
        importer.close()

if __name__ == "__main__":
    main()