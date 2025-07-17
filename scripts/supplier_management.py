import sys
import json
from datetime import datetime
from bson import ObjectId
import os

# Add the parent directory to the system path to allow imports from other directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.database import get_database_connection

def list_suppliers(page=1, limit=10, search_query=None):
    db = get_database_connection()
    collection = db['suppliers']
    
    query = {}
    if search_query:
        query = {
            '$or': [
                {'name': {'$regex': search_query, '$options': 'i'}},
                {'contact_person': {'$regex': search_query, '$options': 'i'}},
                {'phone': {'$regex': search_query, '$options': 'i'}}
            ]
        }
    
    total_records = collection.count_documents(query)
    records = list(collection.find(query).skip((page - 1) * limit).limit(limit))
    
    for record in records:
        record['_id'] = str(record['_id'])
        if 'created_at' in record and isinstance(record['created_at'], datetime):
            record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        if 'updated_at' in record and isinstance(record['updated_at'], datetime):
            record['updated_at'] = record['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            
    return {
        'data': records,
        'total': total_records,
        'page': page,
        'limit': limit
    }

def add_supplier(data):
    db = get_database_connection()
    collection = db['suppliers']
    data['created_at'] = datetime.now()
    data['updated_at'] = datetime.now()
    result = collection.insert_one(data)
    return {'success': True, 'inserted_id': str(result.inserted_id)}

def update_supplier(supplier_id, data):
    db = get_database_connection()
    collection = db['suppliers']
    data['updated_at'] = datetime.now()
    result = collection.update_one({'_id': ObjectId(supplier_id)}, {'$set': data})
    return {'success': result.modified_count > 0}

def delete_supplier(supplier_id):
    db = get_database_connection()
    collection = db['suppliers']
    result = collection.delete_one({'_id': ObjectId(supplier_id)})
    return {'success': result.deleted_count > 0}

def batch_delete_suppliers(supplier_ids):
    db = get_database_connection()
    collection = db['suppliers']
    result = collection.delete_many({'_id': {'$in': [ObjectId(id) for id in supplier_ids]}})
    return {'success': True, 'deleted_count': result.deleted_count}

if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'list':
        page = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        search_query = sys.argv[4] if len(sys.argv) > 4 else None
        result = list_suppliers(page, limit, search_query)
    elif command == 'add':
        supplier_data = json.loads(sys.argv[2])
        result = add_supplier(supplier_data)
    elif command == 'update':
        supplier_id = sys.argv[2]
        supplier_data = json.loads(sys.argv[3])
        result = update_supplier(supplier_id, supplier_data)
    elif command == 'delete':
        supplier_id = sys.argv[2]
        result = delete_supplier(supplier_id)
    elif command == 'batch_delete':
        supplier_ids = json.loads(sys.argv[2])
        result = batch_delete_suppliers(supplier_ids)
    else:
        result = {'error': 'Invalid command'}
    
    print(json.dumps(result, ensure_ascii=False))
