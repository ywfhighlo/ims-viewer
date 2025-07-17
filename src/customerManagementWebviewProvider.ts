import * as vscode from 'vscode';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Customer Management Webview Provider
 */
export class CustomerManagementWebviewProvider {
    public static readonly viewType = 'customerManagement';

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
            CustomerManagementWebviewProvider.viewType,
            '客户管理',
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
    
    private async _handleMessage(message: any) {
        const { command, data } = message;
        switch (command) {
            case 'loadCustomers':
                await this._loadCustomers(data);
                break;
            case 'addCustomer':
                await this._addCustomer(data);
                break;
            case 'updateCustomer':
                await this._updateCustomer(data);
                break;
            case 'deleteCustomer':
                await this._deleteCustomer(data);
                break;
            case 'batchDeleteCustomers':
                await this._batchDeleteCustomers(data);
                break;
            default:
                this._sendMessage({ command: 'error', message: `Unknown command: ${command}` });
        }
    }

    private async _loadCustomers(data: any) {
        const result = await this._executePythonScript('list', data);
        this._sendMessage({ command: 'customersLoaded', ...result });
    }

    private async _addCustomer(data: any) {
        const result = await this._executePythonScript('add', data);
        this._sendMessage({ command: 'customerAdded', ...result });
        if (result.success) {
            await this._loadCustomers({});
        }
    }

    private async _updateCustomer(data: any) {
        const result = await this._executePythonScript('update', data);
        this._sendMessage({ command: 'customerUpdated', ...result });
        if (result.success) {
            await this._loadCustomers({});
        }
    }

    private async _deleteCustomer(data: any) {
        const result = await this._executePythonScript('delete', data);
        this._sendMessage({ command: 'customerDeleted', ...result });
        if (result.success) {
            await this._loadCustomers({});
        }
    }

    private async _batchDeleteCustomers(data: any) {
        const result = await this._executePythonScript('batch_delete', data);
        this._sendMessage({ command: 'customersBatchDeleted', ...result });
        if (result.success) {
            await this._loadCustomers({});
        }
    }

    private async _executePythonScript(operation: string, data?: any): Promise<any> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            throw new Error('Workspace folder not found');
        }
        
        const scriptPath = path.join(workspaceFolder.uri.fsPath, 'scripts', 'customer_management.py');
        const dataString = data ? ` --data '${JSON.stringify(data)}'` : '';
        const command = `python "${scriptPath}" --operation ${operation}${dataString}`;

        try {
            const { stdout, stderr } = await execAsync(command, {
                cwd: workspaceFolder.uri.fsPath,
                encoding: 'utf8',
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            if (stderr) {
                console.warn('Python script warning:', stderr);
            }

            return JSON.parse(stdout.trim());
        } catch (error) {
            console.error('Failed to execute Python script:', error);
            return { success: false, message: `Failed to execute script: ${error}` };
        }
    }

    private _sendMessage(message: any) {
        if (this._panel) {
            this._panel.webview.postMessage(message);
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        const htmlPath = path.join(this._context.extensionPath, 'webviews', 'customer_management.html');
        try {
            const fs = require('fs');
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
