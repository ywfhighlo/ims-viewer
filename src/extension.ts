import * as vscode from 'vscode';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';
import { spawn } from 'child_process';
import { ImsTreeDataProvider } from './treeDataProvider';
import { MaterialWebviewProvider } from './materialWebviewProvider';
import { DataEntryWebviewProvider } from './dataEntryWebviewProvider';
import { CustomerManagementWebviewProvider } from './customerManagementWebviewProvider';
import { SupplierManagementWebviewProvider } from './supplierManagementWebviewProvider';

let outputChannel: vscode.OutputChannel;

// 动态检测Python命令
function getPythonCommand(context: vscode.ExtensionContext): string {
    // 优先使用虚拟环境中的Python
    const venvPythonPath = path.join(context.extensionPath, '.venv', 'bin', 'python');
    const venvPythonPathWin = path.join(context.extensionPath, '.venv', 'Scripts', 'python.exe');
    const venvPython3Path = path.join(context.extensionPath, '.venv', 'bin', 'python3');
    
    // 检查虚拟环境中的Python是否存在
    if (fs.existsSync(venvPythonPath)) {
        return venvPythonPath;
    }
    if (fs.existsSync(venvPython3Path)) {
        return venvPython3Path;
    }
    if (fs.existsSync(venvPythonPathWin)) {
        return venvPythonPathWin;
    }
    
    // 根据操作系统选择合适的Python命令，并提供多个回退选项
    const platform = os.platform();
    if (platform === 'win32') {
        // Windows系统的回退顺序：python -> py -> python3
        const candidates = ['python', 'py', 'python3'];
        return candidates[0]; // 先尝试第一个，如果失败会在错误处理中尝试其他选项
    } else {
        // macOS和Linux系统的回退顺序：python3 -> python
        const candidates = ['python3', 'python'];
        return candidates[0]; // 先尝试第一个，如果失败会在错误处理中尝试其他选项
    }
}

// 获取Python命令的回退选项
function getPythonCommandFallbacks(context: vscode.ExtensionContext): string[] {
    const platform = os.platform();
    if (platform === 'win32') {
        return ['python', 'py', 'python3'];
    } else {
        return ['python3', 'python'];
    }
}

// 获取数据库名称
function getDatabaseName(excelFilePath?: string): string {
    const config = vscode.workspace.getConfiguration('imsViewer');
    // 完全依赖VSCode设置，不使用硬编码默认值
    return config.get<string>('databaseName') || 'ims_database';
}

// 设置数据库配置到环境变量
export function setDatabaseConfigEnv(excelFilePath?: string) {
    const config = vscode.workspace.getConfiguration('imsViewer');
    
    // 设置数据库名称
    const dbName = getDatabaseName(excelFilePath);
    process.env.IMS_DB_NAME = dbName;
    
    // 设置MongoDB连接配置
    const mongoUri = config.get<string>('mongoUri', 'mongodb://localhost:27017/');
    const mongoUsername = config.get<string>('mongoUsername', '');
    const mongoPassword = config.get<string>('mongoPassword', '');
    const mongoAuthDatabase = config.get<string>('mongoAuthDatabase', 'admin');
    
    process.env.IMS_MONGO_URI = mongoUri;
    if (mongoUsername) {
        process.env.IMS_MONGO_USERNAME = mongoUsername;
    }
    if (mongoPassword) {
        process.env.IMS_MONGO_PASSWORD = mongoPassword;
    }
    if (mongoAuthDatabase) {
        process.env.IMS_MONGO_AUTH_DB = mongoAuthDatabase;
    }
}

// 获取操作名称的中文显示
function getActionName(action: string): string {
    const actionNames: { [key: string]: string } = {
        'purchase_order': '采购订单',
        'purchase_receipt': '采购入库',
        'purchase_return': '采购退货',
        'purchase_report': '采购报表',
        'sales_order': '销售订单',
        'sales_delivery': '销售出库',
        'sales_return': '销售退货',
        'sales_report': '销售报表',
        'inventory_check': '库存盘点',
        'inventory_transfer': '库存调拨',
        'inventory_report': '库存报表',
        'stock_alert': '库存预警'
    };
    
    return actionNames[action] || action;
}

// 处理库存管理相关操作
function handleInventoryAction(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, message: any) {
    // 处理库存管理相关的操作
    // 这里可以根据具体的action类型进行不同的处理
    vscode.window.showInformationMessage(`收到库存管理操作: ${message.action}`);
}

// ... (rest of the code remains the same)

export function activate(context: vscode.ExtensionContext) {
    // 1. Create an output channel for detailed logs
    outputChannel = vscode.window.createOutputChannel("IMS Import Logs");

    // 2. Register file-based commands
    const convertToJsonCommand = vscode.commands.registerCommand('ims.convertToJson', (uri: vscode.Uri) => {
        if (!uri) {
            vscode.window.showErrorMessage('请在文件浏览器中右键点击一个Excel文件来执行此命令。');
            return;
        }
        const excelPath = uri.fsPath;
        runExcelToJsonProcess(context, excelPath);
    });
    
    const migrateCommand = vscode.commands.registerCommand('ims.migrateToNewFormat', (uri: vscode.Uri) => {
        if (!uri) {
            vscode.window.showErrorMessage('请在文件浏览器中右键点击一个Excel文件来执行此命令。');
            return;
        }
        const excelPath = uri.fsPath;
        runMigrationProcess(context, excelPath);
    });

    // 3. Register the Tree View provider
    const imsProvider = new ImsTreeDataProvider(context);
    vscode.window.registerTreeDataProvider('ims-viewer', imsProvider);

    // 4. Register Webview Providers and their commands
    const materialProvider = new MaterialWebviewProvider(context);
    const showMaterialManagementCommand = vscode.commands.registerCommand('ims.showMaterialManagement', () => {
        materialProvider.show();
    });
    
    const dataEntryProvider = new DataEntryWebviewProvider(context);
    const showDataEntryCommand = vscode.commands.registerCommand('ims.showDataEntry', () => {
        dataEntryProvider.show();
    });

    const customerManagementProvider = new CustomerManagementWebviewProvider(context);
    const showCustomerManagementCommand = vscode.commands.registerCommand('ims-viewer.showCustomerManagement', () => {
        customerManagementProvider.show();
    });

    const supplierManagementProvider = new SupplierManagementWebviewProvider(context);
    const showSupplierManagementCommand = vscode.commands.registerCommand('ims-viewer.showSupplierManagement', () => {
        supplierManagementProvider.show();
    });

    // 5. Register other utility and view commands
    const refreshCommand = vscode.commands.registerCommand('ims.refreshTreeView', () => {
        imsProvider.refresh();
    });
    
    const reconnectCommand = vscode.commands.registerCommand('ims.reconnectDb', async () => {
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 尝试重新连接数据库...`);
        await imsProvider.reconnect();
    });
    
    const testDbCommand = vscode.commands.registerCommand('ims.testDbConnection', () => {
        runDatabaseTest(context);
    });
    
    const showTableDataCommand = vscode.commands.registerCommand('ims.showTableData', (tableName: string, chineseName: string) => {
        showTableDataPanel(context, tableName, chineseName);
    });
    
    const showBusinessViewCommand = vscode.commands.registerCommand('ims.showBusinessView', (viewName: string, chineseName: string) => {
        showBusinessViewPanel(context, viewName, chineseName);
    });
    
    const addMaterialCommand = vscode.commands.registerCommand('ims.addMaterial', () => {
        showAddMaterialDialog(context);
    });
    
    const openSettingsCommand = vscode.commands.registerCommand('ims.openSettings', () => {
        vscode.commands.executeCommand('workbench.action.openSettings', 'imsViewer');
    });

    const showInventoryManagementCommand = vscode.commands.registerCommand('ims.showInventoryManagement', () => {
        showInventoryManagementPanel(context);
    });

    const showDataAnalysisDashboardCommand = vscode.commands.registerCommand('ims.showDataAnalysisDashboard', () => {
        showDataAnalysisDashboard(context);
    });

    // 6. Push all subscriptions
    context.subscriptions.push(
        convertToJsonCommand,
        migrateCommand,
        refreshCommand, 
        reconnectCommand, 
        testDbCommand, 
        showTableDataCommand, 
        showBusinessViewCommand, 
        addMaterialCommand,
        showMaterialManagementCommand, 
        showDataEntryCommand, 
        showInventoryManagementCommand, 
        showCustomerManagementCommand,
        showSupplierManagementCommand,
        showDataAnalysisDashboardCommand,
        openSettingsCommand
    );
}

// 获取 `docs` 目录的函数，具有正确的优先级
function getDocsDirectory(context: vscode.ExtensionContext): string {
    const config = vscode.workspace.getConfiguration('imsViewer');

    // 1. 优先使用 VSCode 设置中的路径
    const settingsPath = config.get<string>('docsPath');
    if (settingsPath && path.isAbsolute(settingsPath) && fs.existsSync(settingsPath)) {
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 使用来自设置的 docs 目录: ${settingsPath}`);
        return settingsPath;
    }

    // 2. 其次，检查工作区（开发目录）下的 `docs` 目录
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        const workspaceDocsPath = path.join(workspaceFolder.uri.fsPath, 'docs');
        if (fs.existsSync(workspaceDocsPath)) {
            outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 使用来自工作区的 docs 目录: ${workspaceDocsPath}`);
            return workspaceDocsPath;
        }
    }

    // 3. 最后，回退到扩展目录下的 `docs` 目录
    const extensionDocsPath = path.join(context.extensionPath, 'docs');
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 使用来自扩展的 docs 目录: ${extensionDocsPath}`);
    return extensionDocsPath;
}

// 获取输出目录配置
function getOutputDirectory(context: vscode.ExtensionContext): string {
    const config = vscode.workspace.getConfiguration('imsViewer');
    const outputMode = config.get<string>('outputMode', 'development');
    const customOutputPath = config.get<string>('customOutputPath', '');
    
    // 如果用户设置了自定义路径，优先使用自定义路径（不管outputMode是什么）
    if (customOutputPath) {
        return customOutputPath;
    } else if (outputMode === 'temp') {
        // 使用临时目录
        const tempDir = path.join(os.tmpdir(), 'ims-viewer-data');
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }
        return tempDir;
    } else {
        // 开发模式：使用扩展目录下的docs
        return path.join(context.extensionPath, 'docs');
    }
}

// 创建开发模式的符号链接或快捷方式
function createDevModeLink(context: vscode.ExtensionContext, actualOutputDir: string) {
    const config = vscode.workspace.getConfiguration('imsViewer');
    const outputMode = config.get<string>('outputMode', 'development');
    
    if (outputMode !== 'development') {
        const devDocsDir = path.join(context.extensionPath, 'docs');
        const linkPath = path.join(devDocsDir, 'current-output-link.txt');
        
        try {
            // 创建一个文本文件指向实际输出目录
            fs.writeFileSync(linkPath, `当前输出目录: ${actualOutputDir}\n\n` +
                `要查看生成的JSON文件，请访问上述目录。\n` +
                `或者在VS Code设置中将输出模式改为'development'以在docs目录中查看文件。`);
        } catch (error) {
            // 忽略错误，这只是一个便利功能
        }
    }
}

async function runExcelToJsonProcess(context: vscode.ExtensionContext, excelPath: string) {
    outputChannel.clear();
    outputChannel.show(true); // 自动显示输出通道
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 开始Excel转JSON流程: ${excelPath}`);

    // 获取配置的输出目录
    const docsDir = getDocsDirectory(context);
    const outputPath = path.join(docsDir, 'parsed_data.json');
    
    // 显示输出目录信息
    const config = vscode.workspace.getConfiguration('imsViewer');
    const outputMode = config.get<string>('outputMode', 'development');
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 输出模式: ${outputMode}`);
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 输出目录: ${docsDir}`);
    
    // 确保输出目录存在
    if (!fs.existsSync(docsDir)) {
        fs.mkdirSync(docsDir, { recursive: true });
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 已创建输出目录: ${docsDir}`);
    }
    
    try {
        // 第一步：解析Excel文件并生成JSON分表
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] === 步骤1: 解析Excel文件 ===`);
        await runScript(
            context,
            'parse_manager.py', 
            [excelPath, outputPath], 
            'Excel转JSON: 解析Excel文件并生成JSON分表'
        );
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ✅ 步骤1完成：JSON分表已生成`);

        // 第二步：生成标准物料编码表和映射
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] === 步骤2: 生成物料编码映射 ===`);
        await runScript(
            context,
            'generate_standard_material_table.py', 
            ['--docs-dir', docsDir], 
            '生成标准物料编码表和映射关系'
        );
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ✅ 步骤2完成：物料编码映射已生成`);

        // 创建开发模式链接（如果不在开发模式）
        createDevModeLink(context, docsDir);

        vscode.window.showInformationMessage(`✅ ${path.basename(excelPath)} 已成功转换为JSON格式并生成物料映射！`);
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] ✅ Excel转JSON流程成功完成。`);
        outputChannel.appendLine(`\n生成的文件位于: ${docsDir}`);
        outputChannel.appendLine(`- materials.json (物料信息)`);
        outputChannel.appendLine(`- purchase_params.json (进货参数)`);
        outputChannel.appendLine(`- purchase_inbound.json (进货入库)`);
        outputChannel.appendLine(`- sales_outbound.json (销售出库)`);
        outputChannel.appendLine(`- standard_material_table.json (标准物料编码表)`);
        outputChannel.appendLine(`- standard_material_table.json (标准物料编码表)`);
        outputChannel.appendLine(`- 以及其他相关JSON文件`);
        
        if (outputMode !== 'development') {
            outputChannel.appendLine(`\n💡 提示: 当前使用${outputMode}模式，JSON文件不在扩展的docs目录中。`);
            outputChannel.appendLine(`   如需在开发时查看文件，可以:`);
            outputChannel.appendLine(`   1. 直接访问上述输出目录`);
            outputChannel.appendLine(`   2. 或在设置中将输出模式改为'development'`);
        }
        
        outputChannel.appendLine(`\n请检查所有JSON文件确保数据正确，然后可以执行第二步数据迁移。`);

    } catch (error: any) {
        vscode.window.showErrorMessage(`Excel转JSON失败: ${error.message}. 详情请查看 "IMS Import Logs" 输出窗口。`);
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] ❌ Excel转JSON流程失败: ${error.message}`);
    }
}

async function runMigrationProcess(context: vscode.ExtensionContext, excelPath: string) {
    outputChannel.clear();
    outputChannel.show(true); // 自动显示输出通道
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 开始完整数据迁移流程: ${excelPath}`);
    outputChannel.appendLine(`注意：此流程假设JSON文件已通过"Excel转为JSON"功能生成`);

    // 获取并设置数据库配置
    setDatabaseConfigEnv(excelPath);
    const dbName = getDatabaseName(excelPath);
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 使用数据库: ${dbName}`);
    
    // 显示数据库连接配置（不显示密码）
    const config = vscode.workspace.getConfiguration('imsViewer');
    const mongoUri = config.get<string>('mongoUri', 'mongodb://localhost:27017/');
    const mongoUsername = config.get<string>('mongoUsername', '');
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] MongoDB URI: ${mongoUri}`);
    if (mongoUsername) {
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] MongoDB 用户名: ${mongoUsername}`);
    }

    try {
        // 第一步：导入数据到MongoDB（带标准编码）
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] === 第一步：导入数据到MongoDB ===`);
        
        await runScript(
            context,
            'import_to_mongodb_with_standard_codes.py', 
            [], 
            '步骤 2: 导入数据到MongoDB（应用标准编码）'
        );
        
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ✅ 第一步完成：数据已导入MongoDB`);
        
        // 第二步：验证导入结果
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] === 第二步：验证导入结果 ===`);
        
        await runScript(
            context,
            'verify_import.py', 
            [], 
            '步骤 3: 验证数据导入结果'
        );
        
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ✅ 第二步完成：导入验证已完成`);

        vscode.window.showInformationMessage(`✅ ${path.basename(excelPath)} 的完整数据迁移已成功完成！`);
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] ✅ 完整数据迁移流程成功完成。`);
        outputChannel.appendLine(`\n使用的文件：`);
        outputChannel.appendLine(`- docs/standard_material_table.json (完整物料数据)`);
        outputChannel.appendLine(`- docs/standard_material_table.sql (SQL插入脚本)`);
        outputChannel.appendLine(`- docs/standard_material_table.json (标准物料编码表)`);
        outputChannel.appendLine(`- 以及其他JSON分表文件`);
        outputChannel.appendLine(`\n数据库导入：`);
        outputChannel.appendLine(`- MongoDB数据库: ${dbName}`);
        outputChannel.appendLine(`- 包含标准编码的完整数据集`);

    } catch (error: any) {
        vscode.window.showErrorMessage(`完整迁移失败: ${error.message}. 详情请查看 "IMS Import Logs" 输出窗口。`);
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] ❌ 完整数据迁移流程失败: ${error.message}`);
    }
}

function runScript(context: vscode.ExtensionContext, scriptName: string, args: string[], stepName: string): Promise<void> {
    return new Promise((resolve, reject) => {
        // The extension's root is now the project root.
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, scriptName);
        const pythonCmd = getPythonCommand(context);

        outputChannel.appendLine(`\n--- ${stepName} ---`);
        outputChannel.appendLine(`> ${pythonCmd} "${scriptPath}" ${args.map(a => `"${a}"`).join(' ')}`);
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : process.cwd();
        
        // 设置环境变量，包括工作区路径
        const env = { 
            ...process.env, 
            PYTHONIOENCODING: 'utf-8',
            IMS_WORKSPACE_PATH: workspacePath  // 新增：传递工作区路径
        };
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: env
        });

        pythonProcess.stdout.on('data', (data: Buffer) => {
            outputChannel.append(data.toString());
        });

        pythonProcess.stderr.on('data', (data: Buffer) => {
            outputChannel.append(`[错误] ${data.toString()}`);
        });

        pythonProcess.on('error', (err) => {
            reject(new Error(`无法启动脚本 '${scriptName}': ${err.message}. 请确保Python环境已正确配置在系统PATH中。`));
        });

        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                outputChannel.appendLine(`--- ${stepName} 成功 ---`);
                resolve();
            } else {
                reject(new Error(`脚本 '${scriptName}' 执行失败，退出码: ${code}.`));
            }
        });
    });
}

function runDatabaseTest(context: vscode.ExtensionContext) {
    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 开始数据库连接测试...`);
    
    // 设置数据库配置环境变量
    setDatabaseConfigEnv();
    
    const scriptsDir = path.join(context.extensionPath, 'scripts');
    const scriptPath = path.join(scriptsDir, 'test_db_connection.py');
    const pythonCmd = getPythonCommand(context);
    
    outputChannel.appendLine(`> ${pythonCmd} "${scriptPath}"`);
    
    // 获取当前工作区路径
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : process.cwd();
    
    const pythonProcess = spawn(pythonCmd, [scriptPath], {
        env: { 
            ...process.env, 
            PYTHONIOENCODING: 'utf-8',
            IMS_WORKSPACE_PATH: workspacePath
        }
    });
    
    pythonProcess.stdout.on('data', (data: Buffer) => {
        outputChannel.append(data.toString());
    });
    
    pythonProcess.stderr.on('data', (data: Buffer) => {
        outputChannel.append(`[错误] ${data.toString()}`);
    });
    
    pythonProcess.on('error', (err) => {
        outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] ❌ 无法启动测试脚本: ${err.message}`);
        outputChannel.appendLine(`请确保Python环境已正确配置在系统PATH中。`);
        vscode.window.showErrorMessage(`无法启动数据库测试: ${err.message}`);
    });
    
    pythonProcess.on('close', (code: number) => {
        if (code === 0) {
            outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] ✅ 数据库测试完成`);
            vscode.window.showInformationMessage('数据库测试完成，请查看输出窗口了解详情。');
        } else {
            outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] ❌ 数据库测试失败，退出码: ${code}`);
            vscode.window.showWarningMessage('数据库测试发现问题，请查看输出窗口了解详情。');
        }
    });
}

function showTableDataPanel(context: vscode.ExtensionContext, tableName: string, chineseName: string) {
    // 在创建面板之前，先设置好数据库连接环境变量
    setDatabaseConfigEnv();

    const panel = vscode.window.createWebviewPanel(
        'imsTableData',
        `${chineseName} (${tableName})`,
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    panel.webview.html = getWebviewContent(tableName, chineseName, context);
    
    // 处理来自webview的消息
    panel.webview.onDidReceiveMessage(
        message => {
            switch (message.command) {
                case 'loadData':
                    loadTableData(context, panel, tableName);
                    return;
                case 'refresh':
                    loadTableData(context, panel, tableName);
                    return;
                case 'addRecord':
                    handleCrudOperation(context, panel, tableName, 'add', message.data);
                    return;
                case 'updateRecord':
                    handleCrudOperation(context, panel, tableName, 'update', message.data);
                    return;
                case 'deleteRecord':
                    // 将id转换为_id格式，以匹配MongoDB的文档ID字段
                    const deleteData = { _id: message.id, type: message.type };
                    handleCrudOperation(context, panel, tableName, 'delete', deleteData);
                    return;
            }
        },
        undefined,
        context.subscriptions
    );
    
    // 注意：数据加载由webview的JavaScript自动触发，无需在此处调用
}

function showBusinessViewPanel(context: vscode.ExtensionContext, viewName: string, chineseName: string) {
    const panel = vscode.window.createWebviewPanel(
        'imsBusinessView',
        `${chineseName}`,
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    panel.webview.html = getBusinessViewWebviewContent(viewName, chineseName);
    
    // 处理来自webview的消息
    panel.webview.onDidReceiveMessage(
        message => {
            switch (message.command) {
                case 'loadData':
                    loadBusinessViewData(context, panel, viewName);
                    return;
                case 'refresh':
                    loadBusinessViewData(context, panel, viewName);
                    return;
                case 'filter':
                    loadBusinessViewData(context, panel, viewName, message.params);
                    return;
            }
        },
        undefined,
        context.subscriptions
    );
}

function handleCrudOperation(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, tableName: string, operation: string, data: any) {
    const scriptsDir = path.join(context.extensionPath, 'scripts');
    const scriptPath = path.join(scriptsDir, 'crud_operations.py');
    const pythonCmd = getPythonCommand(context);
    
    // 设置数据库配置环境变量
    setDatabaseConfigEnv();
    
    const args = ['--table', tableName, '--operation', operation, '--data', JSON.stringify(data)];
    
    // 获取当前工作区路径
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : process.cwd();
    
    const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
        env: { 
            ...process.env, 
            PYTHONIOENCODING: 'utf-8',
            IMS_WORKSPACE_PATH: workspacePath
        }
    });
    
    let stdoutData = '';
    let errorOutput = '';
    
    pythonProcess.stdout.on('data', (data: Buffer) => {
        stdoutData += data.toString();
    });
    
    pythonProcess.stderr.on('data', (data: Buffer) => {
        errorOutput += data.toString();
    });
    
    pythonProcess.on('error', (err) => {
        panel.webview.postMessage({ 
            command: 'operationResult', 
            success: false,
            message: `无法启动CRUD脚本: ${err.message}` 
        });
    });
    
    pythonProcess.on('close', (code: number) => {
        if (code === 0) {
            try {
                const result = JSON.parse(stdoutData.trim());
                
                // 根据操作类型发送不同的命令
                let command = 'operationResult';
                if (operation === 'delete') {
                    command = 'recordDeleted';
                } else if (operation === 'update') {
                    command = 'recordUpdated';
                } else if (operation === 'create') {
                    command = 'recordSaved';
                }
                
                panel.webview.postMessage({ 
                    command: command, 
                    success: result.success,
                    message: result.message || `${operation}操作完成`,
                    data: result.data,
                    type: data.type || tableName
                });
                
                // 操作成功后刷新数据
                if (result.success) {
                    loadTableData(context, panel, tableName);
                }
            } catch (e) {
                panel.webview.postMessage({ 
                    command: 'error', 
                    message: `操作结果解析失败: ${e}` 
                });
            }
        } else {
            panel.webview.postMessage({ 
                command: 'error', 
                message: `操作失败: ${errorOutput || '未知错误'}` 
            });
        }
    });
}

function loadTableData(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, tableName: string) {
    const scriptsDir = path.join(context.extensionPath, 'scripts');
    const scriptPath = path.join(scriptsDir, 'query_table_data.py');
    const pythonCmd = getPythonCommand(context);
    
    // 修正：使用新的参数格式
    const args = ['--type', 'table', '--name', tableName];

    // 显示加载状态
    panel.webview.postMessage({ command: 'loading', data: true });
    
    // 获取当前工作区路径
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : process.cwd();
    
    const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
        env: { 
            ...process.env, 
            PYTHONIOENCODING: 'utf-8',
            IMS_WORKSPACE_PATH: workspacePath
        }
    });
    
    let stdoutData = '';
    let errorOutput = '';
    
    pythonProcess.stdout.on('data', (data: Buffer) => {
        stdoutData += data.toString();
    });
    
    pythonProcess.stderr.on('data', (data: Buffer) => {
        errorOutput += data.toString();
    });
    
    pythonProcess.on('error', (err) => {
        panel.webview.postMessage({ 
            command: 'error', 
            data: `无法启动查询脚本: ${err.message}` 
        });
    });
    
    pythonProcess.on('close', (code: number) => {
        panel.webview.postMessage({ command: 'loading', data: false });
        
        if (code === 0) {
            try {
                // 清理输出数据，移除重复的JSON
                let cleanOutput = stdoutData.trim();
                
                // 如果输出包含多个JSON对象，只取第一个
                const jsonStart = cleanOutput.indexOf('{');
                const jsonEnd = cleanOutput.lastIndexOf('}');
                if (jsonStart !== -1 && jsonEnd !== -1) {
                    // 尝试找到完整的JSON对象
                    let braceCount = 0;
                    let endIndex = jsonStart;
                    for (let i = jsonStart; i <= jsonEnd; i++) {
                        if (cleanOutput[i] === '{') braceCount++;
                        if (cleanOutput[i] === '}') braceCount--;
                        if (braceCount === 0) {
                            endIndex = i;
                            break;
                        }
                    }
                    cleanOutput = cleanOutput.substring(jsonStart, endIndex + 1);
                }
                
                const jsonData = JSON.parse(cleanOutput);
                panel.webview.postMessage({ 
                    command: 'data', 
                    data: jsonData 
                });
            } catch (e) {
                panel.webview.postMessage({ 
                    command: 'error', 
                    data: `数据解析失败: ${e}\n原始输出: ${stdoutData}` 
                });
            }
        } else {
            panel.webview.postMessage({ 
                command: 'error', 
                data: `查询失败: ${errorOutput || '未知错误'}` 
            });
        }
    });
}

function getWebviewContent(tableName: string, chineseName: string, context: vscode.ExtensionContext): string {
    // 读取字段映射字典
    const mappingPath = path.join(context.extensionPath, 'field_mapping_dictionary.json');
    let fieldMapping: { [key: string]: string } = {};
    try {
        const mappingContent = require('fs').readFileSync(mappingPath, 'utf8');
        const mappingData = JSON.parse(mappingContent);
        // 创建英文到中文的映射
        for (const [chinese, info] of Object.entries(mappingData.field_dictionary)) {
            if (info && typeof info === 'object' && 'english' in info) {
                fieldMapping[(info as any).english] = chinese;
            }
        }
    } catch (e) {
        console.error('Failed to load field mapping:', e);
    }
    
    // 读取字体大小配置
    const config = vscode.workspace.getConfiguration('imsViewer');
    const fontSize = config.get<number>('tableFontSize', 12);
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${chineseName}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 4px;
            background-color: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3px;
            padding-bottom: 2px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .title-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .title {
            font-size: 10px;
            font-weight: bold;
        }
        .subtitle {
            font-size: 8px;
            color: var(--vscode-descriptionForeground);
        }
        .controls {
            display: flex;
            gap: 10px;
        }
        button {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 2px 6px;
            border-radius: 2px;
            cursor: pointer;
            font-size: 9px;
        }
        button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: var(--vscode-descriptionForeground);
            font-size: 9px;
        }
        .error {
            background-color: var(--vscode-inputValidation-errorBackground);
            color: var(--vscode-inputValidation-errorForeground);
            border: 1px solid var(--vscode-inputValidation-errorBorder);
            padding: 8px;
            border-radius: 2px;
            margin: 10px 0;
            font-size: 9px;
        }
        .data-container {
            overflow: auto;
            max-height: calc(100vh - 120px);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background-color: var(--vscode-editor-background);
        }
        th, td {
            padding: 2px 4px;
            text-align: left;
            border-bottom: 1px solid var(--vscode-panel-border);
            font-size: ${fontSize}px;
            line-height: 1.1;
        }
        th {
            background-color: var(--vscode-list-hoverBackground);
            font-weight: bold;
            position: sticky;
            top: 0;
            font-size: ${fontSize}px;
        }
        tr:hover {
            background-color: var(--vscode-list-hoverBackground);
        }
        .stats {
            margin-top: 4px;
            padding: 3px 6px;
            background-color: var(--vscode-textBlockQuote-background);
            border-left: 2px solid var(--vscode-textBlockQuote-border);
            font-size: 9px;
        }
        .empty {
            text-align: center;
            padding: 20px;
            color: var(--vscode-descriptionForeground);
            font-size: 9px;
        }
        .action-buttons {
            white-space: nowrap;
        }
        .action-buttons button {
            margin-right: 5px;
            padding: 1px 4px;
            font-size: 8px;
        }
        .btn-edit {
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        .btn-delete {
            background-color: var(--vscode-errorForeground);
            color: white;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: var(--vscode-editor-background);
            margin: 5% auto;
            padding: 20px;
            border: 1px solid var(--vscode-panel-border);
            width: 80%;
            max-width: 600px;
            border-radius: 4px;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .close {
            color: var(--vscode-descriptionForeground);
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: var(--vscode-editor-foreground);
        }
        .form-group {
            margin-bottom: 10px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-size: 10px;
            font-weight: bold;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 5px;
            border: 1px solid var(--vscode-input-border);
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            font-size: 10px;
            border-radius: 2px;
        }
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 15px;
        }
        .notification {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 10px 15px;
            border-radius: 4px;
            font-size: 10px;
            z-index: 1001;
            display: none;
        }
        .notification.success {
            background-color: var(--vscode-terminal-ansiGreen);
            color: white;
        }
        .notification.error {
            background-color: var(--vscode-errorForeground);
            color: white;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="title-container">
            <span class="title">${chineseName}</span>
            <span class="subtitle">表名: ${tableName}</span>
        </div>
        <div class="controls">
            <button onclick="showAddForm()">添加记录</button>
            <button onclick="refreshData()">刷新数据</button>
        </div>
    </div>
    
    <div id="content">
        <div class="loading">正在加载数据...</div>
    </div>
    
    <!-- 添加/编辑记录模态框 -->
    <div id="recordModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">添加记录</h3>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <form id="recordForm">
                <div id="formFields"></div>
                <div class="form-actions">
                    <button type="button" onclick="closeModal()">取消</button>
                    <button type="submit">保存</button>
                </div>
            </form>
        </div>
    </div>
    
    <!-- 通知消息 -->
    <div id="notification" class="notification"></div>
    
    <script>
        const vscode = acquireVsCodeApi();
        const fieldMapping = ${JSON.stringify(fieldMapping)};
        
        function refreshData() {
            vscode.postMessage({ command: 'refresh' });
        }
        
        let currentData = [];
        let currentFields = [];
        let editingRecord = null;
        
        window.addEventListener('message', event => {
            const message = event.data;
            const content = document.getElementById('content');
            
            switch (message.command) {
                case 'loading':
                    if (message.data) {
                        content.innerHTML = '<div class="loading">正在加载数据...</div>';
                    }
                    break;
                    
                case 'error':
                    content.innerHTML = '<div class="error">错误: ' + message.data + '</div>';
                    break;
                    
                case 'data':
                    displayData(message.data);
                    break;
                    
                case 'operationResult':
                    showNotification(message.message, message.success ? 'success' : 'error');
                    if (message.success) {
                        closeModal();
                    }
                    break;
            }
        });
        
        function displayData(result) {
            const content = document.getElementById('content');
            
            // 处理错误情况
            if (result.error) {
                content.innerHTML = '<div class="error">错误: ' + result.error + '</div>';
                return;
            }
            
            // 获取数据数组
            const data = result.data || [];
            
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div class="empty">暂无数据</div>';
                return;
            }
            
            // 获取所有字段名
            const fields = new Set();
            data.forEach(row => {
                Object.keys(row).forEach(key => fields.add(key));
            });
            // 过滤掉 _id 字段
            const fieldArray = Array.from(fields).filter(f => f !== '_id');
            
            // 保存当前数据和字段信息
            currentData = data;
            currentFields = fieldArray;
            
            // 生成表格
            let html = '<div class="data-container"><table>';
            
            // 表头
            html += '<thead><tr>';
            fieldArray.forEach(field => {
                const displayName = fieldMapping[field] || field;
                html += '<th>' + displayName + '</th>';
            });
            html += '<th>操作</th>';
            html += '</tr></thead>';
            
            // 数据行
            html += '<tbody>';
            data.forEach((row, index) => {
                html += '<tr>';
                fieldArray.forEach(field => {
                    const value = row[field];
                    const displayValue = value !== null && value !== undefined ? String(value) : '';
                    html += '<td>' + displayValue + '</td>';
                });
                // 操作按钮
                html += '<td class="action-buttons">';
                html += '<button class="btn-edit" onclick="editRecord(' + index + ')">编辑</button>';
                html += '<button class="btn-delete" onclick="deleteRecord(' + index + ')">删除</button>';
                html += '</td>';
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            
            // 统计信息
            const totalRecords = result.total || data.length;
            const displayedRecords = result.displayed || data.length;
            html += '<div class="stats">显示 ' + displayedRecords + ' 条记录，共 ' + totalRecords + ' 条，' + fieldArray.length + ' 个字段</div>';
            
            content.innerHTML = html;
        }
        
        // CRUD操作函数
        function showAddForm() {
            editingRecord = null;
            document.getElementById('modalTitle').textContent = '添加记录';
            generateForm();
            document.getElementById('recordModal').style.display = 'block';
        }
        
        function editRecord(index) {
            editingRecord = currentData[index];
            document.getElementById('modalTitle').textContent = '编辑记录';
            generateForm(editingRecord);
            document.getElementById('recordModal').style.display = 'block';
        }
        
        function deleteRecord(index) {
            if (confirm('确定要删除这条记录吗？')) {
                const record = currentData[index];
                vscode.postMessage({ 
                    command: 'deleteRecord', 
                    data: { _id: record._id } 
                });
            }
        }
        
        function generateForm(record = null) {
            const formFields = document.getElementById('formFields');
            formFields.innerHTML = '';
            
            currentFields.forEach(field => {
                if (field === '_id') return; // 跳过_id字段
                
                const formGroup = document.createElement('div');
                formGroup.className = 'form-group';
                
                const label = document.createElement('label');
                label.textContent = fieldMapping[field] || field;
                
                const input = document.createElement('input');
                input.type = 'text';
                input.name = field;
                input.value = record ? (record[field] || '') : '';
                
                formGroup.appendChild(label);
                formGroup.appendChild(input);
                formFields.appendChild(formGroup);
            });
        }
        
        function closeModal() {
            document.getElementById('recordModal').style.display = 'none';
            editingRecord = null;
        }
        
        function showNotification(message, type) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = 'notification ' + type;
            notification.style.display = 'block';
            
            setTimeout(() => {
                notification.style.display = 'none';
            }, 3000);
        }
        
        // 表单提交处理
        document.getElementById('recordForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {};
            
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            
            if (editingRecord) {
                // 编辑模式
                data._id = editingRecord._id;
                vscode.postMessage({ 
                    command: 'updateRecord', 
                    data: data 
                });
            } else {
                // 添加模式
                vscode.postMessage({ 
                    command: 'addRecord', 
                    data: data 
                });
            }
        });
        
        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('recordModal');
            if (event.target === modal) {
                closeModal();
            }
        }
        
        // 页面加载完成后请求数据
        vscode.postMessage({ command: 'loadData' });
    </script>
</body>
</html>`;
}

function loadBusinessViewData(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, viewName: string, params?: any) {
    const scriptsDir = path.join(context.extensionPath, 'scripts');
    let scriptPath = '';
    let args: string[] = [];
    
    // 根据业务视图名称选择对应的脚本
    switch (viewName) {
        case '供应商对账表':
            scriptPath = path.join(scriptsDir, 'business_view_supplier_reconciliation.py');
            // 构建命名参数
            args = [];
            if (params?.startDate) {
                args.push('--start_date', params.startDate);
            }
            if (params?.endDate) {
                args.push('--end_date', params.endDate);
            }
            if (params?.supplierName) {
                args.push('--supplier_name', params.supplierName);
            }
            args.push('--format', 'json');
            break;
        case '客户对账单':
            scriptPath = path.join(scriptsDir, 'business_view_customer_reconciliation.py');
            // 构建命名参数
            args = [];
            if (params?.startDate) {
                args.push('--start_date', params.startDate);
            }
            if (params?.endDate) {
                args.push('--end_date', params.endDate);
            }
            if (params?.customerName) {
                args.push('--customer_name', params.customerName);
            }
            args.push('--format', 'json');
            break;
        case '库存盘点报表':
            scriptPath = path.join(scriptsDir, 'business_view_inventory_report.py');
            args = [];
            if (params?.startDate) {
                args.push('--start_date', params.startDate);
            }
            if (params?.endDate) {
                args.push('--end_date', params.endDate);
            }
            if (params?.productName) {
                args.push('--product_name', params.productName);
            }
            args.push('--format', 'json');
            break;
        case '销售统计报表':
            scriptPath = path.join(scriptsDir, 'business_view_sales_report.py');
            args = [];
            if (params?.startDate) {
                args.push('--start_date', params.startDate);
            }
            if (params?.endDate) {
                args.push('--end_date', params.endDate);
            }
            if (params?.customerName) {
                args.push('--customer_name', params.customerName);
            }
            if (params?.productName) {
                args.push('--product_name', params.productName);
            }
            args.push('--format', 'json');
            break;
        case '采购统计报表':
            scriptPath = path.join(scriptsDir, 'business_view_purchase_report.py');
            args = [];
            if (params?.startDate) {
                args.push('--start_date', params.startDate);
            }
            if (params?.endDate) {
                args.push('--end_date', params.endDate);
            }
            if (params?.supplierName) {
                args.push('--supplier_name', params.supplierName);
            }
            if (params?.productName) {
                args.push('--product_name', params.productName);
            }
            args.push('--format', 'json');
            break;
        case '应收账款统计':
            scriptPath = path.join(scriptsDir, 'business_view_receivables_report.py');
            args = [];
            if (params?.startDate) {
                args.push('--start_date', params.startDate);
            }
            if (params?.endDate) {
                args.push('--end_date', params.endDate);
            }
            if (params?.customerName) {
                args.push('--customer_name', params.customerName);
            }
            args.push('--format', 'summary');
            break;
        case '应付账款统计':
            scriptPath = path.join(scriptsDir, 'business_view_payables_report.py');
            args = [];
            if (params?.startDate) {
                args.push('--start_date', params.startDate);
            }
            if (params?.endDate) {
                args.push('--end_date', params.endDate);
            }
            if (params?.supplierName) {
                args.push('--supplier_name', params.supplierName);
            }
            args.push('--format', 'summary');
            break;
        default:
            panel.webview.postMessage({ 
                command: 'error', 
                data: `不支持的业务视图: ${viewName}` 
            });
            return;
    }
    
    // 显示加载状态
    panel.webview.postMessage({ command: 'loading', data: true });
    
    const pythonCmd = getPythonCommand(context);
    // 获取当前工作区路径
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
    
    const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
        env: { 
            ...process.env, 
            PYTHONIOENCODING: 'utf-8',
            IMS_WORKSPACE_PATH: workspacePath
        }
    });
    
    let dataOutput = '';
    let errorOutput = '';
    
    pythonProcess.stdout.on('data', (data: Buffer) => {
        dataOutput += data.toString();
    });
    
    pythonProcess.stderr.on('data', (data: Buffer) => {
        errorOutput += data.toString();
    });
    
    pythonProcess.on('error', (err) => {
        panel.webview.postMessage({ 
            command: 'error', 
            data: `无法启动业务视图脚本: ${err.message}` 
        });
    });
    
    pythonProcess.on('close', (code: number) => {
        panel.webview.postMessage({ command: 'loading', data: false });
        
        if (code === 0) {
            try {
                const jsonData = JSON.parse(dataOutput.trim());
                panel.webview.postMessage({ 
                    command: 'data', 
                    data: jsonData 
                });
            } catch (e) {
                panel.webview.postMessage({ 
                    command: 'error', 
                    data: `数据解析失败: ${e}\n原始输出: ${dataOutput}` 
                });
            }
        } else {
            panel.webview.postMessage({ 
                command: 'error', 
                data: `业务视图生成失败: ${errorOutput || '未知错误'}` 
            });
        }
    });
}

function getBusinessViewWebviewContent(viewName: string, chineseName: string): string {
    // 读取字体大小配置
    const config = vscode.workspace.getConfiguration('imsViewer');
    const fontSize = config.get<number>('tableFontSize', 12);
    
    let html = '<!DOCTYPE html>';
    html += '<html lang="zh-CN">';
    html += '<head>';
    html += '<meta charset="UTF-8">';
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">';
    html += '<title>' + chineseName + '</title>';
    html += '<style>';
    html += 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background-color: var(--vscode-editor-background); color: var(--vscode-editor-foreground); }';
    html += '.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid var(--vscode-panel-border); }';
    html += '.title { font-size: 10px; font-weight: bold; }';
    html += '.subtitle { font-size: 8px; color: var(--vscode-descriptionForeground); }';
    html += '.controls { display: flex; gap: 10px; align-items: center; }';
    html += '.filter-group { display: flex; gap: 5px; align-items: center; }'; html += '.filter-group label { font-size: 10px; }';
    html += 'input, select { background-color: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); padding: 2px 4px; border-radius: 2px; font-size: 9px; }';
    html += 'button { background-color: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 2px 6px; border-radius: 2px; cursor: pointer; font-size: 9px; }';
    html += 'button:hover { background-color: var(--vscode-button-hoverBackground); }';
    html += '.loading { text-align: center; padding: 40px; color: var(--vscode-descriptionForeground); }';
    html += '.error { background-color: var(--vscode-inputValidation-errorBackground); color: var(--vscode-inputValidation-errorForeground); border: 1px solid var(--vscode-inputValidation-errorBorder); padding: 15px; border-radius: 3px; margin: 20px 0; }';
    html += '.data-container { overflow: auto; max-height: calc(100vh - 180px); }';
    html += 'table { width: 100%; border-collapse: collapse; background-color: var(--vscode-editor-background); }';
    html += 'th, td { padding: 2px 4px; text-align: left; border-bottom: 1px solid var(--vscode-panel-border); font-size: ' + fontSize + 'px; line-height: 1.1; }';
    html += 'th { background-color: var(--vscode-list-hoverBackground); font-weight: bold; position: sticky; top: 0; }';
    html += 'tr:hover { background-color: var(--vscode-list-hoverBackground); }';
    html += '.empty { text-align: center; padding: 40px; color: var(--vscode-descriptionForeground); }';
    html += '.summary-card { background-color: var(--vscode-textBlockQuote-background); border: 1px solid var(--vscode-panel-border); border-radius: 5px; padding: 8px; margin-bottom: 10px; }';
    html += '.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }';
    html += '.summary-item { text-align: center; }';
    html += '.summary-value { font-size: 12px; font-weight: bold; color: var(--vscode-charts-blue); }';
    html += '.summary-label { font-size: 8px; color: var(--vscode-descriptionForeground); margin-top: 5px; }';
    html += '.amount-positive { color: var(--vscode-charts-green); }';
    html += '.amount-negative { color: var(--vscode-charts-red); }';
    html += '.amount-warning { color: var(--vscode-charts-orange); }';
    html += '.section { margin-bottom: 20px; }';
    html += '.section h3 { margin-bottom: 10px; font-size: 16px; font-weight: bold; }';
    html += '</style>';
    html += '</head>';
    html += '<body>';
    html += '<div class="header">';
    html += '<div><div class="title">' + chineseName + '</div><div class="subtitle">业务视图</div></div>';
    html += '<div class="controls">';
    html += '<div class="filter-group"><label>开始日期:</label><input type="date" id="startDate"></div>';
    html += '<div class="filter-group"><label>结束日期:</label><input type="date" id="endDate"></div>';
    
    // 根据视图类型显示不同的筛选控件
    if (viewName === '供应商对账表' || viewName === '采购统计报表' || viewName === '应付账款统计') {
        html += '<div class="filter-group"><label>供应商:</label><input type="text" id="supplierName" placeholder="输入供应商名称"></div>';
    } else if (viewName === '客户对账单' || viewName === '销售统计报表' || viewName === '应收账款统计') {
        html += '<div class="filter-group"><label>客户:</label><input type="text" id="customerName" placeholder="输入客户名称"></div>';
    }
    
    if (viewName === '库存盘点报表' || viewName === '销售统计报表' || viewName === '采购统计报表') {
        html += '<div class="filter-group"><label>产品:</label><input type="text" id="productName" placeholder="输入产品名称"></div>';
    }
    
    html += '<button onclick="applyFilter()">筛选</button>';
    html += '<button onclick="refreshData()">刷新</button>';
    html += '</div></div>';
    html += '<div id="summary" style="display: none;"></div>';
    html += '<div id="content"><div class="loading">正在加载数据...</div></div>';
    html += '<script>';
    html += 'const vscode = acquireVsCodeApi();';
    html += 'function refreshData() { vscode.postMessage({ command: "refresh" }); }';
    html += 'function applyFilter() { const params = { startDate: document.getElementById("startDate").value || null, endDate: document.getElementById("endDate").value || null }; const supplierInput = document.getElementById("supplierName"); const customerInput = document.getElementById("customerName"); const productInput = document.getElementById("productName"); if (supplierInput) params.supplierName = supplierInput.value || null; if (customerInput) params.customerName = customerInput.value || null; if (productInput) params.productName = productInput.value || null; vscode.postMessage({ command: "filter", params: params }); }';
    html += 'window.addEventListener("message", event => { const message = event.data; const content = document.getElementById("content"); switch (message.command) { case "loading": if (message.data) { content.innerHTML = "<div class=\\"loading\\">正在加载数据...</div>"; document.getElementById("summary").style.display = "none"; } break; case "error": content.innerHTML = "<div class=\\"error\\">错误: " + message.data + "</div>"; document.getElementById("summary").style.display = "none"; break; case "data": displayBusinessViewData(message.data); break; } });';
    html += 'function displayBusinessViewData(data) { const content = document.getElementById("content"); const summary = document.getElementById("summary"); const viewName = "' + viewName + '"; if (viewName === "应付账款统计" && data && typeof data === "object" && !Array.isArray(data)) { displayPayablesSummary(data); return; } if (viewName === "应收账款统计" && data && typeof data === "object" && !Array.isArray(data)) { displayReceivablesSummary(data); return; } if (!Array.isArray(data) || data.length === 0) { content.innerHTML = "<div class=\\"empty\\">暂无数据</div>"; summary.style.display = "none"; return; } let fieldMapping = {}; let summaryHtml = ""; if (viewName === "供应商对账表") { let totalPurchase = 0; let totalPayment = 0; let totalBalance = 0; let supplierCount = data.length; data.forEach(row => { totalPurchase += parseFloat(row.total_purchase_amount || 0); totalPayment += parseFloat(row.total_payment_amount || 0); totalBalance += parseFloat(row.balance || 0); }); summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + supplierCount + "</div><div class=\\"summary-label\\">供应商数量</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-positive\\">¥" + totalPurchase.toFixed(2) + "</div><div class=\\"summary-label\\">采购总金额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-negative\\">¥" + totalPayment.toFixed(2) + "</div><div class=\\"summary-label\\">付款总金额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value " + (totalBalance >= 0 ? "amount-positive" : "amount-negative") + "\\">¥" + totalBalance.toFixed(2) + "</div><div class=\\"summary-label\\">应付余额</div></div></div></div>"; fieldMapping = { "supplier_name": "供应商名称", "supplier_credit_code": "信用代码", "supplier_contact": "联系人", "supplier_phone": "联系电话", "total_purchase_amount": "采购金额", "total_payment_amount": "付款金额", "balance": "应付余额", "purchase_count": "采购笔数", "payment_count": "付款笔数", "latest_purchase_date": "最近采购日期", "latest_payment_date": "最近付款日期", "status": "状态" }; } else if (viewName === "客户对账单") { let totalSales = 0; let totalReceipt = 0; let totalBalance = 0; let customerCount = data.length; data.forEach(row => { totalSales += parseFloat(row.total_sales_amount || 0); totalReceipt += parseFloat(row.total_receipt_amount || 0); totalBalance += parseFloat(row.balance || 0); }); summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + customerCount + "</div><div class=\\"summary-label\\">客户数量</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-positive\\">¥" + totalSales.toFixed(2) + "</div><div class=\\"summary-label\\">销售总金额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-negative\\">¥" + totalReceipt.toFixed(2) + "</div><div class=\\"summary-label\\">收款总金额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value " + (totalBalance >= 0 ? "amount-positive" : "amount-negative") + "\\">¥" + totalBalance.toFixed(2) + "</div><div class=\\"summary-label\\">应收余额</div></div></div></div>"; fieldMapping = { "customer_name": "客户名称", "customer_credit_code": "信用代码", "customer_contact": "联系人", "customer_phone": "联系电话", "customer_address": "客户地址", "total_sales_amount": "销售金额", "total_receipt_amount": "收款金额", "balance": "应收余额", "sales_count": "销售笔数", "receipt_count": "收款笔数", "latest_sales_date": "最近销售日期", "latest_receipt_date": "最近收款日期" }; } else if (viewName === "库存盘点报表") { let totalProducts = data.length; let totalStock = 0; let totalValue = 0; data.forEach(row => { totalStock += parseFloat(row.current_stock || 0); totalValue += parseFloat(row.stock_value || 0); }); summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + totalProducts + "</div><div class=\\"summary-label\\">产品种类</div></div><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + totalStock.toFixed(0) + "</div><div class=\\"summary-label\\">库存总量</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-positive\\">¥" + totalValue.toFixed(2) + "</div><div class=\\"summary-label\\">库存总价值</div></div></div></div>"; fieldMapping = { "product_name": "产品名称", "product_model": "产品型号", "product_unit": "单位", "current_stock": "当前库存", "unit_price": "单价", "stock_value": "库存价值", "last_inbound_date": "最后入库日期", "last_outbound_date": "最后出库日期", "stock_status": "库存状态", "generated_date": "生成日期" }; } else if (viewName === "销售统计报表") { let totalSales = 0; let totalQuantity = 0; let recordCount = data.length; data.forEach(row => { totalSales += parseFloat(row.total_amount || 0); totalQuantity += parseFloat(row.quantity || 0); }); summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + recordCount + "</div><div class=\\"summary-label\\">销售记录</div></div><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + totalQuantity.toFixed(0) + "</div><div class=\\"summary-label\\">销售数量</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-positive\\">¥" + totalSales.toFixed(2) + "</div><div class=\\"summary-label\\">销售总额</div></div></div></div>"; fieldMapping = { "outbound_date": "销售日期", "outbound_number": "出库单号", "customer_name": "客户名称", "product_name": "产品名称", "product_model": "产品型号", "quantity": "数量", "unit_price": "单价", "total_amount": "总金额", "salesperson": "销售员" }; } else if (viewName === "采购统计报表") { let totalPurchase = 0; let totalQuantity = 0; let recordCount = data.length; data.forEach(row => { totalPurchase += parseFloat(row.total_amount || 0); totalQuantity += parseFloat(row.quantity || 0); }); summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + recordCount + "</div><div class=\\"summary-label\\">采购记录</div></div><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + totalQuantity.toFixed(0) + "</div><div class=\\"summary-label\\">采购数量</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-positive\\">¥" + totalPurchase.toFixed(2) + "</div><div class=\\"summary-label\\">采购总额</div></div></div></div>"; fieldMapping = { "inbound_date": "采购日期", "inbound_number": "入库单号", "supplier_name": "供应商名称", "product_name": "产品名称", "product_model": "产品型号", "quantity": "数量", "unit_price": "单价", "total_amount": "总金额", "purchaser": "采购员" }; } else if (viewName === "应收账款统计") { let totalReceivable = 0; let recordCount = data.length; data.forEach(row => { totalReceivable += parseFloat(row.receivable_amount || 0); }); summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + recordCount + "</div><div class=\\"summary-label\\">应收记录</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-positive\\">¥" + totalReceivable.toFixed(2) + "</div><div class=\\"summary-label\\">应收总额</div></div></div></div>"; fieldMapping = { "customer_name": "客户名称", "outbound_date": "销售日期", "outbound_number": "出库单号", "sales_amount": "销售金额", "receipt_amount": "收款金额", "receivable_amount": "应收金额", "overdue_days": "逾期天数", "status": "状态" }; } else if (viewName === "应付账款统计") { let totalPayable = 0; let recordCount = data.length; data.forEach(row => { totalPayable += parseFloat(row.payable_amount || 0); }); summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + recordCount + "</div><div class=\\"summary-label\\">应付记录</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-negative\\">¥" + totalPayable.toFixed(2) + "</div><div class=\\"summary-label\\">应付总额</div></div></div></div>"; fieldMapping = { "supplier_name": "供应商名称", "inbound_date": "采购日期", "inbound_number": "入库单号", "purchase_amount": "采购金额", "payment_amount": "付款金额", "payable_amount": "应付金额", "overdue_days": "逾期天数", "status": "状态" }; } summary.innerHTML = summaryHtml; summary.style.display = "block"; let html = "<div class=\\"data-container\\"><table><thead><tr>"; Object.entries(fieldMapping).forEach(([field, label]) => { html += "<th>" + label + "</th>"; }); html += "</tr></thead><tbody>"; data.forEach(row => { html += "<tr>"; Object.keys(fieldMapping).forEach(field => { let value = row[field]; let displayValue = ""; if (value !== null && value !== undefined) { if (field.includes("amount") || field === "balance" || field.includes("price") || field.includes("value")) { displayValue = "¥" + parseFloat(value).toFixed(2); } else { displayValue = String(value); } } html += "<td>" + displayValue + "</td>"; }); html += "</tr>"; }); html += "</tbody></table></div>"; content.innerHTML = html; }';
    html += 'function displayPayablesSummary(data) { const content = document.getElementById("content"); const summary = document.getElementById("summary"); try { if (!data || typeof data !== "object") { throw new Error("无效的数据格式"); } let summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + (data.supplier_count || 0) + "</div><div class=\\"summary-label\\">供应商数量</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-negative\\">¥" + (data.total_payables || 0).toFixed(2) + "</div><div class=\\"summary-label\\">应付总额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-warning\\">¥" + (data.overdue_amount || 0).toFixed(2) + "</div><div class=\\"summary-label\\">逾期金额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + (data.overdue_rate || 0).toFixed(1) + "%</div><div class=\\"summary-label\\">逾期率</div></div></div></div>"; summary.innerHTML = summaryHtml; summary.style.display = "block"; let detailHtml = "<div class=\\"data-container\\">"; if (data.total_payables === 0) { detailHtml += "<div class=\\"empty\\">暂无应付账款数据</div>"; } else { if (data.age_distribution && Object.keys(data.age_distribution).length > 0) { detailHtml += "<div class=\\"section\\"><h3>账龄分布</h3><table><thead><tr><th>账龄区间</th><th>金额</th><th>占比</th></tr></thead><tbody>"; Object.entries(data.age_distribution).forEach(([range, amount]) => { const percentage = data.total_payables > 0 ? (parseFloat(amount) / data.total_payables * 100).toFixed(1) : 0; detailHtml += "<tr><td>" + range + "</td><td>¥" + parseFloat(amount).toFixed(2) + "</td><td>" + percentage + "%</td></tr>"; }); detailHtml += "</tbody></table></div>"; } if (data.priority_distribution && Object.keys(data.priority_distribution).length > 0) { detailHtml += "<div class=\\"section\\"><h3>优先级分布</h3><table><thead><tr><th>优先级</th><th>金额</th><th>占比</th></tr></thead><tbody>"; Object.entries(data.priority_distribution).forEach(([priority, amount]) => { const percentage = data.total_payables > 0 ? (parseFloat(amount) / data.total_payables * 100).toFixed(1) : 0; detailHtml += "<tr><td>" + priority + "</td><td>¥" + parseFloat(amount).toFixed(2) + "</td><td>" + percentage + "%</td></tr>"; }); detailHtml += "</tbody></table></div>"; } if (data.top_payables && data.top_payables.length > 0) { detailHtml += "<div class=\\"section\\"><h3>应付账款排名（前" + data.top_payables.length + "名）</h3><table><thead><tr><th>供应商名称</th><th>应付余额</th><th>账龄天数</th><th>账龄区间</th><th>优先级</th></tr></thead><tbody>"; data.top_payables.forEach(item => { detailHtml += "<tr><td>" + (item.supplier_name || "未知") + "</td><td>¥" + (item.payable_balance || 0).toFixed(2) + "</td><td>" + (item.age_days || 0) + "</td><td>" + (item.age_range || "未知") + "</td><td>" + (item.priority_level || "未知") + "</td></tr>"; }); detailHtml += "</tbody></table></div>"; } else { detailHtml += "<div class=\\"section\\"><h3>应付账款排名</h3><div class=\\"empty\\">暂无排名数据</div></div>"; } } detailHtml += "</div>"; content.innerHTML = detailHtml; } catch (error) { console.error("显示应付账款统计数据时出错:", error); content.innerHTML = "<div class=\\"error\\">数据显示错误: " + error.message + "</div>"; summary.style.display = "none"; } }'; html += 'function displayReceivablesSummary(data) { const content = document.getElementById("content"); const summary = document.getElementById("summary"); try { if (!data || typeof data !== "object") { throw new Error("无效的数据格式"); } let summaryHtml = "<div class=\\"summary-card\\"><div class=\\"summary-grid\\"><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + (data.customer_count || 0) + "</div><div class=\\"summary-label\\">客户数量</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-positive\\">¥" + (data.total_receivables || 0).toFixed(2) + "</div><div class=\\"summary-label\\">应收总额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value amount-warning\\">¥" + (data.overdue_amount || 0).toFixed(2) + "</div><div class=\\"summary-label\\">逾期金额</div></div><div class=\\"summary-item\\"><div class=\\"summary-value\\">" + (data.overdue_rate || 0).toFixed(1) + "%</div><div class=\\"summary-label\\">逾期率</div></div></div></div>"; summary.innerHTML = summaryHtml; summary.style.display = "block"; let detailHtml = "<div class=\\"data-container\\">"; if (data.total_receivables === 0) { detailHtml += "<div class=\\"empty\\">暂无应收账款数据</div>"; } else { if (data.age_distribution && Object.keys(data.age_distribution).length > 0) { detailHtml += "<div class=\\"section\\"><h3>账龄分布</h3><table><thead><tr><th>账龄区间</th><th>金额</th><th>占比</th></tr></thead><tbody>"; Object.entries(data.age_distribution).forEach(([range, amount]) => { const percentage = data.total_receivables > 0 ? (parseFloat(amount) / data.total_receivables * 100).toFixed(1) : 0; detailHtml += "<tr><td>" + range + "</td><td>¥" + parseFloat(amount).toFixed(2) + "</td><td>" + percentage + "%</td></tr>"; }); detailHtml += "</tbody></table></div>"; } if (data.risk_distribution && Object.keys(data.risk_distribution).length > 0) { detailHtml += "<div class=\\"section\\"><h3>风险分布</h3><table><thead><tr><th>风险等级</th><th>金额</th><th>占比</th></tr></thead><tbody>"; Object.entries(data.risk_distribution).forEach(([risk, amount]) => { const percentage = data.total_receivables > 0 ? (parseFloat(amount) / data.total_receivables * 100).toFixed(1) : 0; detailHtml += "<tr><td>" + risk + "</td><td>¥" + parseFloat(amount).toFixed(2) + "</td><td>" + percentage + "%</td></tr>"; }); detailHtml += "</tbody></table></div>"; } if (data.top_receivables && data.top_receivables.length > 0) { detailHtml += "<div class=\\"section\\"><h3>应收账款排名（前" + data.top_receivables.length + "名）</h3><table><thead><tr><th>客户名称</th><th>应收余额</th><th>账龄天数</th><th>账龄区间</th><th>风险等级</th></tr></thead><tbody>"; data.top_receivables.forEach(item => { detailHtml += "<tr><td>" + (item.customer_name || "未知") + "</td><td>¥" + (item.receivable_balance || 0).toFixed(2) + "</td><td>" + (item.age_days || 0) + "</td><td>" + (item.age_range || "未知") + "</td><td>" + (item.risk_level || "未知") + "</td></tr>"; }); detailHtml += "</tbody></table></div>"; } else { detailHtml += "<div class=\\"section\\"><h3>应收账款排名</h3><div class=\\"empty\\">暂无排名数据</div></div>"; } } detailHtml += "</div>"; content.innerHTML = detailHtml; } catch (error) { console.error("显示应收账款统计数据时出错:", error); content.innerHTML = "<div class=\\"error\\">数据显示错误: " + error.message + "</div>"; summary.style.display = "none"; } }'; html += 'vscode.postMessage({ command: "loadData" });';
    html += '</script>';
    html += '</body>';
    html += '</html>';
    return html;
}

async function showAddMaterialDialog(context: vscode.ExtensionContext) {
    // 创建输入框收集物料信息
    const materialName = await vscode.window.showInputBox({
        prompt: '请输入物料名称',
        placeHolder: '例如: 工业级内存条'
    });
    
    if (!materialName) {
        return;
    }
    
    const materialModel = await vscode.window.showInputBox({
        prompt: '请输入物料型号',
        placeHolder: '例如: DDR4 16GB ECC'
    });
    
    if (!materialModel) {
        return;
    }
    
    const unit = await vscode.window.showInputBox({
        prompt: '请输入计量单位',
        placeHolder: '例如: 条, 个, 台, 张'
    });
    
    if (!unit) {
        return;
    }
    
    // 选择物料平台
    const platform = await vscode.window.showQuickPick(
        [{ label: 'P - 采购物料', value: 'P' }],
        { placeHolder: '选择物料平台' }
    );
    
    if (!platform) {
        return;
    }
    
    // 选择物料类型1 (国产/非国产)
    const type1 = await vscode.window.showQuickPick(
        [
            { label: '1 - 国产', value: '1' },
            { label: '2 - 非国产', value: '2' }
        ],
        { placeHolder: '选择物料类型 (国产/非国产)' }
    );
    
    if (!type1) {
        return;
    }
    
    // 选择物料类型2 (产品类别)
    const type2 = await vscode.window.showQuickPick(
        [
            { label: '1 - 纯软件', value: '1' },
            { label: '2 - 服务器(硬件)', value: '2' },
            { label: '3 - 工控机(硬件)', value: '3' },
            { label: '4 - 配件', value: '4' }
        ],
        { placeHolder: '选择物料类别' }
    );
    
    if (!type2) {
        return;
    }
    
    // 输入供应商编码
    const supplierCode = await vscode.window.showInputBox({
        prompt: '请输入供应商编码 (2位数字)',
        placeHolder: '例如: 01, 08, 15',
        validateInput: (value) => {
            if (!/^\d{2}$/.test(value)) {
                return '供应商编码必须是2位数字';
            }
            return null;
        }
    });
    
    if (!supplierCode) {
        return;
    }
    
    // 调用Python脚本添加物料
    try {
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] 开始添加物料: ${materialName}`);
        
        const materialInfo = {
            platform: platform.value,
            type1: type1.value,
            type2: type2.value,
            supplier_code: supplierCode,
            material_name: materialName,
            material_model: materialModel,
            unit: unit
        };
        
        await runAddMaterialScript(context, materialInfo);
        
        vscode.window.showInformationMessage(`✅ 物料 "${materialName}" 添加成功！`);
        
        // 刷新树视图
        vscode.commands.executeCommand('ims.refreshTreeView');
        
    } catch (error: any) {
        vscode.window.showErrorMessage(`添加物料失败: ${error.message}`);
        outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ❌ 添加物料失败: ${error.message}`);
    }
}

function runAddMaterialScript(context: vscode.ExtensionContext, materialInfo: any): Promise<void> {
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(context.extensionPath, 'scripts', 'add_material.py');
        const pythonCmd = getPythonCommand(context);
        
        outputChannel.appendLine(`> ${pythonCmd} "${scriptPath}" '${JSON.stringify(materialInfo)}'`);
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, JSON.stringify(materialInfo)], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdout = '';
        let stderr = '';
        
        pythonProcess.stdout.on('data', (data) => {
            const output = data.toString();
            stdout += output;
            outputChannel.append(output);
        });
        
        pythonProcess.stderr.on('data', (data) => {
            const output = data.toString();
            stderr += output;
            outputChannel.append(`[ERROR] ${output}`);
        });
        
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ✅ 物料添加脚本执行成功`);
                resolve();
            } else {
                const errorMsg = stderr || `脚本执行失败，退出代码: ${code}`;
                outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ❌ 物料添加脚本执行失败: ${errorMsg}`);
                reject(new Error(errorMsg));
            }
        });
        
        pythonProcess.on('error', (error) => {
            const errorMsg = `无法启动Python进程: ${error.message}`;
            outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ❌ ${errorMsg}`);
            reject(new Error(errorMsg));
        });
    });
}

// 显示进销存管理面板
function showInventoryManagementPanel(context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        'inventoryManagement',
        '进销存管理',
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    panel.webview.html = getInventoryManagementHtml(panel.webview, context.extensionUri);

    // 处理来自webview的消息
    panel.webview.onDidReceiveMessage(
        async message => {
            switch (message.command || message.action) {
                case 'load_inventory_data':
                    await handleInventoryDataLoad(context, panel, message);
                    break;
                case 'load_purchase_orders':
                    await handlePurchaseDataLoad(context, panel, message);
                    break;
                case 'load_sales_orders':
                    await handleSalesDataLoad(context, panel, message);
                    break;
                case 'load_suppliers':
                    await handleSuppliersLoad(context, panel, message);
                    break;
                case 'load_customers':
                    await handleCustomersLoad(context, panel, message);
                    break;
                case 'load_materials':
                    await handleMaterialsLoad(context, panel, message);
                    break;
                case 'runPython':
                    try {
                        const action = message.data;
                        const pythonCommand = getPythonCommand(context);
                        const scriptPath = vscode.Uri.joinPath(context.extensionUri, 'scripts', 'inventory_management_handler.py').fsPath;
                        
                        // 显示进度提示
                        vscode.window.withProgress({
                            location: vscode.ProgressLocation.Notification,
                            title: `正在执行${getActionName(action)}...`,
                            cancellable: false
                        }, async (progress) => {
                            return new Promise((resolve, reject) => {
                                // 获取当前工作区路径
                                const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
                                const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
                                
                                const pythonProcess = spawn(pythonCommand, [scriptPath, action], {
                                    env: { 
                                        ...process.env, 
                                        PYTHONIOENCODING: 'utf-8',
                                        IMS_WORKSPACE_PATH: workspacePath
                                    }
                                });
                                
                                let stdout = '';
                                let stderr = '';
                                
                                pythonProcess.stdout.on('data', (data) => {
                                    stdout += data.toString();
                                });
                                
                                pythonProcess.stderr.on('data', (data) => {
                                    stderr += data.toString();
                                });
                                
                                pythonProcess.on('close', (code) => {
                                    if (code === 0) {
                                        // 发送结果回webview
                                        panel.webview.postMessage({
                                            command: 'actionResult',
                                            action: action,
                                            success: true,
                                            data: stdout
                                        });
                                        resolve(undefined);
                                    } else {
                                        const errorMsg = stderr || `执行失败，退出代码: ${code}`;
                                        vscode.window.showErrorMessage(`${getActionName(action)}执行失败: ${errorMsg}`);
                                        panel.webview.postMessage({
                                            command: 'actionResult',
                                            action: action,
                                            success: false,
                                            error: errorMsg
                                        });
                                        reject(new Error(errorMsg));
                                    }
                                });
                                
                                pythonProcess.on('error', (error) => {
                                    const errorMsg = `无法启动Python进程: ${error.message}`;
                                    vscode.window.showErrorMessage(errorMsg);
                                    panel.webview.postMessage({
                                        command: 'actionResult',
                                        action: action,
                                        success: false,
                                        error: errorMsg
                                    });
                                    reject(error);
                                });
                            });
                        });
                    } catch (error) {
                        vscode.window.showErrorMessage(`执行失败: ${error}`);
                    }
                    break;
                case 'inventoryAction':
                    // 处理库存管理相关操作
                    handleInventoryAction(context, panel, message);
                    break;
            }
        },
        undefined,
        context.subscriptions
    );
}

// 获取进销存管理HTML内容
function getInventoryManagementHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
    const htmlPath = vscode.Uri.joinPath(extensionUri, 'webviews', 'inventory_management.html');
    
    try {
        const htmlContent = require('fs').readFileSync(htmlPath.fsPath, 'utf8');
        
        // 替换资源路径
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'webview', 'inventory_management.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'webview', 'inventory_management.css'));
        
        return htmlContent
            .replace(/src="inventory_management\.js"/g, `src="${scriptUri}"`)
            .replace(/href="inventory_management\.css"/g, `href="${styleUri}"`);
    } catch (error) {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <title>进销存管理</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    .error { color: red; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .header { background: var(--vscode-editor-background); padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                    .title { font-size: 24px; font-weight: bold; color: var(--vscode-foreground); }
                    .subtitle { font-size: 14px; color: var(--vscode-descriptionForeground); margin-top: 5px; }
                    .section { background: var(--vscode-editor-background); padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                    .section-title { font-size: 18px; font-weight: bold; margin-bottom: 15px; color: var(--vscode-foreground); }
                    .button-group { display: flex; gap: 10px; flex-wrap: wrap; }
                    .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
                    .btn-primary { background: var(--vscode-button-background); color: var(--vscode-button-foreground); }
                    .btn-secondary { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
                    .btn:hover { opacity: 0.8; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="title">进销存管理</div>
                        <div class="subtitle">采购管理 | 销售管理 | 库存管理</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">采购管理</div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="handleAction('purchase_order')">采购订单</button>
                            <button class="btn btn-secondary" onclick="handleAction('purchase_receipt')">采购入库</button>
                            <button class="btn btn-secondary" onclick="handleAction('purchase_return')">采购退货</button>
                            <button class="btn btn-secondary" onclick="handleAction('purchase_report')">采购报表</button>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">销售管理</div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="handleAction('sales_order')">销售订单</button>
                            <button class="btn btn-secondary" onclick="handleAction('sales_delivery')">销售出库</button>
                            <button class="btn btn-secondary" onclick="handleAction('sales_return')">销售退货</button>
                            <button class="btn btn-secondary" onclick="handleAction('sales_report')">销售报表</button>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">库存管理</div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="handleAction('inventory_check')">库存盘点</button>
                            <button class="btn btn-secondary" onclick="handleAction('inventory_transfer')">库存调拨</button>
                            <button class="btn btn-secondary" onclick="handleAction('inventory_report')">库存报表</button>
                            <button class="btn btn-secondary" onclick="handleAction('stock_alert')">库存预警</button>
                        </div>
                    </div>
                </div>
                
                <script>
                    const vscode = acquireVsCodeApi();
                    
                    function handleAction(action) {
                        // 显示加载状态
                        showActionFeedback(action, 'loading');
                        
                        vscode.postMessage({
                            command: 'runPython',
                            data: action
                        });
                    }
                    
                    function showActionFeedback(action, status, message = '') {
                        const actionNames = {
                            'purchase_order': '采购订单',
                            'purchase_receipt': '采购入库',
                            'purchase_return': '采购退货',
                            'purchase_report': '采购报表',
                            'sales_order': '销售订单',
                            'sales_delivery': '销售出库',
                            'sales_return': '销售退货',
                            'sales_report': '销售报表',
                            'inventory_check': '库存盘点',
                            'inventory_transfer': '库存调拨',
                            'inventory_report': '库存报表',
                            'stock_alert': '库存预警'
                        };
                        
                        const actionName = actionNames[action] || action;
                        
                        // 创建或更新反馈元素
                        let feedbackDiv = document.getElementById('actionFeedback');
                        if (!feedbackDiv) {
                            feedbackDiv = document.createElement('div');
                            feedbackDiv.id = 'actionFeedback';
                            feedbackDiv.style.cssText = \`
                                 position: fixed;
                                 top: 20px;
                                 right: 20px;
                                 padding: 15px 20px;
                                 border-radius: 5px;
                                 color: white;
                                 font-weight: bold;
                                 z-index: 1000;
                                 min-width: 200px;
                                 text-align: center;
                             \`;
                            document.body.appendChild(feedbackDiv);
                        }
                        
                        switch (status) {
                            case 'loading':
                                feedbackDiv.style.backgroundColor = '#007acc';
                                feedbackDiv.textContent = \`正在执行\${actionName}...\`;
                                feedbackDiv.style.display = 'block';
                                break;
                            case 'success':
                                feedbackDiv.style.backgroundColor = '#28a745';
                                feedbackDiv.textContent = \`\${actionName}执行成功！\`;
                                setTimeout(() => {
                                    feedbackDiv.style.display = 'none';
                                }, 3000);
                                break;
                            case 'error':
                                feedbackDiv.style.backgroundColor = '#dc3545';
                                feedbackDiv.textContent = \`\${actionName}执行失败: \${message}\`;
                                setTimeout(() => {
                                    feedbackDiv.style.display = 'none';
                                }, 5000);
                                break;
                        }
                    }
                    
                    // 监听来自扩展的消息
                    window.addEventListener('message', event => {
                        const message = event.data;
                        
                        switch (message.command) {
                            case 'actionResult':
                                if (message.success) {
                                    showActionFeedback(message.action, 'success');
                                } else {
                                    showActionFeedback(message.action, 'error', message.error);
                                }
                                break;
                        }
                    });
                                </script>
            </body>
            </html>
        `;
    }
}


// 显示数据分析仪表板面板
function showDataAnalysisDashboard(context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        'imsDataAnalysisDashboard',
        '📊 数据分析仪表板',
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    // 读取HTML文件内容
    const webviewsPath = path.join(context.extensionPath, 'webviews');
    const htmlPath = path.join(webviewsPath, 'data_analysis_dashboard.html');
    
    try {
        panel.webview.html = fs.readFileSync(htmlPath, 'utf8');
    } catch (error) {
        vscode.window.showErrorMessage(`无法加载数据分析仪表板: ${error}`);
        return;
    }

    // 处理来自webview的消息
    panel.webview.onDidReceiveMessage(
        async message => {
            switch (message.command) {
                case 'getDashboardData':
                    await handleDashboardDataRequest(context, panel, message.params);
                    break;
                case 'getSalesTrend':
                    await handleSalesTrendRequest(context, panel, message.params);
                    break;
                case 'getInventoryAnalysis':
                    await handleInventoryAnalysisRequest(context, panel, message.params);
                    break;
                case 'getCustomerAnalysis':
                    await handleCustomerAnalysisRequest(context, panel, message.params);
                    break;
                case 'getPurchaseTrend':
                    await handlePurchaseTrendRequest(context, panel, message.params);
                    break;
                case 'getComparisonAnalysis':
                    await handleComparisonAnalysisRequest(context, panel, message.params);
                    break;
                case 'exportDashboard':
                    await handleDashboardExportRequest(context, panel, message.params);
                    break;
            }
        },
        undefined,
        context.subscriptions
    );
}

// 处理仪表板数据请求
async function handleDashboardDataRequest(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, params: any) {
    try {
        const result = await runDataAnalysisScript(context, 'get_dashboard_summary', params);
        panel.webview.postMessage({
            command: 'dashboardData',
            success: result.success,
            data: result.data,
            error: result.error
        });
    } catch (error) {
        panel.webview.postMessage({
            command: 'dashboardData',
            success: false,
            error: `获取仪表板数据失败: ${error}`
        });
    }
}

// 处理销售趋势请求
async function handleSalesTrendRequest(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, params: any) {
    try {
        const result = await runDataAnalysisScript(context, 'analyze_sales_trend', params);
        panel.webview.postMessage({
            command: 'salesTrendData',
            success: result.success,
            data: result.data,
            dimension: params.dimension,
            error: result.error
        });
    } catch (error) {
        panel.webview.postMessage({
            command: 'salesTrendData',
            success: false,
            error: `获取销售趋势失败: ${error}`
        });
    }
}

// 处理库存分析请求
async function handleInventoryAnalysisRequest(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, params: any) {
    try {
        const result = await runDataAnalysisScript(context, 'analyze_inventory_turnover', params);
        panel.webview.postMessage({
            command: 'inventoryAnalysisData',
            success: result.success,
            data: result.data,
            error: result.error
        });
    } catch (error) {
        panel.webview.postMessage({
            command: 'inventoryAnalysisData',
            success: false,
            error: `获取库存分析失败: ${error}`
        });
    }
}

// 处理客户分析请求
async function handleCustomerAnalysisRequest(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, params: any) {
    try {
        const result = await runDataAnalysisScript(context, 'analyze_customer_value', params);
        panel.webview.postMessage({
            command: 'customerAnalysisData',
            success: result.success,
            data: result.data,
            error: result.error
        });
    } catch (error) {
        panel.webview.postMessage({
            command: 'customerAnalysisData',
            success: false,
            error: `获取客户分析失败: ${error}`
        });
    }
}

// 处理采购趋势请求
async function handlePurchaseTrendRequest(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, params: any) {
    try {
        const result = await runDataAnalysisScript(context, 'analyze_purchase_trend', params);
        panel.webview.postMessage({
            command: 'purchaseTrendData',
            success: result.success,
            data: result.data,
            dimension: params.dimension,
            error: result.error
        });
    } catch (error) {
        panel.webview.postMessage({
            command: 'purchaseTrendData',
            success: false,
            error: `获取采购趋势失败: ${error}`
        });
    }
}

// 处理对比分析请求
async function handleComparisonAnalysisRequest(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, params: any) {
    try {
        const result = await runDataAnalysisScript(context, 'generate_comparison_analysis', params);
        panel.webview.postMessage({
            command: 'comparisonAnalysisData',
            success: result.success,
            data: result.data,
            error: result.error
        });
    } catch (error) {
        panel.webview.postMessage({
            command: 'comparisonAnalysisData',
            success: false,
            error: `生成对比分析失败: ${error}`
        });
    }
}

// 处理仪表板导出请求
async function handleDashboardExportRequest(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, params: any) {
    try {
        // 这里可以实现导出功能，比如生成PDF或Excel报告
        panel.webview.postMessage({
            command: 'exportResult',
            success: true,
            message: '导出功能暂未实现'
        });
    } catch (error) {
        panel.webview.postMessage({
            command: 'exportResult',
            success: false,
            error: `导出失败: ${error}`
        });
    }
}

// 运行数据分析脚本
async function runDataAnalysisScript(context: vscode.ExtensionContext, method: string, params: any): Promise<any> {
    return new Promise((resolve, reject) => {
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, 'data_analysis_service.py');
        const pythonCmd = getPythonCommand(context);
        
        // 设置数据库配置环境变量
        setDatabaseConfigEnv();
        
        // 构建参数
        const args = ['--method', method];
        if (params) {
            args.push('--params', JSON.stringify(params));
        }
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdoutData = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            stdoutData += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data: Buffer) => {
            errorOutput += data.toString();
        });
        
        pythonProcess.on('error', (err) => {
            reject(`无法启动数据分析脚本: ${err.message}`);
        });
        
        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData.trim() || '{"success": false, "error": "无数据返回"}');
                    resolve(result);
                } catch (parseError) {
                    resolve({
                        success: false,
                        error: `解析结果失败: ${parseError}`,
                        rawOutput: stdoutData
                    });
                }
            } else {
                resolve({
                    success: false,
                    error: errorOutput || `脚本执行失败，退出码: ${code}`,
                    rawOutput: stdoutData
                });
            }
        });
    });
}

export function deactivate() {}

// 处理库存数据加载
async function handleInventoryDataLoad(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, message: any) {
    try {
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, 'business_view_inventory_report.py');
        const pythonCmd = getPythonCommand(context);
        
        // 设置数据库配置环境变量
        setDatabaseConfigEnv();
        
        const args = ['--format', 'json'];
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdoutData = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            stdoutData += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data: Buffer) => {
            errorOutput += data.toString();
        });
        
        pythonProcess.on('error', (err) => {
            panel.webview.postMessage({
                requestId: message.requestId,
                success: false,
                error: `无法启动库存报表脚本: ${err.message}`
            });
        });
        
        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData.trim());
                    if (result.success) {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: true,
                            data: result.data || []
                        });
                    } else {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: false,
                            error: result.error || '库存数据加载失败'
                        });
                    }
                } catch (parseError) {
                    panel.webview.postMessage({
                        requestId: message.requestId,
                        success: false,
                        error: `数据解析失败: ${parseError}`
                    });
                }
            } else {
                panel.webview.postMessage({
                    requestId: message.requestId,
                    success: false,
                    error: `库存数据加载失败: ${errorOutput || '未知错误'}`
                });
            }
        });
    } catch (error) {
        panel.webview.postMessage({
            requestId: message.requestId,
            success: false,
            error: `处理库存数据请求失败: ${error}`
        });
    }
}

// 处理采购数据加载
async function handlePurchaseDataLoad(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, message: any) {
    try {
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, 'business_view_purchase_report.py');
        const pythonCmd = getPythonCommand(context);
        
        // 设置数据库配置环境变量
        setDatabaseConfigEnv();
        
        const args = ['--format', 'json'];
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdoutData = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            stdoutData += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data: Buffer) => {
            errorOutput += data.toString();
        });
        
        pythonProcess.on('error', (err) => {
            panel.webview.postMessage({
                requestId: message.requestId,
                success: false,
                error: `无法启动采购报表脚本: ${err.message}`
            });
        });
        
        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData.trim());
                    if (result.success) {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: true,
                            data: result.data || []
                        });
                    } else {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: false,
                            error: result.error || '采购数据加载失败'
                        });
                    }
                } catch (parseError) {
                    panel.webview.postMessage({
                        requestId: message.requestId,
                        success: false,
                        error: `数据解析失败: ${parseError}`
                    });
                }
            } else {
                panel.webview.postMessage({
                    requestId: message.requestId,
                    success: false,
                    error: `采购数据加载失败: ${errorOutput || '未知错误'}`
                });
            }
        });
    } catch (error) {
        panel.webview.postMessage({
            requestId: message.requestId,
            success: false,
            error: `处理采购数据请求失败: ${error}`
        });
    }
}

// 处理销售数据加载
async function handleSalesDataLoad(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, message: any) {
    try {
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, 'business_view_sales_report.py');
        const pythonCmd = getPythonCommand(context);
        
        // 设置数据库配置环境变量
        setDatabaseConfigEnv();
        
        const args = ['--format', 'json'];
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdoutData = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            stdoutData += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data: Buffer) => {
            errorOutput += data.toString();
        });
        
        pythonProcess.on('error', (err) => {
            panel.webview.postMessage({
                requestId: message.requestId,
                success: false,
                error: `无法启动销售报表脚本: ${err.message}`
            });
        });
        
        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData.trim());
                    if (result.success) {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: true,
                            data: result.data || []
                        });
                    } else {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: false,
                            error: result.error || '销售数据加载失败'
                        });
                    }
                } catch (parseError) {
                    panel.webview.postMessage({
                        requestId: message.requestId,
                        success: false,
                        error: `数据解析失败: ${parseError}`
                    });
                }
            } else {
                panel.webview.postMessage({
                    requestId: message.requestId,
                    success: false,
                    error: `销售数据加载失败: ${errorOutput || '未知错误'}`
                });
            }
        });
    } catch (error) {
        panel.webview.postMessage({
            requestId: message.requestId,
            success: false,
            error: `处理销售数据请求失败: ${error}`
        });
    }
}

// 处理供应商数据加载
async function handleSuppliersLoad(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, message: any) {
    try {
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, 'query_table_data.py');
        const pythonCmd = getPythonCommand(context);
        
        // 设置数据库配置环境变量
        setDatabaseConfigEnv();
        
        const args = ['--type', 'table', '--name', 'suppliers'];
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdoutData = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            stdoutData += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data: Buffer) => {
            errorOutput += data.toString();
        });
        
        pythonProcess.on('error', (err) => {
            panel.webview.postMessage({
                requestId: message.requestId,
                success: false,
                error: `无法启动供应商查询脚本: ${err.message}`
            });
        });
        
        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData.trim());
                    if (result.success) {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: true,
                            data: result.data || []
                        });
                    } else {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: false,
                            error: result.error || '供应商数据加载失败'
                        });
                    }
                } catch (parseError) {
                    panel.webview.postMessage({
                        requestId: message.requestId,
                        success: false,
                        error: `数据解析失败: ${parseError}`
                    });
                }
            } else {
                panel.webview.postMessage({
                    requestId: message.requestId,
                    success: false,
                    error: `供应商数据加载失败: ${errorOutput || '未知错误'}`
                });
            }
        });
    } catch (error) {
        panel.webview.postMessage({
            requestId: message.requestId,
            success: false,
            error: `处理供应商数据请求失败: ${error}`
        });
    }
}

// 处理客户数据加载
async function handleCustomersLoad(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, message: any) {
    try {
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, 'query_table_data.py');
        const pythonCmd = getPythonCommand(context);
        
        // 设置数据库配置环境变量
        setDatabaseConfigEnv();
        
        const args = ['--type', 'table', '--name', 'customers'];
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdoutData = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            stdoutData += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data: Buffer) => {
            errorOutput += data.toString();
        });
        
        pythonProcess.on('error', (err) => {
            panel.webview.postMessage({
                requestId: message.requestId,
                success: false,
                error: `无法启动客户查询脚本: ${err.message}`
            });
        });
        
        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData.trim());
                    if (result.success) {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: true,
                            data: result.data || []
                        });
                    } else {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: false,
                            error: result.error || '客户数据加载失败'
                        });
                    }
                } catch (parseError) {
                    panel.webview.postMessage({
                        requestId: message.requestId,
                        success: false,
                        error: `数据解析失败: ${parseError}`
                    });
                }
            } else {
                panel.webview.postMessage({
                    requestId: message.requestId,
                    success: false,
                    error: `客户数据加载失败: ${errorOutput || '未知错误'}`
                });
            }
        });
    } catch (error) {
        panel.webview.postMessage({
            requestId: message.requestId,
            success: false,
            error: `处理客户数据请求失败: ${error}`
        });
    }
}

// 处理物料数据加载
async function handleMaterialsLoad(context: vscode.ExtensionContext, panel: vscode.WebviewPanel, message: any) {
    try {
        const scriptsDir = path.join(context.extensionPath, 'scripts');
        const scriptPath = path.join(scriptsDir, 'query_table_data.py');
        const pythonCmd = getPythonCommand(context);
        
        // 设置数据库配置环境变量
        setDatabaseConfigEnv();
        
        const args = ['--type', 'table', '--name', 'materials'];
        
        // 获取当前工作区路径
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const workspacePath = workspaceFolder ? workspaceFolder.uri.fsPath : '';
        
        const pythonProcess = spawn(pythonCmd, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONIOENCODING: 'utf-8',
                IMS_WORKSPACE_PATH: workspacePath
            }
        });
        
        let stdoutData = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data: Buffer) => {
            stdoutData += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data: Buffer) => {
            errorOutput += data.toString();
        });
        
        pythonProcess.on('error', (err) => {
            panel.webview.postMessage({
                requestId: message.requestId,
                success: false,
                error: `无法启动物料查询脚本: ${err.message}`
            });
        });
        
        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData.trim());
                    if (result.success) {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: true,
                            data: result.data || []
                        });
                    } else {
                        panel.webview.postMessage({
                            requestId: message.requestId,
                            success: false,
                            error: result.error || '物料数据加载失败'
                        });
                    }
                } catch (parseError) {
                    panel.webview.postMessage({
                        requestId: message.requestId,
                        success: false,
                        error: `数据解析失败: ${parseError}`
                    });
                }
            } else {
                panel.webview.postMessage({
                    requestId: message.requestId,
                    success: false,
                    error: `物料数据加载失败: ${errorOutput || '未知错误'}`
                });
            }
        });
    } catch (error) {
        panel.webview.postMessage({
            requestId: message.requestId,
            success: false,
            error: `处理物料数据请求失败: ${error}`
        });
    }
}