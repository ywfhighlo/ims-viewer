#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准物料编码表生成器

根据imsviewer-a.md文档中定义的编码规则生成物料编码表
编码格式：P-2301-0000-001

编码规则：
- 第1位：P(采购)或R(自研)
- 第2位：1(国产)或2(非国产)
- 第3位：1(纯软件)、2(服务器)、3(工控机)、4(配件)
- 第4-5位：供应商代码(01-99)
- 第6-9位：保留位(固定0000)
- 第10-12位：物料序号(001-999)

作者：AI Assistant
创建时间：2025-01-13
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

class StandardMaterialTableGenerator:
    def __init__(self, docs_dir: str = None):
        # 自动检测docs目录路径
        if docs_dir is None:
            # 获取脚本所在目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # 向上查找docs目录
            parent_dir = os.path.dirname(script_dir)
            potential_docs = os.path.join(parent_dir, 'docs')
            
            if os.path.exists(potential_docs):
                self.docs_dir = potential_docs
            else:
                # 如果在扩展安装目录中，docs可能在同级目录
                potential_docs = os.path.join(script_dir, '..', 'docs')
                potential_docs = os.path.abspath(potential_docs)
                if os.path.exists(potential_docs):
                    self.docs_dir = potential_docs
                else:
                    # 默认使用相对路径
                    self.docs_dir = "docs"
        else:
            self.docs_dir = docs_dir
            
        print(f"使用docs目录: {self.docs_dir}")
        self.materials = {}
        self.supplier_codes = {}  # 供应商到代码的映射
        self.material_counter = 1  # 物料序号计数器
        
        # 初始化供应商代码映射
        self.init_supplier_codes()
        
    def init_supplier_codes(self) -> None:
        """初始化供应商代码映射"""
        self.supplier_codes = {
            '福州创实讯联信息技术有限公司': '01',
            '深圳迈拓诚悦科技有限公司': '02',
            '深圳顺信科技有限公司': '03',
            '深圳广和电子有限公司': '04',
            '深圳市鲲鹏网络科技有限公司': '05'
        }
        
    def load_json_file(self, filename: str) -> Dict[str, Any]:
        """加载JSON文件"""
        filepath = os.path.join(self.docs_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: 文件 {filepath} 不存在")
            return {}
        except json.JSONDecodeError as e:
            print(f"错误: 解析JSON文件 {filepath} 失败: {e}")
            return {}
    
    def get_supplier_code(self, supplier_name: str) -> str:
        """获取供应商代码"""
        if not supplier_name:
            return '99'  # 未知供应商
        
        # 精确匹配
        for full_name, code in self.supplier_codes.items():
            if full_name in supplier_name:
                return code
        
        # 关键词匹配
        if '创实' in supplier_name:
            return '01'
        elif '迈拓' in supplier_name:
            return '02'
        elif '顺信' in supplier_name:
            return '03'
        elif '广和' in supplier_name:
            return '04'
        elif '鲲鹏' in supplier_name:
            return '05'
        
        # 如果没有匹配到，分配新的代码
        next_code = str(len(self.supplier_codes) + 1).zfill(2)
        if next_code not in self.supplier_codes.values():
            self.supplier_codes[supplier_name] = next_code
            return next_code
        
        return '99'  # 默认未知供应商
    
    def classify_material_type(self, material_name: str, specification: str) -> str:
        """根据物料名称和规格分类物料类型
        
        返回值：
        1 - 纯软件
        2 - 服务器（硬件）
        3 - 工控机（硬件）
        4 - 配件（如CF卡、SSD卡、硬盘、内存、板卡、电源、机箱等）
        """
        name_spec = f"{material_name} {specification}".lower()
        
        # 纯软件
        if any(keyword in name_spec for keyword in ['软件', 'software', '系统', '程序']):
            return '1'
        
        # 服务器
        elif any(keyword in name_spec for keyword in ['服务器', 'server']):
            return '2'
        
        # 工控机
        elif any(keyword in name_spec for keyword in ['工控机', 'industrial', 'ipc', '1u', '2u', '桌面']):
            return '3'
        
        # 配件
        elif any(keyword in name_spec for keyword in [
            'cf卡', 'ssd', 'msata', '硬盘', '内存', '板卡', '电源', '机箱',
            '配件', '线缆', '存储', '硬件'
        ]):
            return '4'
        
        # 默认归类为工控机（因为当前数据主要是工控机）
        else:
            return '3'
    
    def determine_origin_type(self, supplier_name: str, material_name: str) -> str:
        """判断物料来源类型
        
        返回值：
        1 - 国产
        2 - 非国产
        """
        # 根据供应商名称判断
        domestic_keywords = ['福州', '深圳', '北京', '上海', '广州', '杭州', '成都', '西安']
        foreign_keywords = ['美国', '德国', '日本', '韩国', '台湾', 'intel', 'amd', 'nvidia']
        
        supplier_lower = supplier_name.lower()
        material_lower = material_name.lower()
        
        # 检查是否包含国外关键词
        if any(keyword in supplier_lower or keyword in material_lower for keyword in foreign_keywords):
            return '2'
        
        # 检查是否包含国内关键词
        if any(keyword in supplier_lower for keyword in domestic_keywords):
            return '1'
        
        # 默认认为是国产
        return '1'
    
    def generate_material_code(self, material_name: str, specification: str, supplier_name: str) -> str:
        """生成标准物料编码
        
        格式：P-2301-0000-001
        - P: 采购物料
        - 2: 第2位（国产/非国产）
        - 3: 第3位（物料类型）
        - 01: 第4-5位（供应商代码）
        - 0000: 第6-9位（保留位）
        - 001: 第10-12位（物料序号）
        """
        # 第1位：固定为P（采购）
        platform = 'P'
        
        # 第2位：国产/非国产
        origin_type = self.determine_origin_type(supplier_name, material_name)
        
        # 第3位：物料类型
        material_type = self.classify_material_type(material_name, specification)
        
        # 第4-5位：供应商代码
        supplier_code = self.get_supplier_code(supplier_name)
        
        # 第6-9位：保留位（固定0000）
        reserved = '0000'
        
        # 第10-12位：物料序号
        sequence = str(self.material_counter).zfill(3)
        self.material_counter += 1
        
        # 组合编码
        new_code = f"{platform}-{origin_type}{material_type}{supplier_code}-{reserved}-{sequence}"
        
        return new_code
    
    def extract_materials_from_purchase_params(self) -> None:
        """从进货参数中提取物料信息"""
        data = self.load_json_file('purchase_params.json')
        if not data or 'data' not in data:
            return
        
        for item in data['data']:
            old_code = item.get('material_code', '')
            if not old_code:
                continue
                
            material_name = item.get('material_name', '')
            specification = item.get('specification', '')
            supplier_name = item.get('supplier_name', '')
            
            # 生成新的标准编码
            new_code = self.generate_material_code(material_name, specification, supplier_name)
            
            # 分析编码组成
            code_analysis = self.analyze_material_code(new_code)
            
            self.materials[old_code] = {
                'id': len(self.materials) + 1,
                'old_code': old_code,
                'new_code': new_code,
                'material_name': material_name,
                'specification': specification,
                'unit': item.get('unit', '台'),
                'supplier_name': supplier_name,
                'initial_quantity': float(item.get('initial_quantity', 0)),
                'safety_stock': float(item.get('safety_stock', 0)),
                'parameter_description': item.get('parameter_description', ''),
                'handler': item.get('handler', ''),
                'source': 'purchase_params',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'is_active': True,
                'code_analysis': code_analysis
            }
    
    def analyze_material_code(self, code: str) -> Dict[str, str]:
        """分析物料编码的组成部分"""
        # 解析编码格式：P-2301-0000-001
        parts = code.split('-')
        if len(parts) != 4:
            return {'error': '编码格式不正确'}
        
        platform = parts[0]
        type_supplier = parts[1]
        reserved = parts[2]
        sequence = parts[3]
        
        # 解析类型和供应商部分
        if len(type_supplier) >= 4:
            origin_type = type_supplier[0]
            material_type = type_supplier[1]
            supplier_code = type_supplier[2:4]
        else:
            return {'error': '编码格式不正确'}
        
        # 映射说明
        platform_desc = {'P': '采购物料', 'R': '自研物料'}.get(platform, '未知')
        origin_desc = {'1': '国产', '2': '非国产'}.get(origin_type, '未知')
        type_desc = {
            '1': '纯软件',
            '2': '服务器（硬件）',
            '3': '工控机（硬件）',
            '4': '配件'
        }.get(material_type, '未知')
        
        # 查找供应商名称
        supplier_name = '未知供应商'
        for name, code_val in self.supplier_codes.items():
            if code_val == supplier_code:
                supplier_name = name
                break
        
        return {
            'platform': f"{platform} ({platform_desc})",
            'origin_type': f"{origin_type} ({origin_desc})",
            'material_type': f"{material_type} ({type_desc})",
            'supplier_code': f"{supplier_code} ({supplier_name})",
            'reserved': f"{reserved} (保留位)",
            'sequence': f"{sequence} (序号)"
        }
    
    def extract_materials_from_transactions(self) -> None:
        """从交易记录中提取额外的物料信息"""
        # 从进货入库记录中提取
        purchase_data = self.load_json_file('purchase_inbound.json')
        if purchase_data and 'data' in purchase_data:
            for item in purchase_data['data']:
                old_code = item.get('material_code', '')
                if old_code and old_code not in self.materials:
                    material_name = item.get('material_name', '')
                    specification = item.get('specification', '')
                    supplier_name = item.get('supplier_name', '')
                    
                    new_code = self.generate_material_code(material_name, specification, supplier_name)
                    code_analysis = self.analyze_material_code(new_code)
                    
                    self.materials[old_code] = {
                        'id': len(self.materials) + 1,
                        'old_code': old_code,
                        'new_code': new_code,
                        'material_name': material_name,
                        'specification': specification,
                        'unit': item.get('unit', '台'),
                        'supplier_name': supplier_name,
                        'initial_quantity': 0.0,
                        'safety_stock': 0.0,
                        'parameter_description': '',
                        'handler': item.get('handler', ''),
                        'source': 'purchase_inbound',
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'is_active': True,
                        'code_analysis': code_analysis
                    }
        
        # 从销售出库记录中提取
        sales_data = self.load_json_file('sales_outbound.json')
        if sales_data and 'data' in sales_data:
            for item in sales_data['data']:
                old_code = item.get('material_code', '')
                if old_code and old_code not in self.materials:
                    material_name = item.get('material_name', '')
                    specification = item.get('specification', '')
                    
                    # 销售记录中可能没有供应商信息，使用空字符串
                    new_code = self.generate_material_code(material_name, specification, '')
                    code_analysis = self.analyze_material_code(new_code)
                    
                    self.materials[old_code] = {
                        'id': len(self.materials) + 1,
                        'old_code': old_code,
                        'new_code': new_code,
                        'material_name': material_name,
                        'specification': specification,
                        'unit': item.get('unit', '台'),
                        'supplier_name': '',
                        'initial_quantity': 0.0,
                        'safety_stock': 0.0,
                        'parameter_description': '',
                        'handler': item.get('handler', ''),
                        'source': 'sales_outbound',
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'is_active': True,
                        'code_analysis': code_analysis
                    }
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """计算统计信息"""
        total_materials = len(self.materials)
        
        # 按平台统计
        platform_stats = {}
        # 按来源类型统计
        origin_stats = {}
        # 按物料类型统计
        type_stats = {}
        # 按供应商统计
        supplier_stats = {}
        
        for material in self.materials.values():
            code = material['new_code']
            parts = code.split('-')
            if len(parts) >= 4:
                platform = parts[0]
                type_supplier = parts[1]
                
                if len(type_supplier) >= 4:
                    origin_type = type_supplier[0]
                    material_type = type_supplier[1]
                    supplier_code = type_supplier[2:4]
                    
                    platform_stats[platform] = platform_stats.get(platform, 0) + 1
                    origin_stats[origin_type] = origin_stats.get(origin_type, 0) + 1
                    type_stats[material_type] = type_stats.get(material_type, 0) + 1
                    supplier_stats[supplier_code] = supplier_stats.get(supplier_code, 0) + 1
        
        return {
            'total_materials': total_materials,
            'platform_distribution': platform_stats,
            'origin_distribution': origin_stats,
            'type_distribution': type_stats,
            'supplier_distribution': supplier_stats,
            'generation_time': datetime.now().isoformat()
        }
    
    def generate_sql_insert_statements(self) -> str:
        """生成SQL插入语句"""
        sql_statements = []
        
        # 创建表结构
        create_table_sql = """
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    old_code VARCHAR(50) NOT NULL,
    new_code VARCHAR(50) UNIQUE NOT NULL,
    material_name VARCHAR(200) NOT NULL,
    specification TEXT,
    unit VARCHAR(20) DEFAULT '台',
    supplier_name VARCHAR(200),
    initial_quantity DECIMAL(10,2) DEFAULT 0.00,
    safety_stock DECIMAL(10,2) DEFAULT 0.00,
    parameter_description TEXT,
    handler VARCHAR(100),
    source VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
"""
        sql_statements.append(create_table_sql)
        
        # 生成插入语句
        for material in self.materials.values():
            insert_sql = f"""
INSERT INTO materials (
    old_code, new_code, material_name, specification, unit,
    supplier_name, initial_quantity, safety_stock,
    parameter_description, handler, source, created_at, updated_at, is_active
) VALUES (
    '{material['old_code']}',
    '{material['new_code']}',
    '{material['material_name'].replace("'", "''")}',
    '{material['specification'].replace("'", "''")}',
    '{material['unit']}',
    '{material['supplier_name'].replace("'", "''")}',
    {material['initial_quantity']},
    {material['safety_stock']},
    '{material['parameter_description'].replace("'", "''")}',
    '{material['handler']}',
    '{material['source']}',
    '{material['created_at']}',
    '{material['updated_at']}',
    {1 if material['is_active'] else 0}
);"""
            sql_statements.append(insert_sql)
        
        return '\n'.join(sql_statements)
    
    def save_standard_material_table(self) -> None:
        """保存标准物料编码表"""
        # 准备输出数据
        materials_list = list(self.materials.values())
        statistics = self.calculate_statistics()
        
        output_data = {
            'metadata': {
                'title': '标准物料编码表',
                'description': '遵循imsviewer-a.md文档规定的编码规则生成的物料编码表',
                'generated_at': datetime.now().isoformat(),
                'total_materials': len(materials_list),
                'encoding_rules': {
                    'format': 'P-2301-0000-001',
                    'description': {
                        'position_1': 'P(采购)或R(自研)',
                        'position_2': '1(国产)或2(非国产)',
                        'position_3': '1(纯软件)、2(服务器)、3(工控机)、4(配件)',
                        'position_4_5': '供应商代码(01-99)',
                        'position_6_9': '保留位(固定0000)',
                        'position_10_12': '物料序号(001-999)'
                    },
                    'supplier_codes': self.supplier_codes
                }
            },
            'statistics': statistics,
            'materials': materials_list
        }
        
        # 保存JSON文件
        json_filepath = os.path.join(self.docs_dir, 'standard_material_table.json')
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已生成标准物料编码表: {json_filepath}")
        
        # 保存SQL文件
        sql_filepath = os.path.join(self.docs_dir, 'standard_material_table.sql')
        with open(sql_filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_sql_insert_statements())
        
        print(f"✓ 已生成SQL插入脚本: {sql_filepath}")
        
        # 保存标准编码映射文件
        mapping_data = {
            'metadata': {
                'title': '标准物料编码映射表',
                'description': '旧编码到标准编码的映射关系',
                'generated_at': datetime.now().isoformat(),
                'encoding_rules': 'P-2301-0000-001格式'
            },
            'mappings': {old_code: material['new_code'] for old_code, material in self.materials.items()}
        }
        
        mapping_filepath = os.path.join(self.docs_dir, 'standard_material_code_mapping.json')
        with open(mapping_filepath, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已生成标准编码映射文件: {mapping_filepath}")
    
    def print_summary(self) -> None:
        """打印生成摘要"""
        statistics = self.calculate_statistics()
        
        print("\n" + "="*60)
        print("标准物料编码表生成完成")
        print("="*60)
        
        print(f"\n📊 统计信息:")
        print(f"  总物料数量: {statistics['total_materials']}")
        
        print(f"\n🏷️ 平台分布:")
        for platform, count in statistics['platform_distribution'].items():
            platform_name = {'P': '采购物料', 'R': '自研物料'}.get(platform, platform)
            print(f"  {platform} ({platform_name}): {count}")
        
        print(f"\n🌍 来源分布:")
        for origin, count in statistics['origin_distribution'].items():
            origin_name = {'1': '国产', '2': '非国产'}.get(origin, origin)
            print(f"  {origin} ({origin_name}): {count}")
        
        print(f"\n📦 物料类型分布:")
        for mat_type, count in statistics['type_distribution'].items():
            type_name = {
                '1': '纯软件',
                '2': '服务器',
                '3': '工控机',
                '4': '配件'
            }.get(mat_type, mat_type)
            print(f"  {mat_type} ({type_name}): {count}")
        
        print(f"\n🏢 供应商分布:")
        for supplier_code, count in statistics['supplier_distribution'].items():
            supplier_name = '未知供应商'
            for name, code in self.supplier_codes.items():
                if code == supplier_code:
                    supplier_name = name
                    break
            print(f"  {supplier_code} ({supplier_name}): {count}")
        
        print(f"\n📋 编码规则:")
        print(f"  格式: P-2301-0000-001")
        print(f"  说明: {{平台}}-{{来源类型}}{{物料类型}}{{供应商}}-{{保留位}}-{{序号}}")
        
        print(f"\n📄 生成的文件:")
        print(f"  - standard_material_table.json (完整物料数据)")
        print(f"  - standard_material_table.sql (SQL插入脚本)")
        print(f"  - standard_material_code_mapping.json (编码映射表)")
        
        print(f"\n💡 使用建议:")
        print(f"  1. 使用 standard_material_table.sql 直接导入数据库")
        print(f"  2. 使用 standard_material_code_mapping.json 进行数据迁移")
        print(f"  3. 新编码严格遵循imsviewer-a.md文档规定的标准")
        
        # 显示前几个示例
        print(f"\n🔍 编码示例:")
        count = 0
        for old_code, material in self.materials.items():
            if count >= 5:
                break
            print(f"  {old_code} → {material['new_code']} ({material['material_name']})")
            count += 1
        
        if len(self.materials) > 5:
            print(f"  ... 还有 {len(self.materials) - 5} 个物料")
        
        print(f"\n📝 供应商代码分配:")
        for supplier, code in self.supplier_codes.items():
            print(f"  {code}: {supplier}")
    
    def generate(self) -> None:
        """执行完整的生成流程"""
        print("开始生成标准物料编码表...")
        print("编码规则: P-2301-0000-001 (遵循imsviewer-a.md文档规定)")
        
        # 提取物料信息
        print("\n1. 从进货参数中提取物料信息...")
        self.extract_materials_from_purchase_params()
        
        print("2. 从交易记录中提取额外物料信息...")
        self.extract_materials_from_transactions()
        
        print("3. 生成标准编码和保存文件...")
        self.save_standard_material_table()
        
        print("4. 生成完成!")
        self.print_summary()

def main():
    """主函数"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="生成标准物料编码表和映射文件")
    parser.add_argument("--docs-dir", help="指定docs目录路径")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("开始生成标准物料编码表...")
    print("="*60)
    
    try:
        # 创建生成器实例
        generator = StandardMaterialTableGenerator(docs_dir=args.docs_dir)
        
        # 执行生成流程
        generator.generate()
        
    except Exception as e:
        print(f"\n❌ 生成过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()