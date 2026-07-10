import telebot
import requests
import time
from threading import Thread
from flask import Flask

# ==========================================
# CẤU HÌNH WEB SERVER ĐỂ LÁCH LUẬT RENDER FREE
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot Shopee đang hoạt động ổn định 24/7!"

def run_web_server():
    # Render yêu cầu chạy ở port 10000 hoặc port do hệ thống cấp
    app.run(host='0.0.0.0', port=10000)

# ==========================================
# CẤU HÌNH BOT TELEGRAM
# ==========================================
BOT_TOKEN = "8643742163:AAHNQs25fNJkB1D6CFVBR8ryRYsrt0-sp-w"
bot = telebot.TeleBot(BOT_TOKEN)

# Danh sách mã voucher bạn muốn gom (Thay đổi tùy ý)
DANH_SACH_VOUCHER = ["HSJULBANMOISHOPEE", "BANMOISIEUHOIJUL", "B2B3A0709SHGD", "B2B3C0709SHGD", "B2B3A0713SHGD"]
current_proxy = None  

# Lệnh thêm Proxy SOCKS5
@bot.message_handler(commands=['addprx'])
def handle_add_proxy(message):
    global current_proxy
    try:
        proxy_text = message.text.split(' ', 1)[1].strip()
        current_proxy = {"http": proxy_text, "https": proxy_text}
        bot.reply_to(message, f"✅ Đã cấu hình Proxy SOCKS5 thành công!\n🌐 `{proxy_text}`", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "❌ Cú pháp: `/addprx socks5://ip:port`", parse_mode="Markdown")

# Lắng nghe tin nhắn gửi dữ liệu tài khoản: tk|mk|spc_f
@bot.message_handler(func=lambda message: True)
def handle_shopee_login(message):
    global current_proxy
    data_text = message.text.strip()
    chat_id = message.chat.id
    
    if "|" in data_text and len(data_text.split("|")) == 3:
        tk, mk, spc_f = [item.strip() for item in data_text.split("|")]
        bot.send_message(chat_id, "⚙️ Đang xử lý đăng nhập qua API...")
        tien_trinh_shopee(tk, mk, spc_f, chat_id, current_proxy)
    else:
        bot.send_message(chat_id, "⚠️ Định dạng không hợp lệ!\nNhập: `tài_khoản | mật_khẩu | spc_f`", parse_mode="Markdown")

# Hàm xử lý Đăng nhập qua API
def tien_trinh_shopee(username, password, spc_f, chat_id, proxy_config):
    session = requests.Session()
    if proxy_config: 
        session.proxies.update(proxy_config)
    session.cookies.set("spc_f", spc_f, domain=".shopee.vn")
    
    login_url = "https://shopee.vn/api/v4/account/login_by_password"
    headers = {
        "User-Agent": "Android Shopee/Version 2.90.11", 
        "Content-Type": "application/json", 
        "X-Shopee-Http-Client-Type": "4",
        "Referer": "https://shopee.vn/"
    }
    payload = {"username": username, "password": password, "support_iv": True, "client_id": spc_f}
    
    try:
        # Kiểm tra IP Proxy trước khi gọi Shopee
        if proxy_config:
            ip_check = session.get("https://api.ipify.org?format=json", timeout=5).json()
            bot.send_message(chat_id, f"🌐 Đang chạy qua IP Proxy: {ip_check.get('ip')}")

        response = session.post(login_url, json=payload, headers=headers, timeout=10)
        res_data = response.json()
        
        if response.status_code == 200 and "error" not in res_data:
            bot.send_message(chat_id, "🔓 Đăng nhập thành công! Đang tiến hành gom voucher...")
            # Chuyển sang hàm lưu voucher chi tiết
            xu_ly_claim_voucher_api(session, chat_id)
        elif "error" in res_data and res_data.get("error") == "login_need_otp":
            bot.send_message(chat_id, "❌ Thất bại: Shopee đòi OTP (Proxy lỏ hoặc spc_f hết hạn).")
        else:
            reason = res_data.get("msg", "Tài khoản hoặc mật khẩu không chính xác.")
            bot.send_message(chat_id, f"❌ Đăng nhập lỗi: {reason}")
    except Exception as e:
        bot.send_message(chat_id, f"💥 Lỗi kết nối: {str(e)}")

# Hàm lưu Voucher và Báo cáo Chi tiết về Telegram
def xu_ly_claim_voucher_api(session, chat_id):
    claim_url = "https://shopee.vn/api/v2/voucher_wallet/claim_vouchercode"
    headers = {
        "User-Agent": "Android Shopee/Version 2.90.11",
        "Content-Type": "application/json",
        "X-Shopee-Http-Client-Type": "4"
    }
    
    for code in DANH_SACH_VOUCHER:
        payload = {
            "voucher_code": code,
            "need_user_voucher_status": True
        }
        try:
            res = session.post(claim_url, json=payload, headers=headers, timeout=5)
            res_json = res.json()
            error_code = res_json.get("error", -1)
            
            # Phân tích kết quả từ API Shopee trả về
            if error_code == 0:
                bot.send_message(chat_id, f"✅ Đã lưu thành công: *{code}*", parse_mode="Markdown")
            elif error_code == 2:
                bot.send_message(chat_id, f"🔁 Mã *{code}* đã sở hữu từ trước.", parse_mode="Markdown")
            else:
                msg = res_json.get("error_msg", "Hết lượt hoặc không hợp lệ.")
                bot.send_message(chat_id, f"❌ Mã *{code}* thất bại: {msg}", parse_mode="Markdown")
                
            time.sleep(1.2) # Giãn cách để tránh bị Shopee chặn spam
            
        except Exception:
            bot.send_message(chat_id, f"⚠️ Lỗi kết nối khi gửi mã: {code}")
            
    bot.send_message(chat_id, "🎉 Đã quét xong toàn bộ danh sách voucher!")

# ==========================================
# KHỞI CHẠY SONG SONG CẢ WEB VÀ BOT
# ==========================================
if __name__ == "__main__":
    # 1. Khởi động Web Server ở luồng riêng để Render kiểm tra
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 2. Khởi động Bot Telegram
    print("Bot API SOCKS5 đang trực chiến trên Web Service...")
    bot.infinity_polling()
