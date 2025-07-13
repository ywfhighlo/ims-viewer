#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pymongo import MongoClient

def check_supplier_names():
    client = MongoClient('mongodb://localhost:27017/')
    db_name = os.environ.get('IMS_DB_NAME', 'ims_viewer')
db = client[db_name]
    
    # 获取供应商表中的名称
    suppliers = list(db['suppliers'].find({}, {'supplier_name': 1}).limit(10))
    print('供应商表中的名称:')
    supplier_names = set()
    for s in suppliers:
        name = s.get('supplier_name')
        if name:
            supplier_names.add(name)
            print(f'  {name}')
    
    print('\n采购表中的名称:')
    purchases = list(db['purchase_inbound'].find({}, {'supplier_name': 1}).limit(10))
    purchase_names = set()
    for p in purchases:
        name = p.get('supplier_name')
        if name:
            purchase_names.add(name)
            print(f'  {name}')
    
    print('\n付款表中的名称:')
    payments = list(db['payment_details'].find({}, {'supplier_name': 1}).limit(10))
    payment_names = set()
    for p in payments:
        name = p.get('supplier_name')
        if name:
            payment_names.add(name)
            print(f'  {name}')
    
    print('\n匹配情况:')
    print(f'供应商表中的名称数量: {len(supplier_names)}')
    print(f'采购表中的名称数量: {len(purchase_names)}')
    print(f'付款表中的名称数量: {len(payment_names)}')
    
    # 检查交集
    common_supplier_purchase = supplier_names.intersection(purchase_names)
    common_supplier_payment = supplier_names.intersection(payment_names)
    
    print(f'\n供应商表与采购表匹配的名称数量: {len(common_supplier_purchase)}')
    for name in list(common_supplier_purchase)[:5]:
        print(f'  {name}')
    
    print(f'\n供应商表与付款表匹配的名称数量: {len(common_supplier_payment)}')
    for name in list(common_supplier_payment)[:5]:
        print(f'  {name}')

if __name__ == '__main__':
    check_supplier_names()