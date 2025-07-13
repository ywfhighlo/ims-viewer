import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { spawn } from 'child_process';

export class DataEntryWebviewProvider {
    private panel: vscode.WebviewPanel | undefined;
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    public show() {
        if (this.panel) {
            this.panel.reveal(vscode.ViewColumn.One);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            'imsDataEntry',
            '数据录入管理',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.file(path.join(this.context.extensionPath, 'webviews'))
                ]
            }
        );

        this.panel.webview.html = this.getWebviewContent();

        // 处理来自webview的消息
        this.panel.webview.onDidReceiveMessage(
            message => {
                this.handleMessage(message);
            },
            undefined,
            this.context.subscriptions
        );

        // 当panel被关闭时清理
        this.panel.onDidDispose(
            () => {
                this.panel = undefined;
            },
            null,
            this.context.subscriptions
        );
    }

    private async handleMessage(message: any) {
        try {
            const result = await this.runPythonScript('data_entry_handler.py', message.command, message.data);
            
            if (this.panel) {
                this.panel.webview.postMessage(result);
            }
        } catch (error: any) {
            if (this.panel) {
                this.panel.webview.postMessage({
                    success: false,
                    error: `处理请求失败: ${error.message}`
                });
            }
        }
    }

    private runPythonScript(scriptName: string, command: string, data?: any): Promise<any> {
        return new Promise((resolve, reject) => {
            const scriptsDir = path.join(this.context.extensionPath, 'scripts');
            const scriptPath = path.join(scriptsDir, scriptName);
            
            // 获取Python命令
            const pythonCmd = this.getPythonCommand();
            
            // 准备参数
            const args = [scriptPath, command];
            if (data) {
                args.push(JSON.stringify(data));
            }

            const pythonProcess = spawn(pythonCmd, args, {
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
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
                reject(new Error(`无法启动脚本: ${err.message}`));
            });

            pythonProcess.on('close', (code: number) => {
                if (code === 0) {
                    try {
                        const result = JSON.parse(stdoutData.trim());
                        resolve(result);
                    } catch (e) {
                        reject(new Error(`解析脚本输出失败: ${e}\n原始输出: ${stdoutData}`));
                    }
                } else {
                    reject(new Error(`脚本执行失败，退出码: ${code}\n错误输出: ${errorOutput}`));
                }
            });
        });
    }

    private getPythonCommand(): string {
        // 优先使用虚拟环境中的Python
        const venvPythonPath = path.join(this.context.extensionPath, '.venv', 'bin', 'python');
        const venvPythonPathWin = path.join(this.context.extensionPath, '.venv', 'Scripts', 'python.exe');
        const venvPython3Path = path.join(this.context.extensionPath, '.venv', 'bin', 'python3');
        
        if (fs.existsSync(venvPythonPath)) {
            return venvPythonPath;
        }
        if (fs.existsSync(venvPython3Path)) {
            return venvPython3Path;
        }
        if (fs.existsSync(venvPythonPathWin)) {
            return venvPythonPathWin;
        }
        
        // 根据操作系统选择合适的Python命令
        const platform = process.platform;
        if (platform === 'win32') {
            return 'python';
        } else {
            return 'python3';
        }
    }

    private getWebviewContent(): string {
        // 读取HTML文件
        const htmlPath = path.join(this.context.extensionPath, 'webviews', 'data_entry.html');
        
        try {
            let htmlContent = fs.readFileSync(htmlPath, 'utf8');
            
            // 替换资源路径为webview可访问的路径
            const webviewsUri = this.panel!.webview.asWebviewUri(
                vscode.Uri.file(path.join(this.context.extensionPath, 'webviews'))
            );
            
            // 如果HTML中有相对路径的资源引用，需要替换为webview URI
            htmlContent = htmlContent.replace(
                /src="\.\/([^"]+)"/g,
                `src="${webviewsUri}/$1"`
            );
            htmlContent = htmlContent.replace(
                /href="\.\/([^"]+)"/g,
                `href="${webviewsUri}/$1"`
            );
            
            return htmlContent;
        } catch (error) {
            return `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>数据录入管理</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            margin: 20px;
                            background-color: var(--vscode-editor-background);
                            color: var(--vscode-editor-foreground);
                        }
                        .error {
                            background-color: var(--vscode-inputValidation-errorBackground);
                            color: var(--vscode-inputValidation-errorForeground);
                            border: 1px solid var(--vscode-inputValidation-errorBorder);
                            padding: 15px;
                            border-radius: 4px;
                            margin: 10px 0;
                        }
                    </style>
                </head>
                <body>
                    <h1>数据录入管理</h1>
                    <div class="error">
                        <strong>错误:</strong> 无法加载数据录入界面。<br>
                        请确保 webviews/data_entry.html 文件存在。<br>
                        错误详情: ${error}
                    </div>
                </body>
                </html>
            `;
        }
    }
}