# Render Server & Persistent Key Manager

Welcome to your complete **Render-ready Auth Server & Admin Dashboard**!

---

## 🔒 Keys Safe Protection (पुराने Keys कभी डिलीट नहीं होंगे)

Render जैसे Free hosting प्लेटफार्म पर जब भी आप कोड को **Update / Modify / Re-deploy** करते हैं, तो सर्वर रीस्टार्ट हो जाता है। 

Keys को 100% सुरक्षित रखने के लिए हमने 2 तरीके सेट किए हैं:

### 1. Cloud Database (MongoDB Atlas) - RECOMMENDED (100% Safe)
अगर आप [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (Free Cloud Database) का इस्तेमाल करेंगे, तो:
* आपका कोड चाहे कितनी बार भी बदलो, मॉडिफाई करो या डिलीट करके फिर डिप्लॉय करो — **आपकी बनी हुई पुरानी Keys कभी डिलीट नहीं होंगी!**
* **कैसे कनेक्ट करें**: Render Dashboard में Environment Variable में `MONGO_URI` जोड़ें (उदा. `mongodb+srv://user:pass@cluster...`).

### 2. Separate Local `keys.json` File
* अगर आप MongoDB नहीं जोड़ते हैं, तो यह Keys को अलग फ़ाइल `keys.json` में स्टोर रखेगा ताकि मुख्य ऐप कोड और डाटा अलग रहें।

---

## 📁 File Structure
```
render_server/
├── app.py                # Main Flask app (Server API + Persistent Key Logic)
├── keys.json             # Separate file storing keys (Isolated from App Code)
├── requirements.txt      # Dependencies (Flask, Gunicorn, PyMongo)
├── Procfile              # Render deployment configuration
└── templates/
    └── admin.html        # Modern Dark-themed Web Dashboard UI
```

---

## 🚀 How to Deploy on Render.com

1. **GitHub पर प्रोजेक्ट डालें**: `render_server` फ़ोल्डर की सभी फ़ाइलों को GitHub Repository में अपलोड करें।
2. **Render.com पर जाएं**: New Web Service बनाकर Repository चुनें।
3. **Settings**:
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app`
4. (Optional) **Environment Variable**: `MONGO_URI` = `mongodb+srv://...`
