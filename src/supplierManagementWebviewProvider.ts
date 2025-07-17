import * as vscode from 'vscode';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';

const execAsync = promisify(exec);

export class SupplierManagementWebviewProvider {
    public static readonly viewType = 'ims.supplierManagement';

    private _panel: vscode.WebviewPanel | undefined;
    private readonly _context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this._context = context;
    }

    public show() {
        if (this._panel) {
            this._panel.reveal(vscode.ViewColumn.One);
            return;
        }

        this._panel = vscode.window.createWebviewPanel(
            SupplierManagementWebviewProvider.viewType,
            '供应商管理',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [this._context.extensionUri]
            }
        );

        this._panel.webview.html = this._getHtmlForWebview(this._panel.webview);

        this._panel.webview.onDidReceiveMessage(async message => {
            await this._handleMessage(message);
        });

        this._panel.onDidDispose(() => {
            this._panel = undefined;
        }, null, this._context.subscriptions);
    }

    private async _handleMessage(message: any) {
        const { command, page, limit, searchQuery, id, data, ids } = message;
        let result;
        switch (command) {
            case 'list':
                result = await this._executePythonScript(command, [page.toString(), limit.toString(), searchQuery || '']);
                this._sendMessage({ command: 'updateList', data: result });
                break;
            case 'add':
            case 'update':
            case 'delete':
            case 'batch_delete':
                const args = command === 'add' || command === 'update' ? [id, JSON.stringify(data)] : [JSON.stringify(ids)];
                if(command === 'delete') args.splice(0,1,id);
                if(command === 'add') args.shift();

                await this._executePythonScript(command, args);
                // Refresh list after modification
                const listResult = await this._executePythonScript('list', ['1', '10', '']);
                this._sendMessage({ command: 'updateList', data: listResult });
                break;
            default:
                this._sendMessage({ command: 'error', message: `Unknown command: ${command}` });
        }
    }

    private async _executePythonScript(command: string, args: (string | number)[]): Promise<any> {
        const scriptPath = path.join(this._context.extensionPath, 'scripts', 'supplier_management.py');
        const commandArgs = [command, ...args.map(String)];

        const pythonCommand = `python "${scriptPath}" ${commandArgs.join(' ')}`;

        try {
            const { stdout, stderr } = await execAsync(pythonCommand, {
                cwd: this._context.extensionPath,
                encoding: 'utf8',
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            if (stderr) {
                console.warn('Python script warning:', stderr);
            }
            return JSON.parse(stdout.trim());
        } catch (error) {
            console.error('Failed to execute Python script:', error);
            vscode.window.showErrorMessage(`执行供应商管理脚本失败: ${error}`);
            return { success: false, message: `Failed to execute script: ${error}` };
        }
    }

    private _sendMessage(message: any) {
        if (this._panel) {
            this._panel.webview.postMessage(message);
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        const htmlPath = path.join(this._context.extensionPath, 'webviews', 'supplier_management.html');
        try {
            let html = fs.readFileSync(htmlPath, 'utf8');
            const resourceUri = webview.asWebviewUri(vscode.Uri.joinPath(this._context.extensionUri, 'webviews'));
            html = html.replace(/\{\{resourceUri\}\}/g, resourceUri.toString());
            return html;
        } catch (error) {
            console.error('Failed to read HTML file:', error);
            return `<h2>Error: Could not load webview content.</h2><p>${error}</p>`;
        }
    }

}
