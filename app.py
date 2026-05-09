#Credit:- Wotax exe!
"""Before sharing the src with other please give credit to Wotax who made this"""


import os
from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
import binascii
import aiohttp
import requests
import json
import like_pb2
import like_count_pb2
import uid_generator_pb2
from google.protobuf.message import DecodeError
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import secrets
from flask import session, redirect, url_for, render_template

app = Flask(__name__)

base_dir = os.path.abspath(os.path.dirname(__file__))
persistent_dir = os.environ.get('DATABASE_DIR') or os.environ.get('RENDER_DATA_DIR') or os.path.join(base_dir, 'instance')
os.makedirs(persistent_dir, exist_ok=True)
api_db_path = os.path.join(persistent_dir, 'api_keys.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or f'sqlite:///{api_db_path}'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey')  # Change this to a secure key
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    daily_limit = db.Column(db.Integer, nullable=False)
    expiration_days = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_reset = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usage_today = db.Column(db.Integer, default=0)
    total_requests = db.Column(db.Integer, default=0)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, default='bhuwan')
    password = db.Column(db.String(120), default='bhuwan')

with app.app_context():
    db.create_all()

def normalize_datetime(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

def load_tokens(server_name):
    REPO = "mahadevihik0-cyber/tokens"
    BASE_URL = f"https://raw.githubusercontent.com/{REPO}/main/"
    
    try:
        if server_name == "IND":
            url = BASE_URL + "token_ind.json"
        elif server_name in {"BR", "NA", "US", "SAC"}:
            url = BASE_URL + "token_br.json"
        else:
            url = BASE_URL + "token_ag.json"
            
        print(f"Attempting to load tokens from: {url}")  # Debug print
            
        response = requests.get(url, timeout=10)  # Increased timeout
        print(f"Response status: {response.status_code}")  # Debug print
        
        if response.status_code == 200:
            tokens = response.json()
            print(f"Successfully loaded {len(tokens)} tokens")  # Debug print
            return tokens
        else:
            app.logger.error(f"Failed to fetch tokens from {url}: {response.status_code}")
            print(f"Response content: {response.text[:200]}")  # Print first 200 chars of response
            return None
    except Exception as e:
        app.logger.error(f"Error loading tokens for server {server_name}: {e}")
        print(f"Exception details: {e}")
        return None

def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting message: {e}")
        return None

def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating protobuf message: {e}")
        return None

async def send_request(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 12; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2022.3.47f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB52"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers) as response:
                if response.status != 200:
                    app.logger.error(f"Request failed with status code: {response.status}")
                    return response.status
                return await response.text()
    except Exception as e:
        app.logger.error(f"Exception in send_request: {e}")
        return None

async def send_multiple_requests(uid, server_name):
    try:
        region = server_name
        protobuf_message = create_protobuf_message(uid, region)
        if protobuf_message is None:
            app.logger.error("Failed to create protobuf message.")
            return None
        encrypted_uid = encrypt_message(protobuf_message)
        if encrypted_uid is None:
            app.logger.error("Encryption failed.")
            return None
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/LikeProfile"
        elif server_name in {"BR", "US"}:
            url = "https://client.us.freefiremobile.com/LikeProfile"
        else:
            url = "https://clientbp.ggblueshark.com/LikeProfile"
        app.logger.info(f"Sending LikeProfile requests to {url} for region {server_name}")
        tasks = []
        tokens = load_tokens(server_name)
        if tokens is None:
            app.logger.error("Failed to load tokens.")
            return None
        for i in range(100):
            token = tokens[i % len(tokens)]["token"]
            tasks.append(send_request(encrypted_uid, token, url))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    except Exception as e:
        app.logger.error(f"Exception in send_multiple_requests: {e}")
        return None


def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating uid protobuf: {e}")
        return None

def enc(uid):
    protobuf_data = create_protobuf(uid)
    if protobuf_data is None:
        return None
    encrypted_uid = encrypt_message(protobuf_data)
    return encrypted_uid

def make_request(encrypt, server_name, token):
    try:
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif server_name in {"BR", "US"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
        app.logger.info(f"Using URL {url} for region {server_name}")
        edata = bytes.fromhex(encrypt)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 12; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2022.3.47f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB52"
        }
        response = requests.post(url, data=edata, headers=headers, verify=False)
        hex_data = response.content.hex()
        binary = bytes.fromhex(hex_data)
        decode = decode_protobuf(binary)
        if decode is None:
            app.logger.error("Protobuf decoding returned None.")
        return decode
    except Exception as e:
        app.logger.error(f"Error in make_request: {e}")
        return None

def decode_protobuf(binary):
    try:
        items = like_count_pb2.Info()
        items.ParseFromString(binary)
        return items
    except DecodeError as e:
        app.logger.error(f"Error decoding Protobuf data: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error during protobuf decoding: {e}")
        return None

def fetch_player_info(uid):
    try:
        url = f"https://wotaxxdev-api.vercel.app/info?uid={uid}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            player_data = data.get("playerData", {})
            return {
                "Level": player_data.get("level", "NA"),
                "Region": player_data.get("region", "NA"),
                "ReleaseVersion": player_data.get("releaseVersion", "NA")
            }
        else:
            app.logger.error(f"Player info API failed with status code: {response.status_code}")
            return {"Level": "NA", "Region": "NA", "ReleaseVersion": "NA"}
    except Exception as e:
        app.logger.error(f"Error fetching player info from API: {e}")
        return {"Level": "NA", "Region": "NA", "ReleaseVersion": "NA"}

def validate_key(api_key):
    key_entry = APIKey.query.filter_by(key=api_key).first()
    if not key_entry:
        return False, "Invalid key"
    now = datetime.now(timezone.utc)
    created_at = normalize_datetime(key_entry.created_at)
    last_reset = normalize_datetime(key_entry.last_reset)
    if now > created_at + timedelta(days=key_entry.expiration_days):
        return False, "Key expired"
    if now.date() > last_reset.date():
        key_entry.usage_today = 0
        key_entry.last_reset = now
        db.session.commit()
    if key_entry.usage_today >= key_entry.daily_limit:
        return False, "Daily limit exceeded"
    return True, key_entry

@app.route('/like', methods=['GET'])
def handle_requests():
    uid = request.args.get("uid")
    server_name = request.args.get("server_name", "").upper()
    api_key = request.args.get("key")
    
    if not api_key:
        keys = APIKey.query.all()
        now = datetime.now(timezone.utc)
        active_keys = [k for k in keys if now < normalize_datetime(k.created_at) + timedelta(days=k.expiration_days)]
        total_requests = sum([k.total_requests for k in keys])
        return jsonify({
            "error": "API key required",
            "message": "This API endpoint requires a valid API key to access",
            "total_active_keys": len(active_keys),
            "total_requests_done": total_requests,
            "info": "Get an API key from the admin dashboard to access this service"
        }), 401
    
    valid, key_entry = validate_key(api_key)
    if not valid:
        return jsonify({"error": key_entry}), 400
    if not uid:
        return jsonify({"error": "UID is required"}), 400

    try:
        def process_request():
            player_info = fetch_player_info(uid)
            region = player_info["Region"]
            level = player_info["Level"]
            release_version = player_info["ReleaseVersion"]

            if region != "NA":
                server_name_used = region
                app.logger.info(f"Using API-detected region: {server_name_used}")
            else:
                server_name_used = "BD"
                app.logger.info(f"API region unavailable, defaulting to BD server")

            if server_name:
                server_name_used = server_name
                app.logger.info(f"Overriding with provided server_name: {server_name_used}")

            tokens = load_tokens(server_name_used)
            if tokens is None:
                raise Exception("Failed to load tokens.")
            token = tokens[0]['token']
            encrypted_uid = enc(uid)
            if encrypted_uid is None:
                raise Exception("Encryption of UID failed.")

            before = make_request(encrypted_uid, server_name_used, token)
            if before is None:
                raise Exception("Failed to retrieve initial player info.")
            try:
                jsone = MessageToJson(before)
            except Exception as e:
                raise Exception(f"Error converting 'before' protobuf to JSON: {e}")
            data_before = json.loads(jsone)
            before_like = data_before.get('AccountInfo', {}).get('Likes', 0)
            try:
                before_like = int(before_like)
            except Exception:
                before_like = 0
            app.logger.info(f"Likes before command: {before_like}")

            asyncio.run(send_multiple_requests(uid, server_name_used))

            after = make_request(encrypted_uid, server_name_used, token)
            if after is None:
                raise Exception("Failed to retrieve player info after like requests.")
            try:
                jsone_after = MessageToJson(after)
            except Exception as e:
                raise Exception(f"Error converting 'after' protobuf to JSON: {e}")
            data_after = json.loads(jsone_after)
            after_like = int(data_after.get('AccountInfo', {}).get('Likes', 0))
            player_uid = int(data_after.get('AccountInfo', {}).get('UID', 0))
            player_name = str(data_after.get('AccountInfo', {}).get('PlayerNickname', ''))
            like_given = after_like - before_like
            status = 1 if like_given != 0 else 2
            result = {
                "LikesGivenByAPI": like_given,
                "LikesafterCommand": after_like,
                "LikesbeforeCommand": before_like,
                "PlayerNickname": player_name,
                "Region": region,
                "Level": level,
                "UID": player_uid,
                "ReleaseVersion": release_version,
                "status": status
            }
            return result

        result = process_request()
        key_entry.usage_today += 1
        key_entry.total_requests += 1
        db.session.commit()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.first()
        if not admin:
            admin = Admin(username='bhuwan', password='bhuwan')
            db.session.add(admin)
            db.session.commit()
        if username == admin.username and password == admin.password:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    keys = APIKey.query.all()
    total_keys = len(keys)
    now = datetime.now(timezone.utc)
    active_keys = len([k for k in keys if now < normalize_datetime(k.created_at) + timedelta(days=k.expiration_days)])
    total_requests = sum([k.total_requests for k in keys])
    expired_keys = len([k for k in keys if now >= normalize_datetime(k.created_at) + timedelta(days=k.expiration_days)])
    
    keys_data = []
    for key in keys:
        created_at = normalize_datetime(key.created_at)
        expires_at = created_at + timedelta(days=key.expiration_days)
        is_expired = now >= expires_at
        keys_data.append({
            'key': key.key,
            'daily_limit': key.daily_limit,
            'expires_at': expires_at.strftime('%Y-%m-%d'),
            'usage_today': key.usage_today,
            'total_requests': key.total_requests,
            'created_at': key.created_at.strftime('%Y-%m-%d'),
            'is_expired': is_expired
        })
    
    return render_template('admin_dashboard_new.html', keys=keys_data, total_keys=total_keys, 
                         active_keys=active_keys, total_requests=total_requests, expired_keys=expired_keys)

@app.route('/admin/create_key', methods=['GET', 'POST'])
def create_key():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        key_name = request.form.get('key_name').strip()
        if not key_name:
            return render_template('create_key_new.html', error="Key name is required")
        existing = APIKey.query.filter_by(key=key_name).first()
        if existing:
            return render_template('create_key_new.html', error="Key name already exists")
        daily_limit = int(request.form.get('daily_limit'))
        expiration_days = int(request.form.get('expiration_days'))
        new_key = APIKey(key=key_name, daily_limit=daily_limit, expiration_days=expiration_days)
        db.session.add(new_key)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('create_key_new.html')

@app.route('/admin/delete_key', methods=['POST'])
def delete_key():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    key_name = request.form.get('key_name')
    print(f"Deleting key: {key_name}")
    key_entry = APIKey.query.filter_by(key=key_name).first()
    if key_entry:
        db.session.delete(key_entry)
        db.session.commit()
        print(f"Key {key_name} deleted successfully")
    else:
        print(f"Key {key_name} not found")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('home_new.html', developer_name="BHUWAN")

@app.route('/admin/change_password', methods=['GET', 'POST'])
def change_password():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        admin = Admin.query.first()
        if old_password != admin.password:
            return render_template('change_password.html', error="Old password is incorrect")
        if new_password != confirm_password:
            return render_template('change_password.html', error="Passwords do not match")
        admin.password = new_password
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('change_password.html')

@app.route('/purchase')
def purchase_key():
    keys = APIKey.query.all()
    total_requests = sum([k.total_requests for k in keys])
    return render_template('purchase.html', total_requests=total_requests)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
