# IMS Viewer - 智能库存管理系统

-   **作者**: 余文锋
-   **邮箱**: 909188787@qq.com
-   **项目地址**: https://github.com/ywfhighlo/ims-viewer.git

## 项目概述

IMS Viewer 是一个基于 VSCode 的企业级库存管理系统(Inventory Management System)，专为中小企业的进销存业务设计。系统通过智能化的数据处理引擎，将传统的 Excel 业务数据转换为结构化的数据库存储，并提供丰富的业务分析和报表功能。

### 核心价值
- **数据标准化**: 将混乱的 Excel 数据转换为标准化的业务数据模型
- **业务智能化**: 提供库存分析、销售统计、财务对账等智能业务视图
- **操作便捷化**: 在熟悉的 VSCode 环境中完成所有库存管理操作
- **扩展灵活化**: 模块化架构支持业务逻辑的快速扩展和定制

## 业务数据模型

系统围绕以下核心业务实体构建：

### 基础数据
- **供应商信息** (`suppliers`): 供应商档案、联系方式、信用代码
- **客户信息** (`customers`): 客户档案、联系方式、业务往来
- **物料信息** (`materials`): 物料编码、规格型号、单位价格

### 业务流程数据
- **采购参数** (`purchase_params`): 采购计划、价格协议
- **采购入库** (`purchase_inbound`): 入库记录、质检信息
- **销售出库** (`sales_outbound`): 出库记录、客户订单
- **库存统计** (`inventory_stats`): 实时库存、库存价值

### 财务数据
- **付款明细** (`payment_details`): 供应商付款记录
- **收款明细** (`receipt_details`): 客户收款记录

## 核心功能模块

### 📊 数据导入与解析
- **智能Excel解析**: 自动识别和解析8种业务数据类型
- **字段映射**: 中英文字段自动映射，支持自定义扩展
- **数据验证**: 多层次数据验证，确保数据质量
- **增量更新**: 支持数据的增量导入和更新

### 📈 业务分析报表
- **库存盘点报表**: 实时库存状态、库存价值分析、缺货预警
- **销售统计报表**: 产品销售排行、客户分析、销售趋势
- **采购分析报表**: 供应商评估、采购成本分析
- **财务对账报表**: 应收应付统计、资金流水分析

### 🔧 数据管理工具
- **供应商管理**: 供应商档案维护、编码分配、业务评估
- **客户管理**: 客户信息维护、信用管理、销售跟踪
- **物料管理**: 物料档案、规格管理、价格维护
- **库存管理**: 库存查询、调拨管理、盘点功能

### ⚙️ 系统配置
- **数据库配置**: MongoDB连接参数、认证设置
- **界面配置**: 字体大小、显示模式、输出格式
- **业务配置**: 库存预警阈值、编码规则、审批流程

## 技术特性

### 🏗️ 架构设计
- **前后端分离**: TypeScript前端 + Python后端
- **模块化设计**: 业务逻辑模块化，支持独立开发测试
- **插件化架构**: 基于VSCode扩展机制，集成度高
- **数据驱动**: 配置化的字段映射和业务规则

### 🚀 性能优化
- **异步处理**: 大数据量导入的异步处理机制
- **缓存机制**: 智能缓存提升查询性能
- **增强日志**: 完整的操作日志和错误追踪
- **错误恢复**: 健壮的错误处理和数据恢复机制

### 🔒 数据安全
- **数据验证**: 多层次的数据完整性验证
- **访问控制**: 基于角色的数据访问控制
- **备份恢复**: 自动化的数据备份和恢复机制
- **审计日志**: 完整的操作审计和变更追踪

## 项目结构

```
ims-viewer/
├── src/                    # TypeScript 插件主入口及 UI 逻辑
│   ├── extension.ts        # 插件激活、命令注册、脚本调用
│   ├── treeDataProvider.ts # 侧边栏树视图，数据库/业务/管理多层级
│   ├── materialWebviewProvider.ts # 物料管理 Webview
│   └── dataEntryWebviewProvider.ts # 数据录入 Webview
├── scripts/                # Python 数据处理与业务脚本
│   ├── parse*.py          # 数据解析脚本（8个业务模块）
│   ├── business_view_*.py  # 业务分析/报表脚本
│   ├── material_manager.py # 物料管理
│   ├── data_entry_handler.py # 数据录入
│   └── parse_manager.py   # 解析管理器
├── webviews/              # Web界面文件
│   ├── data_entry.html    # 数据录入界面
│   ├── material_management.html # 物料管理界面
│   └── inventory_management.html # 库存管理界面
├── field_mapping_dictionary.json # 字段映射与表结构配置
├── package.json           # 插件定义、命令、依赖、配置项
├── requirements.txt       # Python 依赖
└── README.md
```

## 主要命令

### 📥 数据导入
- **Excel转为JSON** (`ims.convertToJson`): 解析Excel文件并转换为JSON格式
- **完整数据迁移流程** (`ims.migrateToNewFormat`): 执行完整的数据导入和迁移
- **导入到MongoDB** (`ims.importToMongodb`): 将数据导入到MongoDB数据库

### 🔍 数据查看
- **刷新树视图** (`ims.refreshTreeView`): 刷新侧边栏数据树
- **显示表数据** (`ims.showTableData`): 查看数据库表内容
- **显示业务视图** (`ims.showBusinessView`): 运行业务分析报表

### 🛠️ 数据管理
- **物料管理** (`ims.showMaterialManagement`): 打开物料管理界面
- **数据录入** (`ims.showDataEntry`): 打开数据录入界面
- **库存管理** (`ims.showInventoryManagement`): 打开库存管理界面
- **添加物料** (`ims.addMaterial`): 快速添加物料

### ⚙️ 系统配置
- **数据库连接** (`ims.reconnectDb`): 重新连接数据库
- **测试连接** (`ims.testDbConnection`): 测试数据库连接
- **打开设置** (`ims.openSettings`): 打开系统配置

## 快速开始

### 环境要求
- **VSCode**: >= 1.74.0
- **Node.js**: >= 16.x
- **Python**: >= 3.8
- **MongoDB**: >= 4.0

### 安装配置
```bash
# 1. 克隆项目
git clone https://github.com/ywfhighlo/ims-viewer.git
cd ims-viewer

# 2. 安装依赖
pip install -r requirements.txt
npm install

# 3. 配置MongoDB连接
# 在VSCode设置中配置数据库参数

# 4. 启动扩展
# 按F5启动调试模式
```

### 使用流程
1. **准备数据**: 整理Excel业务数据文件
2. **导入数据**: 使用`转换为JSON`命令导入数据
3. **查看数据**: 在侧边栏浏览数据库结构
4. **生成报表**: 运行业务视图脚本生成分析报表
5. **数据维护**: 通过管理界面维护基础数据

## 开发指南

### 扩展开发

#### 添加新业务模块
```python
# 1. 创建解析器 scripts/parse9_new_module.py
def parse_new_module_data(file_path):
    # 实现解析逻辑
    pass

# 2. 添加业务视图 scripts/business_view_new_report.py
def generate_new_report():
    # 实现报表逻辑
    pass
```

#### 扩展字段映射
```json
// field_mapping_dictionary.json
{
  "new_module": {
    "chinese_name": "新模块",
    "english_name": "new_module",
    "fields": [...]
  }
}
```

#### 注册新命令
```typescript
// extension.ts
vscode.commands.registerCommand('ims.newCommand', () => {
    // 实现命令逻辑
});
```

### 开发工具
- **实时编译**: `npm run watch`
- **打包发布**: `npm run package`
- **代码规范**: `npm run lint`
- **Python脚本**: 可独立运行，便于调试和扩展

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。

---

如需反馈建议或贡献代码，欢迎访问 [ywfhighlo/ims-viewer](https://github.com/ywfhighlo/ims-viewer) 提交 Issue 或 PR。