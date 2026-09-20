import os
import json
import secrets
import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for

app = Flask(__name__)

# -------------------------------------------------------------
# DATABASE PERSISTENCE SETUP
# 1. External Cloud DB (MongoDB Atlas) - RECOMMENDED
#    Set environment variable MONGO_URI in Render dashboard
# 2. Local Fallback (keys.json file)
# -------------------------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI", "")

use_mongo = False
mongo_col = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        db_mongo = client['dimzmods_db']
        mongo_col = db_mongo['keys']
        use_mongo = True
        print("Connected to Cloud MongoDB Atlas successfully!")
    except Exception as e:
        print("MongoDB connection failed, falling back to local keys.json:", e)

LOCAL_KEY_FILE = "keys.json"

def get_settings():
    if use_mongo:
        settings_col = db_mongo['settings']
        doc = settings_col.find_one({"_id": "config"})
        if doc:
            return doc.get("strict_mode", True)
        else:
            settings_col.insert_one({"_id": "config", "strict_mode": True})
            return True
    else:
        db = load_local_data()
        return db.get("strict_mode", True)

def set_settings(strict_mode):
    if use_mongo:
        settings_col = db_mongo['settings']
        settings_col.update_one({"_id": "config"}, {"$set": {"strict_mode": strict_mode}}, upsert=True)
    else:
        db = load_local_data()
        db["strict_mode"] = strict_mode
        save_local_data(db)

def load_local_data():
    if os.path.exists(LOCAL_KEY_FILE):
        try:
            with open(LOCAL_KEY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "strict_mode": True,
        "keys": {
            "DIMZ-ADMIN-888": {
                "max_devices": 10,
                "expire_at": "2030-12-31 23:59:59"
            }
        }
    }

def save_local_data(data):
    with open(LOCAL_KEY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_all_keys():
    if use_mongo:
        keys_dict = {}
        for doc in mongo_col.find():
            keys_dict[doc['key']] = {
                "max_devices": doc.get("max_devices", 1),
                "expire_at": doc.get("expire_at", "2030-12-31 23:59:59")
            }
        return keys_dict
    else:
        db = load_local_data()
        return db.get("keys", {})

def save_key(key_name, max_devices, expire_at):
    if use_mongo:
        mongo_col.update_one(
            {"key": key_name},
            {"$set": {"key": key_name, "max_devices": max_devices, "expire_at": expire_at}},
            upsert=True
        )
    else:
        db = load_local_data()
        db["keys"][key_name] = {
            "max_devices": max_devices,
            "expire_at": expire_at
        }
        save_local_data(db)

def remove_key(key_name):
    if use_mongo:
        mongo_col.delete_one({"key": key_name})
    else:
        db = load_local_data()
        if key_name in db.get("keys", {}):
            del db["keys"][key_name]
            save_local_data(db)


# -------------------------------------------------------------
# 1. AUTHENTICATION ENDPOINT (Matches App Binary)
# -------------------------------------------------------------
@app.route('/dimzff', methods=['POST'])
def handle_auth():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"status": "ERROR", "message": "Invalid JSON"}), 200

        licence = data.get("licence")
        device_uuid = data.get("uuid")
        timestamp = data.get("timestamp")

        if not licence or not device_uuid or not timestamp:
            return jsonify({"status": "ERROR", "message": "Missing fields (licence, uuid, timestamp)"}), 200

        strict_mode = get_settings()
        keys = get_all_keys()

        now = datetime.datetime.now()

        # Check key validity
        if licence in keys:
            key_info = keys[licence]
            expire_dt = datetime.datetime.strptime(key_info["expire_at"], "%Y-%m-%d %H:%M:%S")
            
            if now > expire_dt:
                return jsonify({
                    "status": "ERROR",
                    "message": "Licence Key Expired!"
                }), 200

            expire_date_str = key_info["expire_at"]
            max_dev = key_info.get("max_devices", 1)

        elif not strict_mode:
            # Free Mode: Accept any key with 30 days expiry
            expire_date_str = (now + datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            max_dev = -1
        else:
            return jsonify({
                "status": "ERROR",
                "message": "Invalid Licence Key!"
            }), 200

        # Successful Auth Response
        response = {
            "status": "OK",
            "message": "Welcome to DimzMods!",
            "expired_at": expire_date_str,
            "signature": "b583fb0037725d79cfaa019ac53342785c992297606b9d762bfe72f206f8c75f",
            "canary": "cde2c37ab46e42ff1f4a55085cdddbdb9ec44ecc5405c0209535a14c5a0d5ebf",
            "surplusKey": 5,
            "offset_engine": 5455596745,
            "offset_hmac": "083fd9470cfa3d1c7182e2137250153ea3550d9ad581ffbdd59f6ab55124345c",
            "devices_used": 1,
            "devices_max": max_dev
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 200


# -------------------------------------------------------------
# 2. WEB ADMIN PANEL FOR MANAGING KEYS
# -------------------------------------------------------------
@app.route('/', methods=['GET'])
@app.route('/admin', methods=['GET'])
def admin_panel():
    strict_mode = get_settings()
    keys_raw = get_all_keys()

    now = datetime.datetime.now()
    formatted_keys = []

    for k, info in keys_raw.items():
        exp_dt = datetime.datetime.strptime(info["expire_at"], "%Y-%m-%d %H:%M:%S")
        formatted_keys.append({
            "key": k,
            "max_devices": info.get("max_devices", 1),
            "expire_at": info["expire_at"],
            "is_expired": now > exp_dt
        })

    message = request.args.get('msg', '')
    storage_type = "Cloud Database (MongoDB)" if use_mongo else "Local File (keys.json)"
    return render_template('admin.html', keys=formatted_keys, strict_mode=strict_mode, message=message, storage_type=storage_type)


@app.route('/admin/create', methods=['POST'])
def create_key():
    key_name = request.form.get('key_name', '').strip()
    duration_days = int(request.form.get('duration_days', 30))
    max_devices = int(request.form.get('max_devices', 1))

    if not key_name:
        random_code = secrets.token_hex(4).upper()
        new_key = f"DIMZ-{random_code}"
    else:
        new_key = key_name

    if duration_days == 9999:
        expire_at = "2099-12-31 23:59:59"
    else:
        expire_at = (datetime.datetime.now() + datetime.timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M:%S")

    save_key(new_key, max_devices, expire_at)
    return redirect(url_for('admin_panel', msg=f"Key '{new_key}' created successfully!"))


@app.route('/admin/delete/<key_name>', methods=['GET'])
def delete_key(key_name):
    remove_key(key_name)
    return redirect(url_for('admin_panel', msg=f"Key '{key_name}' deleted."))


@app.route('/admin/toggle-mode', methods=['POST'])
def toggle_mode():
    new_mode = 'strict_mode' in request.form
    set_settings(new_mode)
    mode_str = "Strict Mode (Keys required)" if new_mode else "Free Mode (Any key accepted)"
    return redirect(url_for('admin_panel', msg=f"Server mode updated to: {mode_str}"))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
