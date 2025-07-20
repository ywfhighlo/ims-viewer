import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { exec } from 'child_process';
import { setDatabaseConfigEnv } from './extension';

// 获取数据库名称
function getDatabaseName(): string {
    const config = vscode.workspace.getConfiguration('imsViewer');
    // 完全依赖VSCode设置，不使用硬编码默认值
    return config.get<string>('databaseName') || 'ims_database';
}

// 定义物料项接口
interface Material {
    _id: string;
    material_code: string;
    material_name: string;
    material_model: string;
    unit: string;
}

export class ImsTreeDataProvider implements vscode.TreeDataProvider<vscode.TreeItem> {

    private _onDidChangeTreeData: vscode.EventEmitter<vscode.TreeItem | undefined | null | void> = new vscode.EventEmitter<vscode.TreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<vscode.TreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private isConnected: boolean = false;
    private collections: string[] = [];
    private tableMapping: { [key: string]: string } = {};
    constructor(private context: vscode.ExtensionContext) {
        this.loadTableMapping();
        this.checkConnection();
    }

    private loadTableMapping(): void {
        try {
            const mappingFilePath = path.join(this.context.extensionPath, 'field_mapping_dictionary.json');
            if (fs.existsSync(mappingFilePath)) {
                const mappingData = JSON.parse(fs.readFileSync(mappingFilePath, 'utf8'));
                const tableSchemas = mappingData.table_schemas;
                
                // 从JSON文件中提取表映射关系
                for (const [englishName, schema] of Object.entries(tableSchemas)) {
                    if (schema && typeof schema === 'object' && 'chinese_name' in schema) {
                        this.tableMapping[englishName] = (schema as any).chinese_name;
                    }
                }
                
                console.log('Table mapping loaded:', this.tableMapping);
            } else {
                console.warn('Field mapping dictionary file not found, using default mapping');
                // 如果文件不存在，使用默认映射
                this.tableMapping = {
                    "materials": "物料信息表",
                    "suppliers": "供应商信息表",
                    "customers": "客户信息表",
                    "purchase_params": "进货参数表",
                    "purchase_inbound": "进货入库明细表",
                    "sales_outbound": "销售出库明细表",
                    "payment_details": "付款明细表",
                    "receipt_details": "收款明细表",
                    "inventory_stats": "库存统计表"
                };
            }
        } catch (error) {
            console.error('Error loading table mapping:', error);
            // 出错时使用默认映射
            this.tableMapping = {
                "materials": "物料信息表",
                "suppliers": "供应商信息表",
                "customers": "客户信息表",
                "purchase_params": "进货参数表",
                "purchase_inbound": "进货入库明细表",
                "sales_outbound": "销售出库明细表",
                "payment_details": "付款明细表",
                "receipt_details": "收款明细表",
                "inventory_stats": "库存统计表"
            };
        }
    }

    private async checkConnection(): Promise<void> {
        setDatabaseConfigEnv();

        const pythonPath = "python"; // or a specific path to python executable
        const scriptPath = path.join(this.context.extensionPath, 'scripts', 'get_collection_names.py');
        const command = `${pythonPath} "${scriptPath}"`;

        exec(command, { 
            encoding: 'utf8',
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        }, (error, stdout, stderr) => {
            if (error || stderr) {
                vscode.window.showWarningMessage(`动态获取数据表列表失败，将加载默认列表: ${stderr || '未知错误'}`);
                this.isConnected = true; // 即使动态获取失败，也认为连接是成功的，以便显示默认列表
                this.loadDefaultCollections();
            } else {
                try {
                    const result = JSON.parse(stdout);
                    if (result.error) {
                        vscode.window.showWarningMessage(`获取数据表列表时出错，将加载默认列表: ${result.error}`);
                        this.isConnected = true;
                        this.loadDefaultCollections();
                    } else {
                        this.isConnected = true;
                        this.collections = result.collections || [];
                    }
                } catch (e) {
                    vscode.window.showWarningMessage('解析数据表列表时出错，将加载默认列表。');
                    this.isConnected = true;
                    this.loadDefaultCollections();
                }
            }
            this.refresh();
        });
    }

    private loadDefaultCollections(): void {
        this.collections = Object.keys(this.tableMapping);
    }
    
    async reconnect(): Promise<void> {
        await this.checkConnection();
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: vscode.TreeItem): Promise<vscode.TreeItem[]> {
        if (!this.isConnected) {
            const connectItem = new vscode.TreeItem("数据库未连接 - 点击重新连接", vscode.TreeItemCollapsibleState.None);
            connectItem.iconPath = new vscode.ThemeIcon("error");
            connectItem.command = {
                command: 'ims.reconnectDb',
                title: '重新连接数据库'
            };
            
            const testItem = new vscode.TreeItem("测试数据库连接", vscode.TreeItemCollapsibleState.None);
            testItem.iconPath = new vscode.ThemeIcon("debug-console");
            testItem.command = {
                command: 'ims.testDbConnection',
                title: '测试数据库连接'
            };
            
            return [connectItem, testItem];
        }
        
        // 根节点 - 创建三个并列的一级节点
        if (!element) {
            // 数据库表节点
            const databaseTables = new vscode.TreeItem("数据库表", vscode.TreeItemCollapsibleState.Collapsed);
            databaseTables.iconPath = new vscode.ThemeIcon("database");
            databaseTables.contextValue = "databaseTablesRoot";

            // 业务视图节点
            const businessViews = new vscode.TreeItem("业务视图", vscode.TreeItemCollapsibleState.Collapsed);
            businessViews.iconPath = new vscode.ThemeIcon("graph");
            businessViews.contextValue = "businessViewsRoot";

            // 管理视图节点
            const managementViews = new vscode.TreeItem("管理视图", vscode.TreeItemCollapsibleState.Collapsed);
            managementViews.iconPath = new vscode.ThemeIcon("tools");
            managementViews.contextValue = "managementViewsRoot";

            return [databaseTables, businessViews, managementViews];
        }

        // 子节点 (数据库表列表)
        if (element && element.contextValue === "databaseTablesRoot") {
            return this.getCollectionsAsTreeItems();
        }
        
        // 子节点 (业务视图列表)
        if (element && element.contextValue === "businessViewsRoot") {
            return this.getBusinessViewsAsTreeItems();
        }
        
        // 子节点 (管理视图列表)
        if (element && element.contextValue === "managementViewsRoot") {
            return this.getManagementViewsAsTreeItems();
        }
        


        return [];
    }

    private async getCollectionsAsTreeItems(): Promise<vscode.TreeItem[]> {
        try {
            return this.collections.map((collectionName: string) => {
                const chineseName = this.tableMapping[collectionName] || collectionName;
                const displayName = `${collectionName} (${chineseName})`;
                const item = new vscode.TreeItem(displayName, vscode.TreeItemCollapsibleState.None);
                item.iconPath = new vscode.ThemeIcon("database");
                item.contextValue = "table";
                item.command = {
                    command: 'ims.showTableData',
                    title: '查看表数据',
                    arguments: [collectionName, chineseName]
                };
                return item;
            });
        } catch (e) {
            vscode.window.showErrorMessage(`获取数据表列表失败: ${e}`);
            return [];
        }
    }

    private async getMaterialsAsTreeItems(): Promise<vscode.TreeItem[]> {
        return new Promise((resolve) => {
            const pythonPath = "python"; // or a specific path to python executable
            const scriptPath = path.join(this.context.extensionPath, 'scripts', 'query_table_data.py');
            const command = `${pythonPath} "${scriptPath}" --type materials`;

            exec(command, { 
                encoding: 'utf8',
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            }, (error, stdout, stderr) => {
                if (error) {
                    vscode.window.showErrorMessage(`执行物料查询脚本失败: ${stderr}`);
                    return resolve([]);
                }

                try {
                    // 清理输出，移除可能的重复JSON
                    let cleanOutput = stdout.trim();
                    const lines = cleanOutput.split('\n').filter(line => line.trim());
                    if (lines.length > 1) {
                        // 如果有多行，取最后一行（最新的输出）
                        cleanOutput = lines[lines.length - 1];
                    }
                    
                    const result = JSON.parse(cleanOutput);
                    if (result.error) {
                        vscode.window.showErrorMessage(`查询物料失败: ${result.error}`);
                        return resolve([]);
                    }

                    const materials: Material[] = result.data;
                    if (materials.length === 0) {
                        return resolve([new vscode.TreeItem("暂无物料", vscode.TreeItemCollapsibleState.None)]);
                    }

                    const items = materials.map(m => {
                        const item = new vscode.TreeItem(`${m.material_code} (${m.material_name})`, vscode.TreeItemCollapsibleState.None);
                        item.tooltip = `型号: ${m.material_model}\n单位: ${m.unit}`;
                        item.iconPath = new vscode.ThemeIcon("symbol-field");
                        item.contextValue = "materialItem";
                        return item;
                    });
                    resolve(items);

                } catch (e: any) {
                    vscode.window.showErrorMessage(`解析物料数据失败: ${e.message}\n原始输出: ${stdout}`);
                    resolve([]);
                }
            });
        });
    }

    private async getManagementViewsAsTreeItems(): Promise<vscode.TreeItem[]> {
        // 管理视图列表
        const managementViews = [
            { name: "物料管理", description: "物料信息管理", icon: "package", command: "ims.showMaterialManagement" },
            { name: "进销存管理", description: "采购管理 | 销售管理 | 库存管理", icon: "archive", command: "ims.showInventoryManagement" },
            { name: "数据录入管理", description: "数据录入和编辑", icon: "edit", command: "ims.showDataEntry" }
        ];

        return managementViews.map(view => {
            const item = new vscode.TreeItem(view.name, vscode.TreeItemCollapsibleState.None);
            item.iconPath = new vscode.ThemeIcon(view.icon);
            item.tooltip = view.description;
            item.contextValue = "managementView";
            
            if (view.command === "ims.showInventoryManagement") {
                item.command = {
                    command: 'ims.showInventoryManagement',
                    title: '进销存管理'
                };
            } else if (view.command === "ims.showDataEntry") {
                item.command = {
                    command: 'ims.showDataEntry',
                    title: '数据录入管理'
                };
            } else if (view.command === "ims.showMaterialManagement") {
                item.command = {
                    command: 'ims.showMaterialManagement',
                    title: '物料管理'
                };
            }
            return item;
        });
    }

    private async getBusinessViewsAsTreeItems(): Promise<vscode.TreeItem[]> {
        // 业务视图列表（移除了管理相关的视图）
        const businessViews = [
            { name: "📊 数据分析仪表板", description: "业务数据统计分析和趋势预测", icon: "dashboard", command: "ims.showDataAnalysisDashboard" },
            { name: "供应商对账表", description: "供应商账务汇总", icon: "graph", command: "ims.showBusinessView" },
            { name: "客户对账单", description: "客户账务汇总", icon: "graph", command: "ims.showBusinessView" },
            { name: "库存盘点报表", description: "库存统计分析", icon: "graph", command: "ims.showBusinessView" },
            { name: "销售统计报表", description: "销售数据分析", icon: "graph", command: "ims.showBusinessView" },
            { name: "采购统计报表", description: "采购数据分析", icon: "graph", command: "ims.showBusinessView" },
            { name: "应收账款统计", description: "应收款项汇总", icon: "graph", command: "ims.showBusinessView" },
            { name: "应付账款统计", description: "应付款项汇总", icon: "graph", command: "ims.showBusinessView" }
        ];

        return businessViews.map(view => {
            const item = new vscode.TreeItem(view.name, vscode.TreeItemCollapsibleState.None);
            item.iconPath = new vscode.ThemeIcon(view.icon);
            item.tooltip = view.description;
            item.contextValue = "businessView";
            
            // 特殊处理数据分析仪表板
            if (view.command === "ims.showDataAnalysisDashboard") {
                item.command = {
                    command: view.command,
                    title: view.name
                };
            } else {
                item.command = {
                    command: view.command,
                    title: view.name,
                    arguments: [view.name, view.name]
                };
            }
            
            return item;
        });
    }
}