import * as vscode from 'vscode';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * 物料管理Web视图提供者
 */
export class MaterialWebviewProvider {
    public static readonly viewType = 'materialManagement';

    private _panel?: vscode.WebviewPanel;
    private _context: vscode.ExtensionContext;

    constructor(private readonly context: vscode.ExtensionContext) {
        this._context = context;
    }

    public show() {
        if (this._panel) {
            this._panel.reveal(vscode.ViewColumn.One);
            return;
        }

        this._panel = vscode.window.createWebviewPanel(
            MaterialWebviewProvider.viewType,
            '物料管理',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [this._context.extensionUri]
            }
        );

        this._panel.webview.html = this._getHtmlForWebview(this._panel.webview);

        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                await this._handleMessage(message);
            },
            undefined,
            this._context.subscriptions
        );

        this._panel.onDidDispose(
            () => {
                this._panel = undefined;
            },
            null,
            this._context.subscriptions
        );
    }
    
    /**
     * 处理来自webview的消息
     */
    private async _handleMessage(message: any) {
        try {
            const { command, data } = message;
            
            switch (command) {
                case 'loadSuppliers':
                    await this._loadSuppliers();
                    break;
                    
                case 'addMaterial':
                    await this._addMaterial(data);
                    break;
                    
                case 'loadMaterials':
                    await this._loadMaterials();
                    break;
                    
                case 'loadSupplierCodes':
                    await this._loadSupplierCodes();
                    break;
                    
                case 'assignSupplierCodes':
                    await this._assignSupplierCodes();
                    break;
                    
                case 'exportMaterials':
                    await this._exportMaterials();
                    break;
                    
                default:
                    this._sendMessage({
                        command: 'error',
                        message: `未知命令: ${command}`
                    });
            }
        } catch (error) {
            this._sendMessage({
                command: 'error',
                message: `处理消息时发生错误: ${error}`
            });
        }
    }
    
    /**
     * 加载供应商列表
     */
    private async _loadSuppliers() {
        try {
            const result = await this._executePythonScript('loadSuppliers');
            if (result.success) {
                this._sendMessage(result);
            } else {
                this._sendMessage({
                    command: 'error',
                    message: result.error
                });
            }
        } catch (error) {
            this._sendMessage({
                command: 'error',
                message: `加载供应商失败: ${error}`
            });
        }
    }
    
    /**
     * 添加物料
     */
    private async _addMaterial(data: any) {
        try {
            const result = await this._executePythonScript('addMaterial', data);
            this._sendMessage(result);
        } catch (error) {
            this._sendMessage({
                command: 'materialAdded',
                success: false,
                error: `添加物料失败: ${error}`
            });
        }
    }
    
    /**
     * 加载物料列表
     */
    private async _loadMaterials() {
        try {
            const result = await this._executePythonScript('loadMaterials');
            if (result.success) {
                this._sendMessage(result);
            } else {
                this._sendMessage({
                    command: 'error',
                    message: result.error
                });
            }
        } catch (error) {
            this._sendMessage({
                command: 'error',
                message: `加载物料列表失败: ${error}`
            });
        }
    }
    
    /**
     * 加载供应商编码
     */
    private async _loadSupplierCodes() {
        try {
            const result = await this._executePythonScript('loadSupplierCodes');
            if (result.success) {
                this._sendMessage(result);
            } else {
                this._sendMessage({
                    command: 'error',
                    message: result.error
                });
            }
        } catch (error) {
            this._sendMessage({
                command: 'error',
                message: `加载供应商编码失败: ${error}`
            });
        }
    }
    
    /**
     * 分配供应商编码
     */
    private async _assignSupplierCodes() {
        try {
            const result = await this._executePythonScript('assignSupplierCodes');
            
            if (result.success) {
                vscode.window.showInformationMessage(result.message);
                // 重新加载供应商编码列表
                await this._loadSupplierCodes();
            } else {
                vscode.window.showErrorMessage(result.error);
            }
        } catch (error) {
            vscode.window.showErrorMessage(`分配供应商编码失败: ${error}`);
        }
    }
    
    /**
     * 导出物料列表
     */
    private async _exportMaterials() {
        try {
            const result = await this._executePythonScript('exportMaterials');
            
            if (result.success) {
                vscode.window.showInformationMessage(result.message);
                
                // 询问是否打开导出文件
                const openFile = await vscode.window.showInformationMessage(
                    '物料列表导出成功！',
                    '打开文件',
                    '打开文件夹'
                );
                
                if (openFile === '打开文件' && result.filepath) {
                    const uri = vscode.Uri.file(result.filepath);
                    await vscode.window.showTextDocument(uri);
                } else if (openFile === '打开文件夹' && result.filepath) {
                    const folderUri = vscode.Uri.file(path.dirname(result.filepath));
                    await vscode.commands.executeCommand('vscode.openFolder', folderUri, true);
                }
            } else {
                vscode.window.showErrorMessage(result.error);
            }
        } catch (error) {
            vscode.window.showErrorMessage(`导出物料列表失败: ${error}`);
        }
    }
    
    /**
     * 执行Python脚本
     */
    private async _executePythonScript(command: string, data?: any): Promise<any> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            throw new Error('未找到工作区文件夹');
        }
        
        const scriptPath = path.join(workspaceFolder.uri.fsPath, 'scripts', 'material_web_handler.py');
        
        let cmd = `python "${scriptPath}" "${command}"`;
        if (data) {
            const jsonData = JSON.stringify(data).replace(/"/g, '\\"');
            cmd += ` "${jsonData}"`;
        }
        
        try {
            const { stdout, stderr } = await execAsync(cmd, {
                cwd: workspaceFolder.uri.fsPath,
                timeout: 30000 // 30秒超时
            });
            
            if (stderr) {
                console.warn('Python脚本警告:', stderr);
            }
            
            if (!stdout.trim()) {
                throw new Error('Python脚本没有返回数据');
            }
            
            return JSON.parse(stdout.trim());
        } catch (error) {
            console.error('执行Python脚本失败:', error);
            throw error;
        }
    }
    
    /**
     * 向webview发送消息
     */
    private _sendMessage(message: any) {
        if (this._panel) {
            this._panel.webview.postMessage(message);
        }
    }
    
    /**
     * 获取webview的HTML内容
     */
    private _getHtmlForWebview(webview: vscode.Webview): string {
        // 读取HTML文件
        const htmlPath = path.join(this._context.extensionPath, 'webviews', 'material_management.html');
        
        try {
            const fs = require('fs');
            let html = fs.readFileSync(htmlPath, 'utf8');
            
            // 替换资源路径为webview可访问的路径
            const resourcePath = webview.asWebviewUri(
                vscode.Uri.file(path.join(this._context.extensionPath, 'webviews'))
            );
            
            html = html.replace(/src="\.\//, `src="${resourcePath}/`);
            html = html.replace(/href="\.\//, `href="${resourcePath}/`);
            
            return html;
        } catch (error) {
            console.error('读取HTML文件失败:', error);
            return this._getDefaultHtml();
        }
    }
    
    /**
     * 获取默认HTML内容（当文件读取失败时使用）
     */
    private _getDefaultHtml(): string {
        return `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>物料管理系统</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        color: var(--vscode-foreground);
                        background-color: var(--vscode-editor-background);
                        padding: 20px;
                        text-align: center;
                    }
                    .error {
                        color: var(--vscode-errorForeground);
                        background-color: var(--vscode-inputValidation-errorBackground);
                        padding: 15px;
                        border-radius: 4px;
                        margin: 20px 0;
                    }
                </style>
            </head>
            <body>
                <h1>🏭 物料管理系统</h1>
                <div class="error">
                    ❌ 无法加载物料管理界面<br>
                    请确保 webviews/material_management.html 文件存在
                </div>
                <script>
                    const vscode = acquireVsCodeApi();
                </script>
            </body>
            </html>
        `;
    }
}