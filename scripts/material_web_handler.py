#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料管理Web界面后端处理器
处理来自Web界面的请求，包括供应商管理、物料添加、查询等功能
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from material_manager import MaterialManager, MATERIALS_COLLECTION
from database_config import get_db_client, get_database_name

# 为了向后兼容
DATABASE_NAME = get_database_name()

def json_serializer(obj):
    """JSON序列化辅助函数，处理MongoDB的ObjectId"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

class MaterialWebHandler:
    """物料管理Web界面处理器"""
    
    def __init__(self):
        self.material_manager = MaterialManager()
        self.client = get_db_client()
        self.db = self.client[DATABASE_NAME] if self.client else None
        
    def handle_request(self, command: str, data: Dict = None) -> Dict[str, Any]:
        """处理Web界面请求"""
        try:
            if command == 'loadSuppliers':
                return self.load_suppliers()
            elif command == 'addMaterial':
                return self.add_material(data)
            elif command == 'loadMaterials':
                return self.load_materials()
            elif command == 'loadSupplierCodes':
                return self.load_supplier_codes()
            elif command == 'assignSupplierCodes':
                return self.assign_supplier_codes()
            elif command == 'exportMaterials':
                return self.export_materials()
            else:
                return {
                    'success': False,
                    'error': f'未知命令: {command}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'处理请求时发生错误: {str(e)}'
            }
    
    def load_suppliers(self) -> Dict[str, Any]:
        """加载供应商列表"""
        try:
            suppliers_collection = self.db['suppliers']
            suppliers = list(suppliers_collection.find(
                {},
                {
                    'supplier_name': 1,
                    'supplier_code': 1,
                    'credit_code': 1,
                    'contact_person': 1,
                    'phone': 1
                }
            ).sort('supplier_name', 1))
            
            # 只返回有编码的供应商
            suppliers_with_codes = [
                supplier for supplier in suppliers 
                if supplier.get('supplier_code')
            ]
            
            return {
                'success': True,
                'command': 'suppliersLoaded',
                'data': suppliers_with_codes
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'加载供应商失败: {str(e)}'
            }
    
    def add_material(self, data: Dict) -> Dict[str, Any]:
        """添加物料"""
        try:
            # 验证必填字段
            required_fields = ['platform', 'type1', 'type2', 'supplier_code', 
                             'supplier_name', 'material_name', 'material_model', 'unit']
            
            for field in required_fields:
                if not data.get(field):
                    return {
                        'success': False,
                        'error': f'缺少必填字段: {field}'
                    }
            
            # 构建物料数据
            material_data = {
                'material_name': data['material_name'],
                'material_model': data['material_model'],
                'supplier_name': data['supplier_name'],
                'unit': data['unit'],
                'platform': data['platform'],
                'hardware_platform': data.get('hardware_platform', ''),
                'type1': data['type1'],
                'type2': data['type2'],
                'supplier_code': data['supplier_code']
            }
            
            # 添加物料
            result = self.material_manager.add_material(material_data)
            
            if result['success']:
                return {
                    'success': True,
                    'command': 'materialAdded',
                    'materialCode': result['material_code'],
                    'message': '物料添加成功'
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'添加物料失败: {str(e)}'
            }
    
    def load_materials(self) -> Dict[str, Any]:
        """加载物料列表"""
        try:
            materials_collection = self.db['materials']
            materials = list(materials_collection.find(
                {},
                {
                    'material_code': 1,
                    'material_name': 1,
                    'material_model': 1,
                    'supplier_name': 1,
                    'unit': 1,
                    'platform': 1,
                    'hardware_platform': 1,
                    'created_at': 1,
                    'status': 1
                }
            ).sort('created_at', -1).limit(50))  # 最新50条记录
            
            # 格式化时间
            for material in materials:
                if 'created_at' in material:
                    material['created_at'] = material['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            return {
                'success': True,
                'command': 'materialsLoaded',
                'data': materials
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'加载物料列表失败: {str(e)}'
            }
    
    def load_supplier_codes(self) -> Dict[str, Any]:
        """加载供应商编码"""
        try:
            suppliers_collection = self.db['suppliers']
            suppliers = list(suppliers_collection.find(
                {},
                {
                    'supplier_name': 1,
                    'supplier_code': 1,
                    'credit_code': 1
                }
            ).sort([('supplier_code', 1), ('supplier_name', 1)]))
            
            return {
                'success': True,
                'command': 'supplierCodesLoaded',
                'data': suppliers
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'加载供应商编码失败: {str(e)}'
            }
    
    def assign_supplier_codes(self) -> Dict[str, Any]:
        """分配供应商编码"""
        try:
            suppliers_collection = self.db['suppliers']
            
            # 获取所有没有编码的供应商
            suppliers_without_codes = list(suppliers_collection.find({
                '$or': [
                    {'supplier_code': {'$exists': False}},
                    {'supplier_code': None},
                    {'supplier_code': ''}
                ]
            }).sort('supplier_name', 1))
            
            if not suppliers_without_codes:
                return {
                    'success': True,
                    'message': '所有供应商都已有编码'
                }
            
            # 获取已使用的编码
            used_codes = set()
            suppliers_with_codes = suppliers_collection.find({
                'supplier_code': {'$exists': True, '$ne': None, '$ne': ''}
            })
            
            for supplier in suppliers_with_codes:
                code = supplier.get('supplier_code')
                if code and code.isdigit():
                    used_codes.add(int(code))
            
            # 分配新编码
            assigned_count = 0
            for supplier in suppliers_without_codes:
                # 找到下一个可用编码
                for code_num in range(1, 100):
                    if code_num not in used_codes:
                        code = f"{code_num:02d}"
                        
                        # 更新供应商编码
                        result = suppliers_collection.update_one(
                            {'_id': supplier['_id']},
                            {'$set': {'supplier_code': code}}
                        )
                        
                        if result.modified_count > 0:
                            used_codes.add(code_num)
                            assigned_count += 1
                            print(f"为供应商 '{supplier['supplier_name']}' 分配编码: {code}")
                        break
            
            return {
                'success': True,
                'message': f'成功为 {assigned_count} 个供应商分配编码'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'分配供应商编码失败: {str(e)}'
            }
    
    def export_materials(self) -> Dict[str, Any]:
        """导出物料列表"""
        try:
            materials_collection = self.db['materials']
            materials = list(materials_collection.find({}).sort('material_code', 1))
            
            # 生成CSV格式数据
            csv_data = []
            csv_data.append('物料编码,物料名称,物料型号,供应商,单位,平台,硬件平台,创建时间,状态')
            
            for material in materials:
                row = [
                    material.get('material_code', ''),
                    material.get('material_name', ''),
                    material.get('material_model', ''),
                    material.get('supplier_name', ''),
                    material.get('unit', ''),
                    material.get('platform', ''),
                    material.get('hardware_platform', ''),
                    material.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if material.get('created_at') else '',
                    material.get('status', 'active')
                ]
                csv_data.append(','.join([f'"{field}"' for field in row]))
            
            # 保存到文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'materials_export_{timestamp}.csv'
            filepath = os.path.join(os.path.dirname(__file__), '..', 'exports', filename)
            
            # 确保导出目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write('\n'.join(csv_data))
            
            return {
                'success': True,
                'message': f'物料列表已导出到: {filename}',
                'filepath': filepath
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'导出物料列表失败: {str(e)}'
            }

def main():
    """主函数 - 处理命令行参数"""
    if len(sys.argv) < 2:
        print("用法: python material_web_handler.py <command> [data]")
        print("命令:")
        print("  loadSuppliers - 加载供应商列表")
        print("  loadMaterials - 加载物料列表")
        print("  loadSupplierCodes - 加载供应商编码")
        print("  assignSupplierCodes - 分配供应商编码")
        print("  exportMaterials - 导出物料列表")
        return
    
    command = sys.argv[1]
    data = None
    
    if len(sys.argv) > 2:
        try:
            data = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(f"错误: 无法解析JSON数据: {sys.argv[2]}")
            return
    
    handler = MaterialWebHandler()
    result = handler.handle_request(command, data)
    
    print(json.dumps(result, ensure_ascii=False, indent=2, default=json_serializer))

if __name__ == '__main__':
    main()