#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段一致性验证工具
检查项目中所有脚本和代码是否使用了统一的字段映射词典
"""

import os
import re
import json
import ast
from typing import Dict, List, Set, Any
from pathlib import Path
from field_mapping_utils import field_mapper

class FieldConsistencyValidator:
    """字段一致性验证器"""
    
    def __init__(self, project_root: str = None):
        """
        初始化验证器
        
        Args:
            project_root: 项目根目录路径
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = Path(project_root)
        self.field_mapper = field_mapper
        
        # 获取词典中的所有字段
        self.dictionary_chinese_fields = set(self.field_mapper._dictionary.get("field_dictionary", {}).keys())
        self.dictionary_english_fields = set()
        for field_info in self.field_mapper._dictionary.get("field_dictionary", {}).values():
            if field_info.get("english"):
                self.dictionary_english_fields.add(field_info["english"])
        
        self.validation_results = {
            "files_checked": 0,
            "inconsistencies": [],
            "hardcoded_mappings": [],
            "undeclared_fields": [],
            "recommendations": []
        }
    
    def validate_project(self) -> Dict[str, Any]:
        """
        验证整个项目的字段一致性
        
        Returns:
            验证结果字典
        """
        print("=== 开始字段一致性验证 ===")
        
        # 检查Python脚本
        self._check_python_files()
        
        # 检查API文件
        self._check_api_files()
        
        # 检查配置文件
        self._check_config_files()
        
        # 生成建议
        self._generate_recommendations()
        
        print("=== 字段一致性验证完成 ===")
        return self.validation_results
    
    def _check_python_files(self):
        """检查Python脚本文件"""
        python_files = [
            "scripts/*.py",
            "backend/*.py",
        ]
        
        for pattern in python_files:
            for file_path in self.project_root.glob(pattern):
                if file_path.name == __file__.split('/')[-1]:  # 跳过自身
                    continue
                
                self._check_python_file(file_path)
    
    def _check_python_file(self, file_path: Path):
        """检查单个Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.validation_results["files_checked"] += 1
            
            # 检查硬编码的字段映射
            self._find_hardcoded_mappings(file_path, content)
            
            # 检查未声明的字段使用
            self._find_undeclared_fields(file_path, content)
            
            # 检查是否使用了统一的字段映射工具
            self._check_field_mapper_usage(file_path, content)
            
        except Exception as e:
            print(f"检查文件 {file_path} 时出错: {e}")
    
    def _find_hardcoded_mappings(self, file_path: Path, content: str):
        """查找硬编码的字段映射"""
        # 查找字典形式的映射
        mapping_patterns = [
            r"column_mapping\s*=\s*{[^}]+}",
            r"field_mapping\s*=\s*{[^}]+}",
            r"{'[^']+'\s*:\s*'[^']+'}",
            r'{"[^"]+"\s*:\s*"[^"]+"}',
        ]
        
        for pattern in mapping_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                mapping_text = match.group(0)
                
                # 尝试解析映射
                try:
                    # 简单的字典解析
                    if '=' in mapping_text:
                        dict_part = mapping_text.split('=', 1)[1].strip()
                    else:
                        dict_part = mapping_text
                    
                    # 检查是否包含中文字段
                    if self._contains_chinese_fields(dict_part):
                        self.validation_results["hardcoded_mappings"].append({
                            "file": str(file_path),
                            "line": content[:match.start()].count('\n') + 1,
                            "mapping": mapping_text[:100] + "..." if len(mapping_text) > 100 else mapping_text,
                            "suggestion": "使用 field_mapper.create_mapping_for_excel() 替代硬编码映射"
                        })
                        
                except Exception:
                    pass
    
    def _find_undeclared_fields(self, file_path: Path, content: str):
        """查找未在词典中声明的字段"""
        # 查找字符串中的中文字段名
        chinese_field_pattern = r'["\']([^"\']*[\u4e00-\u9fff][^"\']*)["\']'
        matches = re.finditer(chinese_field_pattern, content)
        
        for match in matches:
            field_name = match.group(1)
            
            # 检查是否是表字段
            if self._looks_like_field_name(field_name):
                if field_name not in self.dictionary_chinese_fields:
                    self.validation_results["undeclared_fields"].append({
                        "file": str(file_path),
                        "line": content[:match.start()].count('\n') + 1,
                        "field": field_name,
                        "suggestion": f"将字段 '{field_name}' 添加到字段映射词典中"
                    })
    
    def _check_field_mapper_usage(self, file_path: Path, content: str):
        """检查是否使用了统一的字段映射工具"""
        uses_field_mapper = any([
            "from field_mapping_utils import" in content,
            "field_mapper" in content,
            "translate_dict_to_english" in content,
            "translate_to_english" in content
        ])
        
        has_field_operations = any([
            "column_mapping" in content,
            "field_mapping" in content,
            "rename(columns=" in content,
            "中文" in content and "字段" in content
        ])
        
        if has_field_operations and not uses_field_mapper:
            self.validation_results["inconsistencies"].append({
                "file": str(file_path),
                "type": "missing_field_mapper",
                "description": "文件进行了字段操作但未使用统一的字段映射工具",
                "suggestion": "导入并使用 field_mapping_utils 模块"
            })
    
    def _check_api_files(self):
        """检查API文件"""
        api_files = [
            "backend/api_routes.py",
            "backend/views.py",
            "backend/main.py"
        ]
        
        for file_path in api_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self._check_python_file(full_path)
    
    def _check_config_files(self):
        """检查配置文件"""
        # 检查是否有其他的字段映射配置文件
        config_patterns = [
            "**/*mapping*.json",
            "**/*field*.json",
            "**/*schema*.json"
        ]
        
        for pattern in config_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.name == "field_mapping_dictionary.json":
                    continue  # 跳过我们的主词典文件
                
                self._check_config_file(file_path)
    
    def _check_config_file(self, file_path: Path):
        """检查配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 检查是否包含字段映射信息
            if self._contains_field_mapping(config_data):
                self.validation_results["inconsistencies"].append({
                    "file": str(file_path),
                    "type": "duplicate_mapping_config",
                    "description": "发现重复的字段映射配置文件",
                    "suggestion": "合并到统一的字段映射词典中，或确保与主词典保持一致"
                })
                
        except Exception as e:
            print(f"检查配置文件 {file_path} 时出错: {e}")
    
    def _contains_chinese_fields(self, text: str) -> bool:
        """检查文本是否包含中文字段"""
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        for chars in chinese_chars:
            if chars in self.dictionary_chinese_fields:
                return True
        return False
    
    def _looks_like_field_name(self, text: str) -> bool:
        """判断文本是否看起来像字段名"""
        # 简单的启发式规则
        if len(text) < 2 or len(text) > 20:
            return False
        
        # 包含常见字段关键词
        field_keywords = ["名称", "编码", "日期", "金额", "数量", "单价", "地址", "电话", "备注", "信息", "方式"]
        return any(keyword in text for keyword in field_keywords)
    
    def _contains_field_mapping(self, data: Any) -> bool:
        """检查数据是否包含字段映射"""
        if isinstance(data, dict):
            # 检查键名
            for key in data.keys():
                if any(keyword in str(key).lower() for keyword in ["field", "column", "mapping", "schema"]):
                    return True
            
            # 递归检查值
            for value in data.values():
                if self._contains_field_mapping(value):
                    return True
        
        elif isinstance(data, list):
            for item in data:
                if self._contains_field_mapping(item):
                    return True
        
        return False
    
    def _generate_recommendations(self):
        """生成改进建议"""
        recommendations = []
        
        # 基于发现的问题生成建议
        if self.validation_results["hardcoded_mappings"]:
            recommendations.append({
                "priority": "high",
                "category": "字段映射",
                "description": "发现硬编码的字段映射，建议使用统一的字段映射词典",
                "action": "将所有硬编码映射替换为 field_mapper.create_mapping_for_excel() 调用"
            })
        
        if self.validation_results["undeclared_fields"]:
            recommendations.append({
                "priority": "medium",
                "category": "字段声明",
                "description": "发现未在词典中声明的字段",
                "action": "将新字段添加到 field_mapping_dictionary.json 中"
            })
        
        if self.validation_results["inconsistencies"]:
            recommendations.append({
                "priority": "high",
                "category": "工具使用",
                "description": "发现未使用统一字段映射工具的文件",
                "action": "在所有进行字段操作的文件中导入并使用 field_mapping_utils"
            })
        
        # 通用建议
        recommendations.append({
            "priority": "low",
            "category": "最佳实践",
            "description": "建立字段映射的最佳实践",
            "action": "1. 所有新字段必须先在词典中声明\n2. 禁止硬编码字段映射\n3. 使用统一的翻译函数\n4. 定期运行一致性检查"
        })
        
        self.validation_results["recommendations"] = recommendations
    
    def generate_report(self, output_file: str = "field_consistency_report.json"):
        """生成验证报告"""
        report = {
            "validation_timestamp": str(pd.Timestamp.now()),
            "project_root": str(self.project_root),
            "dictionary_version": self.field_mapper._dictionary.get("metadata", {}).get("version", "unknown"),
            "summary": {
                "files_checked": self.validation_results["files_checked"],
                "hardcoded_mappings_found": len(self.validation_results["hardcoded_mappings"]),
                "undeclared_fields_found": len(self.validation_results["undeclared_fields"]),
                "inconsistencies_found": len(self.validation_results["inconsistencies"]),
                "recommendations_count": len(self.validation_results["recommendations"])
            },
            "details": self.validation_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"验证报告已保存到: {output_file}")
        return report
    
    def print_summary(self):
        """打印验证摘要"""
        print("\n=== 字段一致性验证摘要 ===")
        print(f"检查文件数: {self.validation_results['files_checked']}")
        print(f"硬编码映射: {len(self.validation_results['hardcoded_mappings'])} 个")
        print(f"未声明字段: {len(self.validation_results['undeclared_fields'])} 个")
        print(f"不一致问题: {len(self.validation_results['inconsistencies'])} 个")
        
        if self.validation_results["hardcoded_mappings"]:
            print("\n硬编码映射问题:")
            for issue in self.validation_results["hardcoded_mappings"][:3]:  # 只显示前3个
                print(f"  - {issue['file']}:{issue['line']} - {issue['suggestion']}")
        
        if self.validation_results["undeclared_fields"]:
            print("\n未声明字段:")
            for issue in self.validation_results["undeclared_fields"][:3]:  # 只显示前3个
                print(f"  - {issue['file']}:{issue['line']} - 字段: {issue['field']}")
        
        if self.validation_results["inconsistencies"]:
            print("\n不一致问题:")
            for issue in self.validation_results["inconsistencies"][:3]:  # 只显示前3个
                print(f"  - {issue['file']} - {issue['description']}")
        
        print("\n建议:")
        for rec in self.validation_results["recommendations"]:
            print(f"  [{rec['priority'].upper()}] {rec['category']}: {rec['description']}")

def main():
    """主函数"""
    import pandas as pd
    
    validator = FieldConsistencyValidator()
    
    # 执行验证
    results = validator.validate_project()
    
    # 打印摘要
    validator.print_summary()
    
    # 生成报告
    report = validator.generate_report()
    
    print(f"\n详细报告已保存到: field_consistency_report.json")

if __name__ == "__main__":
    main() 