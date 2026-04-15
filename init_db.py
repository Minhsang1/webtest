import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    tables = ['users', 'products', 'payments', 'payment_logs', 'system_logs']
    for table in tables: cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    # Bảng users
    cursor.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT UNIQUE, password TEXT, role TEXT, 
        full_name TEXT, email TEXT, balance INTEGER DEFAULT 0, 
        is_locked INTEGER DEFAULT 0)''')
    
    # Bảng products (Đã thêm cột category)
    cursor.execute('''CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT, price TEXT, old_price TEXT, 
        image_url TEXT, discount TEXT, rating TEXT, 
        sold TEXT, category TEXT)''')
    
    cursor.execute('''CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, order_code TEXT, total_amount TEXT, payment_method TEXT, status TEXT, created_at TIMESTAMP)''')
    cursor.execute('''CREATE TABLE payment_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_id INTEGER, api_endpoint TEXT, raw_request TEXT, raw_response TEXT, created_at TIMESTAMP)''')
    cursor.execute('''CREATE TABLE system_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, ip_address TEXT, details TEXT, created_at TIMESTAMP)''')

    # Admin và User mẫu
    cursor.execute("INSERT INTO users (username, password, role, full_name, email, balance, is_locked) VALUES ('admin', 'admin_P@ssw0rd', 'Administrator', 'Quản Trị Viên', 'admin@techshop.local', 100000000, 0)")
    cursor.execute("INSERT INTO users (username, password, role, full_name, email, balance, is_locked) VALUES ('khachhang1', '123456', 'Customer', 'Nguyễn Văn Khách', 'khach@gmail.com', 50000000, 0)")

    # 6 Sản phẩm mẫu phân loại theo category (apple, laptop, tablet, smartphone)
    products = [
        ('iPhone 15 Pro Max', '32.990.000₫', '34.990.000₫', 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=500', '-6%', '5.0', '1.2k', 'apple'),
        ('MacBook Pro 14 M3', '39.990.000₫', '42.000.000₫', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500', '-5%', '5.0', '120', 'laptop'),
        ('iPad Pro M2 11 inch', '21.490.000₫', '23.000.000₫', 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=500', '-7%', '4.8', '500', 'tablet'),
        ('Samsung Galaxy S24 Ultra', '31.490.000₫', '36.490.000₫', 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=500', '-11%', '4.9', '850', 'smartphone'),
        ('Laptop ASUS ROG Strix', '28.990.000₫', '32.000.000₫', 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=500', '-9%', '4.7', '300', 'laptop'),
        ('Apple Watch Series 9', '9.490.000₫', '10.500.000₫', 'https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500', '-10%', '4.9', '1.5k', 'apple')
    ]
    cursor.executemany('INSERT INTO products (name, price, old_price, image_url, discount, rating, sold, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', products)
    
    conn.commit(); conn.close()
    print("Database đã được làm mới!")

if __name__ == '__main__': init_db()