#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Customer Management Script
Handles all CRUD and batch operations for customer data.
"""

import sys
import os
import json
import argparse
from bson import ObjectId
from datetime import datetime

# Add script directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_connection import get_database_connection

# The collection name for customers
COLLECTION_NAME = 'customers'

def get_collection():
    """Gets the customer collection from the database."""
    db = get_database_connection()
    return db[COLLECTION_NAME]

def list_customers(page=1, limit=10, search_query=None, sort_by='created_at', sort_order=-1):
    """Lists customers with pagination, search, and sorting."""
    try:
        collection = get_collection()
        query = {}
        if search_query:
            query = {
                '$or': [
                    {'customer_name': {'$regex': search_query, '$options': 'i'}},
                    {'customer_contact': {'$regex': search_query, '$options': 'i'}},
                    {'customer_phone': {'$regex': search_query, '$options': 'i'}}
                ]
            }

        total_records = collection.count_documents(query)
        records = list(collection.find(query)
                                 .sort(sort_by, sort_order)
                                 .skip((page - 1) * limit)
                                 .limit(limit))

        # Convert ObjectId to string for JSON serialization
        for record in records:
            record['_id'] = str(record['_id'])

        return {
            'success': True,
            'data': {
                'records': records,
                'total_records': total_records,
                'page': page,
                'limit': limit,
                'total_pages': (total_records + limit - 1) // limit
            }
        }
    except Exception as e:
        return {'success': False, 'message': f'Failed to list customers: {str(e)}'}

def add_customer(data):
    """Adds a new customer record."""
    try:
        collection = get_collection()
        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        result = collection.insert_one(data)
        return {
            'success': True,
            'message': 'Customer added successfully',
            'data': {'_id': str(result.inserted_id)}
        }
    except Exception as e:
        return {'success': False, 'message': f'Failed to add customer: {str(e)}'}

def update_customer(data):
    """Updates an existing customer record."""
    try:
        collection = get_collection()
        record_id = data.pop('_id', None)
        if not record_id:
            return {'success': False, 'message': 'Missing customer ID'}

        data['updated_at'] = datetime.now()
        result = collection.update_one({'_id': ObjectId(record_id)}, {'$set': data})

        if result.matched_count == 0:
            return {'success': False, 'message': 'Customer not found'}

        return {
            'success': True,
            'message': 'Customer updated successfully',
            'data': {'modified_count': result.modified_count}
        }
    except Exception as e:
        return {'success': False, 'message': f'Failed to update customer: {str(e)}'}

def delete_customer(data):
    """Deletes a customer record."""
    try:
        collection = get_collection()
        record_id = data.get('_id')
        if not record_id:
            return {'success': False, 'message': 'Missing customer ID'}

        result = collection.delete_one({'_id': ObjectId(record_id)})

        if result.deleted_count == 0:
            return {'success': False, 'message': 'Customer not found'}

        return {
            'success': True,
            'message': 'Customer deleted successfully',
            'data': {'deleted_count': result.deleted_count}
        }
    except Exception as e:
        return {'success': False, 'message': f'Failed to delete customer: {str(e)}'}

def batch_delete_customers(data):
    """Deletes multiple customer records in a batch."""
    try:
        collection = get_collection()
        ids = data.get('ids', [])
        if not ids:
            return {'success': False, 'message': 'No customer IDs provided for batch delete'}

        object_ids = [ObjectId(id) for id in ids]
        result = collection.delete_many({'_id': {'$in': object_ids}})

        return {
            'success': True,
            'message': f'Batch delete completed. {result.deleted_count} customers deleted.',
            'data': {'deleted_count': result.deleted_count}
        }
    except Exception as e:
        return {'success': False, 'message': f'Failed to batch delete customers: {str(e)}'}

def main():
    """Main function to handle command-line operations."""
    parser = argparse.ArgumentParser(description='Customer Management Operations')
    parser.add_argument('--operation', type=str, required=True, choices=['list', 'add', 'update', 'delete', 'batch_delete'], help='The operation to perform')
    parser.add_argument('--data', type=str, help='JSON string with data for the operation')
    
    args = parser.parse_args()
    
    try:
        data = json.loads(args.data) if args.data else {}
        result = {}

        if args.operation == 'list':
            result = list_customers(
                page=data.get('page', 1),
                limit=data.get('limit', 10),
                search_query=data.get('search_query'),
                sort_by=data.get('sort_by', 'created_at'),
                sort_order=data.get('sort_order', -1)
            )
        elif args.operation == 'add':
            result = add_customer(data)
        elif args.operation == 'update':
            result = update_customer(data)
        elif args.operation == 'delete':
            result = delete_customer(data)
        elif args.operation == 'batch_delete':
            result = batch_delete_customers(data)
        else:
            result = {'success': False, 'message': f'Unknown operation: {args.operation}'}
    except json.JSONDecodeError as e:
        result = {'success': False, 'message': f'Data format error: {str(e)}'}
    except Exception as e:
        result = {'success': False, 'message': f'Operation failed: {str(e)}'}

    print(json.dumps(result, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
