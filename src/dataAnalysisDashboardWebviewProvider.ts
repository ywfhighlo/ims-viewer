import * as vscode from 'vscode';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * 数据分析仪表板Web视图提供者
 */
export class DataAnalysisDashboardWebviewProvider {
    public static readonly viewType = 'dataAnalysisDashboard';

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
            DataAnalysisDashboardWebviewProvider.viewType,
            '数据分析仪表板',
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
            const { command, params } = message;
            
            switch (command) {
                case 'getDashboardData':
                    await this._getDashboardData(params);
                    break;
                    
                default:
                    this._sendMessage({
                        command: 'error',
                        error: { message: `未知命令: ${command}` }
                    });
            }
        } catch (error: any) {
            this._sendMessage({
                command: 'error',
                error: { message: `处理消息时发生错误: ${error.message}` }
            });
        }
    }

    /**
     * 获取仪表板数据
     */
    private async _getDashboardData(params: any) {
        try {
            const result = await this._executePythonScript('data_analysis_service.py', 'get_dashboard_data', params);
            
            this._sendMessage({
                command: 'dashboardData',
                data: result
            });
        } catch (error: any) {
            this._sendMessage({
                command: 'error',
                error: { message: `获取仪表板数据失败: ${error.message}` }
            });
        }
    }

    /**
     * 执行Python脚本
     */
    private async _executePythonScript(scriptName: string, method: string, params?: any): Promise<any> {
        return new Promise((resolve, reject) => {
            const scriptsDir = path.join(this._context.extensionPath, 'scripts');
            const scriptPath = path.join(scriptsDir, scriptName);
            
            // 获取Python命令
            const pythonCmd = this._getPythonCommand();
            
            // 准备参数 - 使用正确的格式
            const paramsStr = params ? JSON.stringify(params) : '{}';
            const cmdArgs = `"${scriptPath}" --method ${method} --params "${paramsStr}"`;

            // 获取当前工作区路径
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            const cwd = workspaceFolder ? workspaceFolder.uri.fsPath : this._context.extensionPath;

            console.log('Executing Python command:', `${pythonCmd} ${cmdArgs}`);
            console.log('Working directory:', cwd);

            const process = exec(`${pythonCmd} ${cmdArgs}`, {
                cwd: cwd,
                timeout: 30000 // 30秒超时
            }, (error, stdout, stderr) => {
                if (error) {
                    console.error('Python script execution error:', error);
                    reject(new Error(`脚本执行失败: ${error.message}`));
                    return;
                }

                if (stderr) {
                    console.warn('Python script stderr:', stderr);
                }

                console.log('Python script stdout:', stdout);

                try {
                    const result = JSON.parse(stdout);
                    resolve(result);
                } catch (parseError) {
                    console.error('Failed to parse Python script output:', stdout);
                    reject(new Error(`解析脚本输出失败: ${parseError}`));
                }
            });
        });
    }

    /**
     * 获取Python命令
     */
    private _getPythonCommand(): string {
        // 优先使用虚拟环境中的Python
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (workspaceFolder) {
            const venvPython = path.join(workspaceFolder.uri.fsPath, '.venv', 'Scripts', 'python.exe');
            const fs = require('fs');
            if (fs.existsSync(venvPython)) {
                return venvPython;
            }
        }
        
        // 回退到系统Python
        return 'python';
    }

    /**
     * 发送消息到webview
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
        const htmlPath = path.join(this._context.extensionPath, 'webviews', 'data_analysis_dashboard.html');
        
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
     * 获取默认HTML内容
     */
    private _getDefaultHtml(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>数据分析仪表板</title>
            </head>
            <body>
                <h1>数据分析仪表板</h1>
                <p>HTML文件加载失败，请检查文件路径。</p>
            </body>
            </html>
        `;
    }
}