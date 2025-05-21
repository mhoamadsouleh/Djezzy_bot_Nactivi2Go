import telebot
import requests
import json
import os
from datetime import datetime, timedelta

TOKEN = '7723535106:AAH_8dQhq7QwVWh5JZf2iTrW4pgrT7vIykQ'
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'djezzy_users.json'

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def hide_number(num):
    return num[:4] + '*****' + num[-2:]

@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "📞 أرسل رقمك Djezzy (يبدأ بـ 07):")
    bot.register_next_step_handler(msg, process_number)

def process_number(msg):
    chat_id = msg.chat.id
    number = msg.text.strip()
    if number.startswith('07') and len(number) == 10:
        msisdn = '213' + number[1:]
        if send_otp(msisdn):
            bot.send_message(chat_id, "📩 تم إرسال رمز OTP إلى هاتفك، أرسله هنا:")
            bot.register_next_step_handler(msg, lambda m: process_otp(m, msisdn))
        else:
            bot.send_message(chat_id, "❌ فشل في إرسال OTP. حاول مرة أخرى.")
    else:
        bot.send_message(chat_id, "⚠️ الرقم غير صحيح. أعد المحاولة.")

def send_otp(msisdn):
    try:
        url = 'https://apim.djezzy.dz/oauth2/registration'
        data = f'msisdn={msisdn}&client_id=6E6CwTkp8H1CyQxraPmcEJPQ7xka&scope=smsotp'
        headers = {'User-Agent': 'Djezzy/2.6.7', 'Content-Type': 'application/x-www-form-urlencoded'}
        res = requests.post(url, data=data, headers=headers)
        return res.status_code == 200
    except:
        return False

def verify_otp(msisdn, otp):
    try:
        url = 'https://apim.djezzy.dz/oauth2/token'
        data = f'otp={otp}&mobileNumber={msisdn}&scope=openid&client_id=6E6CwTkp8H1CyQxraPmcEJPQ7xka&client_secret=MVpXHW_ImuMsxKIwrJpoVVMHjRsa&grant_type=mobile'
        headers = {'User-Agent': 'Djezzy/2.6.7', 'Content-Type': 'application/x-www-form-urlencoded'}
        res = requests.post(url, data=data, headers=headers)
        if res.status_code == 200:
            return res.json()
    except:
        return None
    return None

def check_gift_status(msisdn, token):
    url = f"https://apim.djezzy.dz/djezzy-api/api/v1/subscribers/{msisdn}/subscription-product/GIFTWALKWIN"
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Djezzy/2.6.7'
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        if 'meta' in data.get("data", {}):
            end_time = data['data']['meta'].get("end-date")
            if end_time:
                dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                now = datetime.utcnow()
                if dt > now:
                    remaining = dt - now
                    return {
                        'used': True,
                        'end_date': dt,
                        'remaining': remaining
                    }
    return {'used': False}

def activate_gift(msisdn, token):
    url = f"https://apim.djezzy.dz/djezzy-api/api/v1/subscribers/{msisdn}/subscription-product"
    payload = {
        "data": {
            "id": "GIFTWALKWIN",
            "type": "products",
            "meta": {
                "services": {
                    "steps": 10000,
                    "code": "GIFTWALKWIN2GO",
                    "id": "WALKWIN"
                }
            }
        }
    }
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Djezzy/2.6.7',
        'Content-Type': 'application/json'
    }
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        data = res.json()
        if "successfully" in data.get("message", ""):
            return True
    return False

def process_otp(msg, msisdn):
    chat_id = msg.chat.id
    otp = msg.text.strip()
    tokens = verify_otp(msisdn, otp)
    if tokens:
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

        status = check_gift_status(msisdn, access_token)

        users = load_users()
        users[str(chat_id)] = {
            'username': msg.from_user.username,
            'msisdn': msisdn,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'checked_at': datetime.now().isoformat()
        }
        save_users(users)

        if status['used']:
            days = status['remaining'].days
            hours, remainder = divmod(status['remaining'].seconds, 3600)
            minutes = remainder // 60
            used_time_str = status['end_date'].strftime('%H:%M %d-%m-%Y')
            bot.send_message(chat_id, f"⏳ لقد استخدمت الهدية مسبقًا!\n🕐 يمكنك المحاولة مجددًا بعد:\n{days} يوم، {hours} ساعة و {minutes} دقيقة\n📅 تاريخ انتهاء آخر هدية: {used_time_str}")
        else:
            if activate_gift(msisdn, access_token):
                bot.send_message(chat_id, f"🎉 تم تفعيل هدية 2Go بنجاح!\n📞 رقم: {hide_number(msisdn)}\n⏳ صالحة لمدة أسبوع")
            else:
                bot.send_message(chat_id, "⚠️ فشل في تفعيل الهدية. قد تكون مفعلة بالفعل.")
    else:
        bot.send_message(chat_id, "❌ OTP غير صحيح. حاول من جديد.")

print("✅ البوت يعمل الآن...")
bot.infinity_polling()
