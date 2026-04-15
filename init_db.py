import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    tables = ['users', 'products', 'payments', 'payment_logs', 'system_logs']
    for table in tables: cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    cursor.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, full_name TEXT, email TEXT, balance INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, old_price TEXT, image_url TEXT, discount TEXT, rating TEXT, sold TEXT)''')
    cursor.execute('''CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, order_code TEXT, total_amount TEXT, payment_method TEXT, status TEXT, created_at TIMESTAMP)''')
    cursor.execute('''CREATE TABLE payment_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_id INTEGER, api_endpoint TEXT, raw_request TEXT, raw_response TEXT, created_at TIMESTAMP)''')
    cursor.execute('''CREATE TABLE system_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, ip_address TEXT, details TEXT, created_at TIMESTAMP)''')

    users = [
        ('admin', 'admin_P@ssw0rd', 'Administrator', 'Quản Trị Viên', 'admin@techshop.local', 100000000),
        ('khachhang1', '123456', 'Customer', 'Nguyễn Văn Khách', 'khachhang@gmail.com', 0)
    ]
    cursor.executemany('INSERT INTO users (username, password, role, full_name, email, balance) VALUES (?, ?, ?, ?, ?, ?)', users)

    products = [
        ('iPhone 15 Pro Max 256GB', '32.990.000₫', '34.990.000₫', 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?q=80&w=500', '-6%', '5.0', '1.2k'),
        ('Samsung Galaxy S24 Ultra', '31.490.000₫', '36.490.000₫', 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?q=80&w=500', '-11%', '4.9', '850'),
        ('MacBook Pro 14 M3 2024', '39.990.000₫', '42.000.000₫', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=500', '-5%', '5.0', '120')
    ]
    cursor.executemany('INSERT INTO products (name, price, old_price, image_url, discount, rating, sold) VALUES (?, ?, ?, ?, ?, ?, ?)', products)
    conn.commit(); conn.close()

if __name__ == '__main__': init_db()