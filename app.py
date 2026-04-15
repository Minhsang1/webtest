from flask import Flask, request, render_template, redirect, url_for, session, render_template_string, flash
import sqlite3, os, uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'webtest'

STRIPE_PAYMENT_API_KEY = "sk_live_51MabcXYZ123_TechShop_SecretKey_9999"
PAYMENT_GATEWAY_URL = "https://api.stripe.com/v1/charges"

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def parse_price(price_str):
    try: return int(str(price_str).replace('.', '').replace('₫', '').strip())
    except: return 0

def format_price(num): return f"{num:,.0f}".replace(',', '.') + '₫'

def write_system_log(user_id, action, details):
    ip = request.remote_addr
    conn = get_db_connection()
    conn.execute("INSERT INTO system_logs (user_id, action, ip_address, details, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, action, ip, details, datetime.now()))
    conn.commit(); conn.close()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (request.form['username'], request.form['password'])).fetchone()
        conn.close()
        if user:
            session.update({'loggedin': True, 'user_id': user['id'], 'username': user['username'], 'role': user['role'], 'cart': []})
            write_system_log(user['id'], 'LOGIN_SUCCESS', f"User {user['username']}")
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Sai thông tin!')
    return render_template('login.html', success=request.args.get('success'), error=request.args.get('error'))

# ĐÃ BỔ SUNG LẠI CHỨC NĂNG ĐĂNG KÝ
@app.route('/register', methods=['POST'])
def register():
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password, role, full_name, email, balance) VALUES (?, ?, 'Customer', ?, ?, 0)", 
                     (request.form['reg_username'], request.form['reg_password'], request.form['reg_username'], request.form['reg_username'] + "@techshop.local"))
        conn.commit()
        write_system_log(None, 'REGISTER_SUCCESS', f"User: {request.form['reg_username']}")
        return redirect(url_for('login', success='Đăng ký thành công! Đăng nhập ngay.'))
    except sqlite3.IntegrityError:
        return redirect(url_for('login', error='Tên tài khoản đã tồn tại!'))
    except Exception as e:
        print(f"Lỗi đăng ký: {e}")
        return redirect(url_for('login', error='Lỗi hệ thống, vui lòng thử lại!'))
    finally:
        conn.close()

@app.route('/dashboard')
def dashboard():
    if not session.get('loggedin'): return redirect(url_for('login'))
    s = request.args.get('search', '')
    conn = get_db_connection()
    user = conn.execute("SELECT balance FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    products = conn.execute("SELECT * FROM products WHERE name LIKE ?", ('%'+s+'%',)).fetchall()
    conn.close()
    return render_template('dashboard.html', username=session['username'], role=session['role'], products=products, search_query=s, cart=session.get('cart', []), cart_total=format_price(sum([parse_price(i['price']) for i in session.get('cart', [])])), balance=format_price(user['balance']))

@app.route('/product', methods=['GET'])
def product_detail():
    if not session.get('loggedin'): return redirect(url_for('login'))
    p_id = request.args.get('id')
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (p_id,)).fetchone()
    user = conn.execute("SELECT balance FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('product.html', username=session['username'], product=product, cart=session.get('cart', []), cart_total=format_price(sum([parse_price(item['price']) for item in session.get('cart', [])])), balance=format_price(user['balance']))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('loggedin'): return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute("UPDATE users SET full_name=?, email=?, password=? WHERE id=?", (request.form['full_name'], request.form['email'], request.form['password'], session['user_id']))
        conn.commit(); write_system_log(session['user_id'], 'PROFILE_UPDATE', "Success")
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user_info=user, username=session['username'])

@app.route('/wallet')
def wallet():
    if not session.get('loggedin'): return redirect(url_for('login'))
    conn = get_db_connection()
    user = conn.execute("SELECT balance FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('wallet.html', username=session['username'], balance=format_price(user['balance']))

@app.route('/deposit', methods=['POST'])
def deposit():
    if not session.get('loggedin'): return redirect(url_for('login'))
    amount = parse_price(request.form.get('amount', '0'))
    conn = get_db_connection()
    conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, session['user_id']))
    conn.commit(); conn.close()
    return redirect(url_for('wallet', msg='Nạp tiền thành công!'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if not session.get('loggedin'): return redirect(url_for('login'))
    cart = session.get('cart', [])
    total_val = sum([parse_price(i['price']) for i in cart])
    conn = get_db_connection()
    user = conn.execute("SELECT balance FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    if total_val > user['balance']:
        conn.close(); return redirect(url_for('payment_failed', error='Số dư không đủ!'))
    new_balance = user['balance'] - total_val
    conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, session['user_id']))
    order_code = f"ORD-{str(uuid.uuid4())[:8].upper()}"
    cur = conn.execute("INSERT INTO payments (user_id, order_code, total_amount, payment_method, status, created_at) VALUES (?, ?, ?, ?, ?, ?)", (session['user_id'], order_code, format_price(total_val), 'Wallet', 'Completed', datetime.now()))
    conn.execute("INSERT INTO payment_logs (payment_id, api_endpoint, raw_request, raw_response, created_at) VALUES (?, ?, ?, ?, ?)", (cur.lastrowid, PAYMENT_GATEWAY_URL, f"Pay_{total_val}", "Success", datetime.now()))
    conn.commit(); conn.close()
    session['cart'] = []; write_system_log(session['user_id'], 'CHECKOUT_SUCCESS', order_code)
    return redirect(url_for('payment_success', order_code=order_code, total=format_price(total_val)))

@app.route('/admin')
def admin_dashboard():
    if not session.get('loggedin') or session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('admin.html', users=users, products=products, username=session['username'])

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection()
    conn.execute("INSERT INTO products (name, price, image_url, rating, sold) VALUES (?, ?, ?, '5.0', '0')", (request.form['name'], request.form['price'], request.form['image']))
    conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_product/<int:id>')
def delete_product(id):
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection(); conn.execute("DELETE FROM products WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection(); conn.execute("DELETE FROM users WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/manage_balance', methods=['POST'])
def manage_balance():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    uid, amt, act = request.form.get('user_id'), parse_price(request.form.get('amount', '0')), request.form.get('action')
    conn = get_db_connection()
    if act == 'add': conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amt, uid))
    else: conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amt, uid))
    conn.commit(); conn.close()
    return redirect(url_for('admin_dashboard', success='Thành công!'))
@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password, role, full_name, email, balance) VALUES (?, ?, ?, ?, ?, ?)",
                     (request.form['username'], request.form['password'], request.form['role'], 
                      request.form['full_name'], request.form['email'], parse_price(request.form['balance'])))
        conn.commit()
        write_system_log(session['user_id'], 'ADMIN_ADD_USER', f"Added: {request.form['username']}")
        return redirect(url_for('admin_dashboard', success='Thêm tài khoản thành công!'))
    except sqlite3.IntegrityError:
        return redirect(url_for('admin_dashboard', error='Lỗi: Tên đăng nhập đã tồn tại!'))
    finally:
        conn.close()

@app.route('/admin/edit_user', methods=['POST'])
def admin_edit_user():
    if session.get('role') != 'Administrator': return "403 Forbidden", 403
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET username=?, password=?, role=?, full_name=?, email=?, balance=? WHERE id=?",
                     (request.form['username'], request.form['password'], request.form['role'], 
                      request.form['full_name'], request.form['email'], parse_price(request.form['balance']), request.form['user_id']))
        conn.commit()
        write_system_log(session['user_id'], 'ADMIN_EDIT_USER', f"Edited ID: {request.form['user_id']}")
        return redirect(url_for('admin_dashboard', success='Cập nhật tài khoản thành công!'))
    except sqlite3.IntegrityError:
        return redirect(url_for('admin_dashboard', error='Lỗi: Tên đăng nhập bị trùng!'))
    finally:
        conn.close()

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    conn = get_db_connection()
    p = conn.execute("SELECT * FROM products WHERE id=?", (request.form['product_id'],)).fetchone()
    conn.close()
    if p:
        cart = session.get('cart', [])
        cart.append({'name': p['name'], 'price': p['price'], 'image': p['image_url']})
        session['cart'] = cart; session.modified = True
    return redirect(url_for('dashboard', cart_open=1))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    idx = int(request.form.get('item_index'))
    cart = session.get('cart', [])
    if 0 <= idx < len(cart): cart.pop(idx); session['cart'] = cart; session.modified = True
    return redirect(request.referrer)

@app.route('/qr_pay')
def qr_pay(): return render_template('qr_pay.html')

@app.route('/payment_success')
def payment_success(): return render_template('payment_success.html', order_code=request.args.get('order_code'), total=request.args.get('total'))

@app.route('/payment_failed')
def payment_failed(): return render_template('payment_failed.html', error=request.args.get('error'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == '__main__': 
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)