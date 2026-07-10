import telebot
import tls_client
import time
import hashlib
from threading import Thread
from flask import Flask

# ==========================================
# CẤU HÌNH WEB SERVER ĐỂ LÁCH LUẬT RENDER FREE
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot Shopee Hệ Thống API TLS-Client đang hoạt động 24/7!"

def run_web_server():
    app.run(host='0.0.0.0', port=10000)

# ==========================================
# CẤU HÌNH BOT TELEGRAM
# ==========================================
BOT_TOKEN = "8643742163:AAHNQs25fNJkB1D6CFVBR8ryRYsrt0-sp-w"
bot = telebot.TeleBot(BOT_TOKEN)

# Danh sách mã voucher bạn muốn gom (Thay đổi tùy ý)
DANH_SACH_VOUCHER = ["HSJULBANMOISHOPEE", "BANMOISIEUHOIJUL", "B2B3A0709SHGD", "B2B3C0709SHGD", "B2B3A0713SHGD"]
current_proxy = None  

# Hàm băm mã hóa mật khẩu theo chuẩn API App Shopee (SHA256 -> Hex -> MD5)
def ma_hoa_mat_khau_shopee(password_raw):
    sha256_hash = hashlib.sha256(password_raw.encode('utf-8')).hexdigest()
    md5_hash = hashlib.md5(sha256_hash.encode('utf-8')).hexdigest()
    return md5_hash

# Lệnh thêm Proxy SOCKS5
@bot.message_handler(commands=['addprx'])
def handle_add_proxy(message):
    global current_proxy
    try:
        proxy_text = message.text.split(' ', 1)[1].strip()
        current_proxy = {"http": proxy_text, "https": proxy_text}
        bot.reply_to(message, f"✅ Đã cấu hình Proxy SOCKS5 thành công!\n🌐 `{proxy_text}`", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "❌ Cú pháp: `/addprx socks5://user:pass@ip:port`", parse_mode="Markdown")

# Lắng nghe tin nhắn dữ liệu tài khoản từ kho dữ liệu: tk|mk|spc_f
@bot.message_handler(func=lambda message: True)
def handle_shopee_login(message):
    global current_proxy
    data_text = message.text.strip()
    chat_id = message.chat.id
    
    if "|" in data_text and len(data_text.split("|")) == 3:
        tk, mk, spc_f = [item.strip() for item in data_text.split("|")]
        bot.send_message(chat_id, "⚙️ Đang mã hóa mật khẩu & giả lập vân tay trình duyệt (TLS)...")
        tien_trinh_shopee(tk, mk, spc_f, chat_id, current_proxy)
    else:
        bot.send_message(chat_id, "⚠️ Định dạng không hợp lệ!\nHãy nhập đúng: `tài_khoản | mật_khẩu | spc_f`", parse_mode="Markdown")

# Hàm xử lý Đăng nhập qua API giả lập sâu bằng tls_client
def tien_trinh_shopee(username, password_raw, spc_f, chat_id, proxy_config):
    # Khởi tạo Session đặc biệt giả lập cấu trúc mã hóa bảo mật của Chrome Mobile
    session = tls_client.Session(
        client_identifier="chrome_112", 
        random_tls_extensions_order=True
    )
    
    # Cấu hình proxy nếu có
    if proxy_config: 
        session.proxies = {
            "http": proxy_config["http"],
            "https": proxy_config["https"]
        }
    
    # Gài mã định danh thiết bị vào Cookie nền tảng
    session.cookies.set("spc_f", spc_f, domain=".shopee.vn")
    
    # Gọi hàm mã hóa mật khẩu thô
    password_encrypted = ma_hoa_mat_khau_shopee(password_raw)
    
    login_url = "https://shopee.vn/api/v4/account/login_by_password"
    
    # Định hình tập hợp Headers giả lập môi trường người dùng thật trên Android
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/json", 
        "X-Shopee-Http-Client-Type": "4", 
        "X-Requested-With": "com.shopee.vn",
        "Referer": "https://shopee.vn/",
        "Accept": "application/json"
    }
    
    payload = {
        "username": username,
        "password_encryption": password_encrypted,
        "support_iv": True,
        "client_id": spc_f,
        "ext_info": {
            "device_id": spc_f,
            "is_root": False
        }
    }
    
    try:
        if proxy_config:
            # Kiểm tra IP Proxy thông qua một dịch vụ check IP độc lập
            ip_check = session.get("https://api.ipify.org?format=json", timeout_seconds=5).json()
            bot.send_message(chat_id, f"🌐 Kết nối thông qua IP Proxy: {ip_check.get('ip')}")

        # Gửi gói tin đăng nhập bằng cấu trúc TLS bypass màng lọc
        response = session.post(login_url, json=payload, headers=headers, timeout_seconds=10)
        res_data = response.json()
        
        if response.status_code == 200 and "error" not in res_data:
            bot.send_message(chat_id, f"🔓 Tài khoản [{username}] đăng nhập thành công! Bắt đầu nhập mã voucher...")
            # Chuyển tiếp Session đã được cấp token phiên sang hàm lưu voucher
            xu_ly_claim_voucher_api(session, chat_id)
        elif "error" in res_data and res_data.get("error") == "login_need_otp":
            bot.send_message(chat_id, f"❌ Tài khoản [{username}] bị chặn: Shopee bắt xác thực OTP.\n💡 Lý do: Do IP Proxy này bị dính blacklist hoặc dải mạng đang quét spam nặng.")
        else:
            reason = res_data.get("msg", "Sai tài khoản/mật khẩu hoặc lỗi mã hóa phần cứng.")
            bot.send_message(chat_id, f"❌ Lỗi phản hồi: {reason}")
            
    except Exception as e:
        bot.send_message(chat_id, f"💥 Lỗi luồng kết nối đăng nhập: {str(e)}")

# Hàm gọi API nhập mã lưu Voucher (Cũng chạy trên nền tảng tls_client)
def xu_ly_claim_voucher_api(session, chat_id):
    claim_url = "https://shopee.vn/api/v2/voucher_wallet/claim_vouchercode"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/json",
        "X-Shopee-Http-Client-Type": "4"
    }
    
    for code in DANH_SACH_VOUCHER:
        payload = {
            "voucher_code": code,
            "need_user_voucher_status": True
        }
        try:
            res = session.post(claim_url, json=payload, headers=headers, timeout_seconds=5)
            res_json = res.json()
            error_code = res_json.get("error", -1)
            
            if error_code == 0:
                bot.send_message(chat_id, f"✅ Đã lưu thành công: *{code}*", parse_mode="Markdown")
            elif error_code == 2:
                bot.send_message(chat_id, f"🔁 Mã *{code}* đã sở hữu từ trước.", parse_mode="Markdown")
            else:
                msg = res_json.get("error_msg", "Hết lượt hoặc không hợp lệ.")
                bot.send_message(chat_id, f"❌ Mã *{code}* thất bại: {msg}", parse_mode="Markdown")
                
            time.sleep(1.2) # Giãn cách tiêu chuẩn để tránh thuật toán khóa spam API
            
        except Exception:
            bot.send_message(chat_id, f"⚠️ Lỗi kết nối khi nhập mã: {code}")
            
    bot.send_message(chat_id, "🎉 Quá trình xử lý ví tài khoản hoàn tất!")

# ==========================================
# KHỞI CHẠY HỆ THỐNG SONG SONG
# ==========================================
if __name__ == "__main__":
    # Luồng chạy Web Server lách luật Render Free
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Luồng chạy Bot Telegram
    print("Bot API TLS-Client đang trực chiến...")
    bot.infinity_polling()
