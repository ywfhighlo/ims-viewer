# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IMS Viewer is a VSCode extension that provides enterprise inventory management functionality, converting Excel business data into structured MongoDB storage with comprehensive business analytics and reporting capabilities.

## Architecture

### Technology Stack
- **Frontend**: TypeScript VSCode extension with webview panels
- **Backend**: Python scripts for data processing and business logic
- **Database**: MongoDB for data storage
- **UI**: HTML/CSS/JS webviews for data management interfaces

### Core Components

#### 1. Extension Entry Point (`src/extension.ts`)
- Main activation and command registration
- Python environment detection and script execution
- Webview panel management for data views
- Database configuration management

#### 2. Data Processing Pipeline (`scripts/`)
- **Parse Scripts** (`parse1-8_*.py`): Excel data parsing for 8 business modules
- **Business Views** (`business_view_*.py`): Analytics and reporting scripts
- **Core Services**: CRUD operations, data validation, import/export
- **Material Management**: Standard encoding and supplier code assignment

#### 3. Webview Providers (`src/`)
- `MaterialWebviewProvider.ts`: Material management interface
- `DataEntryWebviewProvider.ts`: Data entry forms
- `CustomerManagementWebviewProvider.ts`: Customer management
- `SupplierManagementWebviewProvider.ts`: Supplier management
- `treeDataProvider.ts`: Sidebar tree navigation

#### 4. Data Models
- **Suppliers**: Supplier information and contact details
- **Customers**: Customer information and business relationships
- **Materials**: Product catalog with standard encoding
- **Purchase/Sales**: Transaction records and inventory tracking
- **Financial**: Payment and receipt tracking

## Development Commands

### Build & Package
```bash
npm run compile          # Compile TypeScript
npm run watch            # Watch mode for development
npm run lint             # Run ESLint
npm run package          # Build VSIX package
npm run vscode:prepublish # Pre-publish compilation
```

### Python Environment Setup
```bash
pip install -r requirements.txt
```

### Extension Commands (VSCode)
- `IMS: Excel转为JSON` - Convert Excel to JSON format
- `IMS: 完整数据迁移流程` - Complete data migration workflow
- `IMS: 打开物料管理` - Open material management interface
- `IMS: 打开数据录入` - Open data entry interface
- `IMS: 打开进销存管理` - Open inventory management
- `IMS: 打开客户管理` - Open customer management
- `IMS: 打开供应商管理` - Open supplier management

## Configuration

### VSCode Settings (`imsViewer.*`)
- `mongoUri`: MongoDB connection URI
- `databaseName`: Database name (default: ims_database)
- `mongoUsername`: MongoDB username
- `mongoPassword`: MongoDB password
- `tableFontSize`: Font size for data tables
- `outputMode`: JSON file output mode (development/temp/custom)

### Field Mapping
Centralized field mapping in `field_mapping_dictionary.json`:
- Chinese to English field name translations
- Data type specifications
- Category classifications
- Table schemas and indexes

## Key Workflows

### 1. Data Import Process
1. Excel file → `parse_manager.py` → JSON files
2. `generate_standard_material_table.py` → Standard material codes
3. `import_to_mongodb_with_standard_codes.py` → Database import

### 2. Business Analytics
- Supplier reconciliation reports
- Customer account statements
- Inventory turnover analysis
- Sales/Purchase trend analysis
- Financial receivables/payables reports

### 3. Material Management
- Standard 12-digit material encoding: PTTTSSNNNNNN
  - P: Platform (1 digit)
  - TTT: Type classification (3 digits)
  - SS: Supplier code (2 digits)
  - NNNNNN: Sequential number (6 digits)

## File Structure

```
ims-viewer/
├── src/                    # TypeScript extension code
│   ├── extension.ts        # Main extension entry
│   ├── treeDataProvider.ts # Sidebar navigation
│   └── *WebviewProvider.ts # UI components
├── scripts/                # Python business logic
│   ├── parse*.py          # Excel parsing (8 modules)
│   ├── business_view_*.py # Analytics scripts
│   ├── material_manager.py # Material operations
│   └── crud_operations.py # Database operations
├── webviews/              # HTML interfaces
├── docs/                  # Generated JSON data
├── field_mapping_dictionary.json # Centralized mappings
└── package.json          # Extension manifest
```

## Development Notes

### Adding New Business Modules
1. Create `parse9_new_module.py` in scripts/
2. Add business view script `business_view_new_report.py`
3. Update field mapping in `field_mapping_dictionary.json`
4. Register new commands in `extension.ts`

### Database Operations
- All database operations use MongoDB
- Connection configured via VSCode settings
- Standard CRUD operations via `crud_operations.py`
- Query optimization in `query_optimizer.py`

### Testing
- Use `test_db_connection.py` for database connectivity
- `test_material_system.py` for material system validation
- Performance testing via `test_performance_comparison.py`

### Environment Variables
- `IMS_DB_NAME`: Database name
- `IMS_MONGO_URI`: MongoDB connection string
- `IMS_MONGO_USERNAME`: Database username
- `IMS_MONGO_PASSWORD`: Database password
- `IMS_WORKSPACE_PATH`: Current workspace path