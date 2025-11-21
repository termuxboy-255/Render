from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, flash
import requests
import json
import uuid
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kadili_boost_secret_key_2024'

ZENOPAY_API_KEY = "ONTf9wztQoDj-MaLB65NHdSQ0kQHwuSSkK1mdsvwNg1M3-uTDVE-6nLuWV2DU7rwnuIXWo7rO680BaSKcQpJqQ"
ZENOPAY_URL = "https://zenoapi.com/api/payments/mobile_money_tanzania"
SMM_API_KEY = "bf09d10508b719405c2384bdd9797808"
SMM_API_URL = "https://5smm.com/api/v2"

users = {}
providers = {}
categories = {}
services = {}
orders = []
deposits = {}

ADMIN_USERNAME = "Kadili"
ADMIN_PASSWORD = "Kadili@123"

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session or not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_user_balance(username):
    return users.get(username, {}).get('balance', 0)

def update_user_balance(username, amount):
    if username in users:
        users[username]['balance'] = users[username].get('balance', 0) + amount

def call_smm_api(action, params=None):
    data = {'key': SMM_API_KEY, 'action': action}
    if params:
        data.update(params)
    try:
        response = requests.post(SMM_API_URL, data=data)
        return response.json()
    except:
        return {'error': 'API Error'}

def base_html(content, balance=0, show_header=True):
    header = ""
    footer = ""
    if show_header:
        admin_link = '<a href="/admin">Admin Dashboard</a>' if session.get('is_admin') else ''
        header = f'''
        <div class="header">
            <div class="logo">KADILI BOOST</div>
            <div class="header-right">
                <div class="balance-box">TZS {balance:.2f}</div>
                <a href="/add-funds" class="btn-add">+</a>
                <button class="menu-btn" onclick="toggleMenu()">&#9776;</button>
            </div>
        </div>
        <div class="menu-overlay" id="menuOverlay" onclick="toggleMenu()"></div>
        <div class="menu-panel" id="menuPanel">
            <h3>Menu</h3>
            <a href="/dashboard">Home</a>
            <a href="/about">About Us</a>
            <a href="/our-services">Our Services</a>
            <a href="/contact">Contact Us</a>
            <a href="/orders">Order Logs</a>
            {admin_link}
            <a href="/logout" class="logout-btn">Logout</a>
        </div>'''
        footer = '''
        <div class="footer">
            <p>MADE WITH <span style="color:#ef4444;">&#9829;</span></p>
            <p>2024 KADILI BOOST</p>
        </div>'''
    
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KADILI BOOST</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:Arial,sans-serif;background:linear-gradient(135deg,#0a0e27,#1a1f3a);color:#e5e7eb;min-height:100vh;}}
.header{{background:#151a30;padding:1rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;border-bottom:2px solid #1e293b;}}
.logo{{font-size:1.5rem;font-weight:bold;color:#3b82f6;}}
.header-right{{display:flex;align-items:center;gap:1rem;}}
.balance-box{{background:#3b82f6;padding:0.5rem 1rem;border-radius:8px;font-weight:bold;}}
.btn{{background:#3b82f6;color:white;border:none;padding:0.7rem 1.5rem;border-radius:8px;cursor:pointer;font-weight:600;text-decoration:none;display:inline-block;}}
.btn:hover{{background:#2563eb;}}
.btn-add{{background:#10b981;color:white;width:35px;height:35px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;text-decoration:none;}}
.btn-add:hover{{background:#059669;}}
.menu-btn{{background:transparent;border:2px solid #3b82f6;color:#3b82f6;width:40px;height:40px;border-radius:8px;cursor:pointer;font-size:1.2rem;}}
.menu-btn:hover{{background:#3b82f6;color:white;}}
.menu-overlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);display:none;z-index:999;}}
.menu-panel{{position:fixed;right:-280px;top:0;width:280px;height:100%;background:#151a30;transition:right 0.3s;z-index:1000;padding:2rem;overflow-y:auto;}}
.menu-panel.active{{right:0;}}
.menu-panel h3{{color:#3b82f6;margin-bottom:1.5rem;}}
.menu-panel a{{display:block;color:#e5e7eb;text-decoration:none;padding:1rem;margin:0.5rem 0;border-radius:8px;}}
.menu-panel a:hover{{background:#3b82f6;}}
.logout-btn{{background:#ef4444!important;color:white!important;margin-top:2rem!important;}}
.container{{max-width:1200px;margin:2rem auto;padding:0 1rem;}}
.card{{background:#151a30;border-radius:12px;padding:1.5rem;margin:1rem 0;border:1px solid #1e293b;}}
.card:hover{{box-shadow:0 4px 15px rgba(59,130,246,0.2);}}
.form-group{{margin:1rem 0;}}
.form-group label{{display:block;margin-bottom:0.5rem;color:#9ca3af;}}
.form-group input,.form-group select,.form-group textarea{{width:100%;padding:0.8rem;border:2px solid #1e293b;border-radius:8px;background:#0a0e27;color:#e5e7eb;font-size:1rem;}}
.form-group input:focus,.form-group select:focus{{outline:none;border-color:#3b82f6;}}
.alert{{padding:1rem;border-radius:8px;margin:1rem 0;}}
.alert-success{{background:rgba(16,185,129,0.2);border-left:4px solid #10b981;}}
.alert-error{{background:rgba(239,68,68,0.2);border-left:4px solid #ef4444;}}
.alert-info{{background:rgba(59,130,246,0.2);border-left:4px solid #3b82f6;}}
table{{width:100%;border-collapse:collapse;}}
th,td{{padding:0.8rem;text-align:left;border-bottom:1px solid #1e293b;}}
th{{background:#0a0e27;color:#3b82f6;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem;}}
.footer{{text-align:center;padding:2rem;margin-top:2rem;border-top:1px solid #1e293b;color:#9ca3af;}}
.modal{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;}}
.modal-content{{background:#151a30;padding:2rem;border-radius:12px;max-width:500px;margin:10% auto;}}
</style>
</head>
<body>
{header}
<div class="container">{content}</div>
{footer}
<script>
function toggleMenu(){{
var p=document.getElementById('menuPanel');
var o=document.getElementById('menuOverlay');
if(p.classList.contains('active')){{p.classList.remove('active');o.style.display='none';}}
else{{p.classList.add('active');o.style.display='block';}}
}}
</script>
</body>
</html>'''

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user'] = username
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        if username in users and users[username]['password'] == password:
            session['user'] = username
            session['is_admin'] = False
            return redirect(url_for('dashboard'))
        msg = '<div class="alert alert-error">Invalid credentials</div>'
    
    content = f'''
    <div style="max-width:400px;margin:4rem auto;">
        <div class="card">
            <h2 style="text-align:center;color:#3b82f6;margin-bottom:1.5rem;">KADILI BOOST</h2>
            {msg}
            <form method="POST">
                <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
                <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
                <button type="submit" class="btn" style="width:100%;">Login</button>
            </form>
            <p style="text-align:center;margin-top:1rem;">No account? <a href="/register" style="color:#3b82f6;">Register</a></p>
        </div>
    </div>'''
    return base_html(content, show_header=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        if username in users:
            msg = '<div class="alert alert-error">Username exists</div>'
        else:
            users[username] = {'password': password, 'email': email, 'balance': 0}
            return redirect(url_for('login'))
    
    content = f'''
    <div style="max-width:400px;margin:4rem auto;">
        <div class="card">
            <h2 style="text-align:center;color:#3b82f6;margin-bottom:1.5rem;">Register</h2>
            {msg}
            <form method="POST">
                <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
                <div class="form-group"><label>Email</label><input type="email" name="email" required></div>
                <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
                <button type="submit" class="btn" style="width:100%;">Register</button>
            </form>
            <p style="text-align:center;margin-top:1rem;">Have account? <a href="/login" style="color:#3b82f6;">Login</a></p>
        </div>
    </div>'''
    return base_html(content, show_header=False)

@app.route('/dashboard')
@login_required
def dashboard():
    balance = get_user_balance(session['user'])
    cats = ""
    for cid, c in categories.items():
        cats += f'<div class="card" onclick="location.href=\'/category/{cid}\'" style="cursor:pointer;"><h3 style="color:#3b82f6;">{c["name"]}</h3><p style="color:#9ca3af;">{c.get("description","Click to view")}</p></div>'
    if not cats:
        cats = '<div class="alert alert-info">No categories available yet.</div>'
    content = f'<h1 style="margin-bottom:1.5rem;">Select Category</h1><div class="grid">{cats}</div>'
    return base_html(content, balance)

@app.route('/category/<cid>')
@login_required
def category_services(cid):
    balance = get_user_balance(session['user'])
    svcs = ""
    for sid, s in services.items():
        if s.get('category_id') == cid:
            svcs += f'<div class="card"><h3 style="color:#3b82f6;">{s["name"]}</h3><p>Rate: TZS {s["rate"]:.2f}/1000</p><p>Min: {s["min"]} | Max: {s["max"]}</p><a href="/order/{sid}" class="btn" style="margin-top:1rem;">Order</a></div>'
    if not svcs:
        svcs = '<div class="alert alert-info">No services in this category.</div>'
    content = f'<h1>Select Service</h1><div class="grid">{svcs}</div>'
    return base_html(content, balance)

@app.route('/order/<sid>', methods=['GET', 'POST'])
@login_required
def place_order(sid):
    if sid not in services:
        return redirect(url_for('dashboard'))
    s = services[sid]
    balance = get_user_balance(session['user'])
    msg = ""
    if request.method == 'POST':
        link = request.form['link']
        qty = int(request.form['quantity'])
        if qty < s['min'] or qty > s['max']:
            msg = f'<div class="alert alert-error">Quantity must be {s["min"]}-{s["max"]}</div>'
        else:
            cost = s['rate'] * qty / 1000
            if balance < cost:
                msg = '<div class="alert alert-error">Insufficient balance</div>'
            else:
                result = call_smm_api('add', {'service': s['provider_service_id'], 'link': link, 'quantity': qty})
                if 'order' in result:
                    orders.append({'order_id': result['order'], 'user': session['user'], 'service_name': s['name'], 'link': link, 'quantity': qty, 'cost': cost, 'status': 'Pending', 'created_at': datetime.now().isoformat()})
                    update_user_balance(session['user'], -cost)
                    return redirect(url_for('orders_log'))
                msg = f'<div class="alert alert-error">Error: {result.get("error","Failed")}</div>'
    content = f'''
    <div class="card" style="max-width:600px;margin:2rem auto;">
        <h2 style="color:#3b82f6;">{s['name']}</h2>
        <p>Rate: TZS {s['rate']:.2f}/1000 | Min: {s['min']} | Max: {s['max']}</p>
        {msg}
        <form method="POST">
            <div class="form-group"><label>Link/URL</label><input type="text" name="link" required></div>
            <div class="form-group"><label>Quantity</label><input type="number" name="quantity" min="{s['min']}" max="{s['max']}" required></div>
            <button type="submit" class="btn" style="width:100%;">Place Order</button>
        </form>
    </div>'''
    return base_html(content, balance)

@app.route('/add-funds', methods=['GET', 'POST'])
@login_required
def add_funds():
    balance = get_user_balance(session['user'])
    msg = ""
    last_deposit = None
    if request.method == 'POST':
        phone = request.form['phone']
        amount = int(request.form['amount'])
        if amount < 1000:
            msg = '<div class="alert alert-error">Minimum is TZS 1000</div>'
        else:
            oid = str(uuid.uuid4())
            try:
                requests.post(ZENOPAY_URL, headers={"Content-Type": "application/json", "x-api-key": ZENOPAY_API_KEY}, json={"order_id": oid, "buyer_email": users[session['user']]['email'], "buyer_name": session['user'], "buyer_phone": phone, "amount": amount, "webhook_url": request.url_root + "webhook/zenopay"})
                deposits[oid] = {'user': session['user'], 'amount': amount, 'status': 'Pending'}
                last_deposit = oid
                msg = '<div class="alert alert-info">Check your phone for USSD prompt! After payment, click Verify Payment.</div>'
            except:
                msg = '<div class="alert alert-error">Payment error</div>'
    
    # Get user's pending deposits
    user_deposits = ""
    for did, d in deposits.items():
        if d['user'] == session['user'] and d['status'] == 'Pending':
            user_deposits += f'<div class="alert alert-info" style="display:flex;justify-content:space-between;align-items:center;"><span>TZS {d["amount"]} - {d["status"]}</span><button class="btn" onclick="checkPayment(\'{did}\')">Verify</button></div>'
    
    content = f'''
    <div class="card" style="max-width:500px;margin:2rem auto;">
        <h2 style="color:#3b82f6;">Add Funds</h2>
        <div class="alert alert-info">Minimum: TZS 1,000</div>
        {msg}
        <form method="POST">
            <div class="form-group"><label>Phone (06XXXXXXXX or 07XXXXXXXX)</label><input type="tel" name="phone" pattern="0[67][0-9]{{8}}" placeholder="0652117588" required></div>
            <div class="form-group"><label>Amount (TZS)</label><input type="number" name="amount" min="1000" required></div>
            <button type="submit" class="btn" style="width:100%;">Pay Now</button>
        </form>
    </div>
    {f'<div class="card" style="max-width:500px;margin:1rem auto;"><h3>Pending Payments</h3>{user_deposits}</div>' if user_deposits else ''}
    <div id="verifyResult"></div>
    <script>
    function checkPayment(oid) {{
        fetch('/check-payment/' + oid)
        .then(r => r.json())
        .then(data => {{
            if(data.status === 'success') {{
                document.getElementById('verifyResult').innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
                setTimeout(() => location.reload(), 1500);
            }} else {{
                document.getElementById('verifyResult').innerHTML = '<div class="alert alert-info">' + data.message + '</div>';
            }}
        }});
    }}
    </script>'''
    return base_html(content, balance)

@app.route('/webhook/zenopay', methods=['POST'])
def zenopay_webhook():
    try:
        data = request.json
        if data:
            oid = data.get('order_id')
            status = data.get('payment_status')
            if oid and oid in deposits:
                if status == 'COMPLETED' or status == 'completed':
                    user = deposits[oid]['user']
                    amount = deposits[oid]['amount']
                    if deposits[oid]['status'] != 'Completed':
                        update_user_balance(user, amount)
                        deposits[oid]['status'] = 'Completed'
    except:
        pass
    return jsonify({'status': 'ok'})

@app.route('/check-payment/<oid>')
@login_required
def check_payment(oid):
    if oid in deposits and deposits[oid]['user'] == session['user']:
        try:
            headers = {"x-api-key": ZENOPAY_API_KEY}
            response = requests.get(f"https://zenoapi.com/api/payments/order-status?order_id={oid}", headers=headers)
            data = response.json()
            if data.get('resultcode') == '000':
                order_info = data.get('data', [{}])[0]
                if order_info.get('payment_status') == 'COMPLETED':
                    if deposits[oid]['status'] != 'Completed':
                        update_user_balance(session['user'], deposits[oid]['amount'])
                        deposits[oid]['status'] = 'Completed'
                    return jsonify({'status': 'success', 'message': 'Payment confirmed!'})
                return jsonify({'status': 'pending', 'message': 'Payment pending'})
        except:
            pass
    return jsonify({'status': 'error', 'message': 'Could not verify'})

@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    msg = ""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_balance':
            username = request.form['username']
            amount = float(request.form['amount'])
            if username in users:
                update_user_balance(username, amount)
                msg = f'<div class="alert alert-success">Added TZS {amount:.2f} to {username}</div>'
            else:
                msg = '<div class="alert alert-error">User not found</div>'
        elif action == 'set_balance':
            username = request.form['username']
            amount = float(request.form['amount'])
            if username in users:
                users[username]['balance'] = amount
                msg = f'<div class="alert alert-success">Set {username} balance to TZS {amount:.2f}</div>'
    
    rows = ""
    for uname, udata in users.items():
        bal = udata.get('balance', 0)
        email = udata.get('email', 'N/A')
        rows += f'''<tr>
            <td>{uname}</td>
            <td>{email}</td>
            <td>TZS {bal:.2f}</td>
            <td>
                <form method="POST" style="display:inline;">
                    <input type="hidden" name="action" value="add_balance">
                    <input type="hidden" name="username" value="{uname}">
                    <input type="number" name="amount" placeholder="Amount" style="width:100px;padding:5px;background:#0a0e27;border:1px solid #1e293b;color:#e5e7eb;border-radius:4px;" required>
                    <button type="submit" class="btn" style="padding:5px 10px;">Add</button>
                </form>
            </td>
        </tr>'''
    if not rows:
        rows = '<tr><td colspan="4" style="text-align:center;">No users yet</td></tr>'
    
    content = f'''
    <h1>Manage Users</h1>{msg}
    <div class="card" style="overflow-x:auto;">
        <table>
            <thead><tr><th>Username</th><th>Email</th><th>Balance</th><th>Add Funds</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    <div class="card">
        <h3>Set User Balance</h3>
        <form method="POST">
            <input type="hidden" name="action" value="set_balance">
            <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
            <div class="form-group"><label>New Balance (TZS)</label><input type="number" step="0.01" name="amount" required></div>
            <button type="submit" class="btn">Set Balance</button>
        </form>
    </div>
    <div class="card">
        <h3>Pending Deposits</h3>
        <table>
            <thead><tr><th>Order ID</th><th>User</th><th>Amount</th><th>Status</th></tr></thead>
            <tbody>'''
    for did, d in deposits.items():
        content += f'<tr><td>{did[:16]}...</td><td>{d["user"]}</td><td>TZS {d["amount"]}</td><td>{d["status"]}</td></tr>'
    if not deposits:
        content += '<tr><td colspan="4" style="text-align:center;">No deposits</td></tr>'
    content += '</tbody></table></div>'
    return base_html(content, 0)

@app.route('/orders')
@login_required
def orders_log():
    balance = get_user_balance(session['user'])
    user_orders = orders if session.get('is_admin') else [o for o in orders if o['user'] == session['user']]
    rows = ""
    for o in user_orders:
        rows += f'<tr><td>{o["order_id"]}</td><td>{o["service_name"]}</td><td>{o["quantity"]}</td><td>TZS {o["cost"]:.2f}</td><td>{o["status"]}</td></tr>'
    if not rows:
        rows = '<tr><td colspan="5" style="text-align:center;">No orders</td></tr>'
    content = f'<h1>Order Logs</h1><div class="card" style="overflow-x:auto;"><table><thead><tr><th>ID</th><th>Service</th><th>Qty</th><th>Cost</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>'
    return base_html(content, balance)

@app.route('/admin')
@admin_required
def admin_dashboard():
    content = f'''
    <h1>Admin Dashboard</h1>
    <div class="grid">
        <div class="card"><h3>Providers</h3><a href="/admin/providers" class="btn">Manage</a></div>
        <div class="card"><h3>Categories</h3><a href="/admin/categories" class="btn">Manage</a></div>
        <div class="card"><h3>Services</h3><a href="/admin/services" class="btn">Manage</a></div>
        <div class="card"><h3>Users</h3><p>{len(users)} registered</p><a href="/admin/users" class="btn" style="margin-top:0.5rem;">Manage</a></div>
        <div class="card"><h3>Orders</h3><p>{len(orders)} total</p><a href="/orders" class="btn" style="margin-top:0.5rem;">View All</a></div>
        <div class="card"><h3>Deposits</h3><p>{len(deposits)} total</p><a href="/admin/users" class="btn" style="margin-top:0.5rem;">View</a></div>
    </div>'''
    return base_html(content, 0)

@app.route('/admin/providers', methods=['GET', 'POST'])
@admin_required
def admin_providers():
    msg = ""
    if request.method == 'POST':
        result = call_smm_api('services')
        if isinstance(result, list):
            for svc in result:
                providers[str(svc['service'])] = svc
            msg = f'<div class="alert alert-success">Synced {len(result)} services!</div>'
        else:
            msg = '<div class="alert alert-error">Sync failed</div>'
    rows = ""
    for p in providers.values():
        rows += f'<tr><td>{p["service"]}</td><td>{p["name"]}</td><td>{p["category"]}</td><td>${p["rate"]}</td><td>{p["min"]}/{p["max"]}</td></tr>'
    if not rows:
        rows = '<tr><td colspan="5" style="text-align:center;">Click Sync to load providers</td></tr>'
    content = f'''
    <h1>Providers</h1>
    <div class="card"><form method="POST"><button type="submit" class="btn">Sync from 5SMM</button></form></div>
    {msg}
    <div class="card" style="overflow-x:auto;"><table><thead><tr><th>ID</th><th>Name</th><th>Category</th><th>Rate</th><th>Min/Max</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    return base_html(content, 0)

@app.route('/admin/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    msg = ""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            cid = str(uuid.uuid4())[:8]
            categories[cid] = {'name': request.form['name'], 'description': request.form.get('description', '')}
            msg = '<div class="alert alert-success">Added!</div>'
        elif action == 'delete':
            cid = request.form['cat_id']
            if cid in categories:
                del categories[cid]
                msg = '<div class="alert alert-success">Deleted!</div>'
    rows = ""
    for cid, c in categories.items():
        rows += f'<tr><td>{c["name"]}</td><td>{c.get("description","")}</td><td><form method="POST" style="display:inline;"><input type="hidden" name="action" value="delete"><input type="hidden" name="cat_id" value="{cid}"><button type="submit" class="btn" style="background:#ef4444;">Delete</button></form></td></tr>'
    if not rows:
        rows = '<tr><td colspan="3" style="text-align:center;">No categories</td></tr>'
    content = f'''
    <h1>Categories</h1>{msg}
    <div class="card">
        <h3>Add Category</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add">
            <div class="form-group"><label>Name</label><input type="text" name="name" required></div>
            <div class="form-group"><label>Description</label><input type="text" name="description"></div>
            <button type="submit" class="btn">Add</button>
        </form>
    </div>
    <div class="card" style="overflow-x:auto;"><table><thead><tr><th>Name</th><th>Description</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    return base_html(content, 0)

@app.route('/admin/services', methods=['GET', 'POST'])
@admin_required
def admin_services():
    msg = ""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            sid = str(uuid.uuid4())[:8]
            services[sid] = {'name': request.form['name'], 'category_id': request.form['category_id'], 'provider_service_id': request.form['provider_service_id'], 'rate': float(request.form['rate']), 'min': int(request.form['min']), 'max': int(request.form['max'])}
            msg = '<div class="alert alert-success">Added!</div>'
        elif action == 'delete':
            sid = request.form['svc_id']
            if sid in services:
                del services[sid]
                msg = '<div class="alert alert-success">Deleted!</div>'
    cat_opts = ''.join([f'<option value="{cid}">{c["name"]}</option>' for cid, c in categories.items()])
    prov_opts = ''.join([f'<option value="{p["service"]}">{p["name"]} ({p["service"]})</option>' for p in providers.values()])
    rows = ""
    for sid, s in services.items():
        cname = categories.get(s['category_id'], {}).get('name', 'N/A')
        rows += f'<tr><td>{s["name"]}</td><td>{cname}</td><td>TZS {s["rate"]:.2f}</td><td>{s["min"]}/{s["max"]}</td><td><form method="POST" style="display:inline;"><input type="hidden" name="action" value="delete"><input type="hidden" name="svc_id" value="{sid}"><button type="submit" class="btn" style="background:#ef4444;">Del</button></form></td></tr>'
    if not rows:
        rows = '<tr><td colspan="5" style="text-align:center;">No services</td></tr>'
    content = f'''
    <h1>Services</h1>{msg}
    <div class="card">
        <h3>Add Service</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add">
            <div class="form-group"><label>Name</label><input type="text" name="name" required></div>
            <div class="form-group"><label>Category</label><select name="category_id" required><option value="">Select</option>{cat_opts}</select></div>
            <div class="form-group"><label>Provider Service</label><select name="provider_service_id" required><option value="">Select</option>{prov_opts}</select></div>
            <div class="form-group"><label>Rate (TZS/1000)</label><input type="number" step="0.01" name="rate" required></div>
            <div class="form-group"><label>Min</label><input type="number" name="min" required></div>
            <div class="form-group"><label>Max</label><input type="number" name="max" required></div>
            <button type="submit" class="btn">Add</button>
        </form>
    </div>
    <div class="card" style="overflow-x:auto;"><table><thead><tr><th>Name</th><th>Category</th><th>Rate</th><th>Min/Max</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    return base_html(content, 0)

@app.route('/about')
@login_required
def about():
    content = '<div class="card"><h1 style="color:#3b82f6;">About KADILI BOOST</h1><p style="margin:1rem 0;line-height:1.8;">Your trusted partner for social media growth. We provide quality SMM services at affordable prices.</p><h3 style="color:#3b82f6;margin-top:1.5rem;">Why Us?</h3><p>- Fast Delivery<br>- 24/7 Support<br>- Secure Payments<br>- Quality Services</p></div>'
    return base_html(content, get_user_balance(session['user']))

@app.route('/our-services')
@login_required
def our_services():
    content = '<div class="card"><h1 style="color:#3b82f6;">Our Services</h1><div class="grid"><div class="card"><h3>Instagram</h3><p>Followers, Likes, Views</p></div><div class="card"><h3>TikTok</h3><p>Followers, Likes, Views</p></div><div class="card"><h3>Facebook</h3><p>Likes, Followers</p></div><div class="card"><h3>YouTube</h3><p>Views, Subscribers</p></div><div class="card"><h3>Twitter</h3><p>Followers, Likes</p></div><div class="card"><h3>More...</h3><p>Telegram, Spotify</p></div></div></div>'
    return base_html(content, get_user_balance(session['user']))

@app.route('/contact')
@login_required
def contact():
    content = '<div class="card" style="max-width:600px;margin:2rem auto;"><h1 style="color:#3b82f6;">Contact Us</h1><p style="margin:1.5rem 0;"><strong>Email:</strong> support@kadiliboost.com</p><p style="margin:1.5rem 0;"><strong>WhatsApp:</strong> +255 752 117 588</p><p style="margin:1.5rem 0;"><strong>Hours:</strong> 24/7 Support</p></div>'
    return base_html(content, get_user_balance(session['user']))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
