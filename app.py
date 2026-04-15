from flask import Flask, request, render_template, redirect, url_for, session, flash
import sqlite3, os, uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'huit_security_sang_master_key'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def parse_price(price_str):
    try: return int(str(price_str).replace('.', '').replace('₫', '').strip())
    except: return 0

def format_price(num): return f"{num:,.0f}".replace(',', '.') + '₫'

# ĐÁ USER KHI BỊ KHÓA
@app.before_request
def check_user_status():
    if request.endpoint in ['login', 'register', 'static', 'logout'] or not session.get('loggedin'):
        return
    conn = get_db_connection()
    user = conn.execute("SELECT is_locked FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    if not user or user['is_locked'] == 1:
        session.clear()
        return redirect(url_for('login', error='Tài khoản của bạn đã bị Admin khóa hoặc xóa!'))

# ĐĂNG NHẬP / ĐĂNG KÝ
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (request.form['username'], request.form['password'])).fetchone()
        conn.close()
        if user:
            if user['is_locked'] == 1: return render_template('login.html', error='Tài khoản đang bị khóa!')
            session.update({'loggedin': True, 'user_id': user['id'], 'username': user['username'], 'role': user['role'], 'cart': []})
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Sai tài khoản hoặc mật khẩu!')
    return render_template('login.html', success=request.args.get('success'), error=request.args.get('error'))

@app.route('/register', methods=['POST'])
def register():
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password, role, full_name, email, balance, is_locked) VALUES (?, ?, 'Customer', ?, ?, 0, 0)", 
                     (request.form['reg_username'], request.form['reg_password'], request.form['reg_username'], request.form['reg_username'] + "@techshop.local"))
        conn.commit(); conn.close()
        return redirect(url_for('login', success='Đăng ký thành công!'))
    except:
        conn.close()
        return redirect(url_for('login', error='Tên đăng nhập đã tồn tại!'))

# HỒ SƠ
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('loggedin'): return redirect(url_for('login'))
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        old_pw = request.form.get('old_password')
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')

        conn.execute("UPDATE users SET full_name=?, email=? WHERE id=?", (full_name, email, session['user_id']))
        
        if old_pw or new_pw or confirm_pw:
            if old_pw != user['password']:
                flash("Mật khẩu cũ không chính xác!", "danger")
            elif new_pw != confirm_pw:
                flash("Mật khẩu mới nhập lại không khớp!", "danger")
            elif len(new_pw) < 3:
                flash("Mật khẩu mới phải dài hơn 3 ký tự!", "danger")
            else:
                conn.execute("UPDATE users SET password=? WHERE id=?", (new_pw, session['user_id']))
                flash("Đã cập nhật thông tin và mật khẩu thành công!", "success")
        else:
            flash("Cập nhật thông tin cá nhân thành công!", "success")
            
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()

    conn.close()
    return render_template('profile.html', user_info=user, username=session['username'])

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

# DASHBOARD & SẢN PHẨM
@app.route('/dashboard')
def dashboard():
    if not session.get('loggedin'): return redirect(url_for('login'))
    s, cat = request.args.get('search', ''), request.args.get('cat', '')
    conn = get_db_connection()
    user = conn.execute("SELECT balance FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    if cat: products = conn.execute("SELECT * FROM products WHERE category = ?", (cat,)).fetchall()
    else: products = conn.execute("SELECT * FROM products WHERE name LIKE ?", ('%'+s+'%',)).fetchall()
    conn.close()
    cart = session.get('cart', [])
    cart_total = format_price(sum([parse_price(i['price']) for i in cart]))
    return render_template('dashboard.html', username=session['username'], role=session['role'], products=products, balance=format_price(user['balance']), cart=cart, cart_total=cart_total)

# NẠP TIỀN
@app.route('/topup', methods=['POST'])
def topup():
    amount = parse_price(request.form.get('amount', '0'))
    bank = request.form.get('bank', 'Chưa rõ')
    acc_num = request.form.get('account_number', '')
    
    if amount <= 0:
        flash("Số tiền không hợp lệ!", "danger")
    else:
        conn = get_db_connection()
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, session['user_id']))
        conn.commit(); conn.close()
        flash(f"Nạp {format_price(amount)} từ ngân hàng {bank} (STK: {acc_num}) thành công!", "success")
    return redirect(url_for('dashboard'))

# GIỎ HÀNG & THANH TOÁN
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    conn = get_db_connection()
    p = conn.execute("SELECT * FROM products WHERE id=?", (request.form['product_id'],)).fetchone()
    conn.close()
    if p:
        cart = session.get('cart', [])
        cart.append({'id': str(uuid.uuid4()), 'name': p['name'], 'price': p['price'], 'image': p['image_url']})
        session['cart'] = cart; session.modified = True
        flash(f"🛒 Đã thêm [{p['name']}] vào giỏ hàng!", "success")
    return redirect(url_for('dashboard'))

@app.route('/remove_from_cart/<item_id>')
def remove_from_cart(item_id):
    cart = session.get('cart', [])
    session['cart'] = [i for i in cart if i['id'] != item_id]
    session.modified = True
    flash("🗑️ Đã xóa sản phẩm khỏi giỏ hàng!", "warning")
    return redirect(url_for('dashboard'))

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', [])
    if not cart:
        flash("Giỏ hàng đang trống!", "warning")
        return redirect(url_for('dashboard'))
    
    total_val = sum([parse_price(i['price']) for i in cart])
    conn = get_db_connection()
    user = conn.execute("SELECT balance FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    if total_val > user['balance']:
        flash("Số dư ví không đủ! Vui lòng nạp thêm tiền.", "danger")
        conn.close(); return redirect(url_for('dashboard'))
        
    order_code = f"ORD-{str(uuid.uuid4())[:8].upper()}"
    conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (total_val, session['user_id']))
    conn.execute("INSERT INTO payments (user_id, order_code, total_amount, payment_method, status, created_at) VALUES (?, ?, ?, ?, 'Success', ?)", (session['user_id'], order_code, format_price(total_val), 'Hệ Thống', datetime.now()))
    conn.commit(); conn.close()
    session['cart'] = []
    flash("Thanh toán thành công!", "success")
    return redirect(url_for('view_orders'))

@app.route('/orders')
def view_orders():
    if not session.get('loggedin'): return redirect(url_for('login'))
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('orders.html', orders=orders, username=session['username'])

# ==========================================
# QUẢN TRỊ ADMIN (Thêm Sản Phẩm Mới)
# ==========================================
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('admin.html', users=users, products=products, username=session['username'])

@app.route('/admin/edit_user', methods=['POST'])
def edit_user():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    uid, fname, email, u_role = request.form.get('user_id'), request.form.get('full_name'), request.form.get('email'), request.form.get('role')
    conn = get_db_connection()
    conn.execute("UPDATE users SET full_name=?, email=?, role=? WHERE id=?", (fname, email, u_role, uid))
    conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard', success='Đã cập nhật thông tin khách hàng!'))

@app.route('/admin/manage_balance', methods=['POST'])
def manage_balance():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    uid, amt, act = request.form.get('user_id'), parse_price(request.form.get('amount')), request.form.get('action')
    conn = get_db_connection()
    if act == 'add': conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amt, uid))
    else: conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amt, uid))
    conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard', success='Đã cập nhật tiền!'))

@app.route('/admin/toggle_lock/<int:id>')
def toggle_lock(id):
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection()
    u = conn.execute("SELECT is_locked FROM users WHERE id=?", (id,)).fetchone()
    conn.execute("UPDATE users SET is_locked=? WHERE id=?", (1 if u['is_locked'] == 0 else 0, id))
    conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection(); conn.execute("DELETE FROM users WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard'))

# TÍNH NĂNG MỚI: THÊM SẢN PHẨM
@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    name, price, img, cat = request.form.get('name'), request.form.get('price'), request.form.get('image'), request.form.get('category')
    conn = get_db_connection()
    conn.execute("INSERT INTO products (name, price, image_url, category) VALUES (?, ?, ?, ?)", (name, price, img, cat))
    conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard', success='Đã thêm sản phẩm mới thành công!'))

@app.route('/admin/edit_product', methods=['POST'])
def edit_product():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    pid, name, price, img, cat = request.form.get('product_id'), request.form.get('name'), request.form.get('price'), request.form.get('image'), request.form.get('category')
    conn = get_db_connection()
    conn.execute("UPDATE products SET name=?, price=?, image_url=?, category=? WHERE id=?", (name, price, img, cat, pid))
    conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard', success='Đã sửa sản phẩm!'))

@app.route('/admin/delete_product/<int:id>')
def delete_product(id):
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection(); conn.execute("DELETE FROM products WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard', success='Đã xóa sản phẩm!'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)