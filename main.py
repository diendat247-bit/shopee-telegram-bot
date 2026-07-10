import telebot
import requests
import time

# ==========================================
# CẤU HÌNH BAN ĐẦU
# ==========================================
BOT_TOKEN = "8643742163:AAHNQs25fNJkB1D6CFVBR8ryRYsrt0-sp-w"
bot = telebot.TeleBot(BOT_TOKEN)

DANH_SACH_VOUCHER = ["B2B3A0713SHGD", "B2B3C0709SHGD", "B2B3A0709SHGD", "BANMOISIEUHOIJUL", "HSJULBANMOISHOPEE"]

# Biến lưu cấu hình Proxy toàn cục
current_proxy = None  

# ==========================================
# XỬ LÝ LỆNH TELEGRAM
# ==========================================

# Lệnh thêm Proxy SOCKS5: /addprx socks5://user:pass@ip:port hoặc socks5://ip:port
@bot.message_handler(commands=['addprx'])
def handle_add_proxy(message):
    global current_proxy
    try:
        proxy_text = message.text.split(' ', 1)[1].strip()
        
        # Đồng bộ hóa cả http và https về giao thức socks5
        current_proxy = {
            "http": proxy_text,
            "https": proxy_text
        }
        bot.reply_to(message, f"✅ Đã cấu hình Proxy SOCKS5 thành công!\n🌐 `{proxy_text}`", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "❌ Vui lòng nhập đúng cú pháp SOCKS5:\n`/addprx socks5://username:password@ip:port` hoặc `/addprx socks5://ip:port`", parse_mode="Markdown")

# Lắng nghe tin nhắn gửi dữ liệu tài khoản: tk|mk|spc_f
@bot.message_handler(func=lambda message: True)
def handle_shopee_login(message):
    global current_proxy
    data_text = message.text.strip()
    chat_id = message.chat.id
    
    if "|" in data_text and len(data_text.split("|")) == 3:
        tk, mk, spc_f = [item.strip() for item in data_text.split("|")]
        bot.send_message(chat_id, "⚙️ Đang xử lý đăng nhập qua API bằng mã thiết bị và SOCKS5...")
        tien_trinh_shopee(tk, mk, spc_f, chat_id, current_proxy)
    else:
        bot.send_message(chat_id, "⚠️ Định dạng không hợp lệ!\nNhập dữ liệu theo cấu trúc:\n`tài_khoản | mật_khẩu | spc_f`", parse_mode="Markdown")

# ==========================================
# CORE XỬ LÝ API SHOPEE
# ==========================================
def tien_trinh_shopee(username, password, spc_f, chat_id, proxy_config):
    session = requests.Session()
    
    # Nạp cấu hình SOCKS5 vào Session nếu có
    if proxy_config:
        session.proxies.update(proxy_config)
    
    session.cookies.set("spc_f", spc_f, domain=".shopee.vn")
    
    login_url = "https://shopee.vn/api/v4/account/login_by_password"
    headers = {
        "User-Agent": "Android Shopee/Version 2.90.11", 
        "Content-Type": "application/json",
        "X-Shopee-Http-Client-Type": "4", 
        "Referer": "https://shopee.vn/",
    }
    
    payload = {
        "username": username,
        "password": password, 
        "support_iv": True,
        "client_id": spc_f
    }
    
    try:
        # Kiểm tra IP hiện tại qua SOCKS5 trước khi gọi Shopee để đảm bảo Proxy hoạt động
        if proxy_config:
            ip_check = session.get("https://api.ipify.org?format=json", timeout=5).json()
            bot.send_message(chat_id, f"🌐 Đang chạy qua IP Proxy: {ip_check.get('ip')}")

        response = session.post(login_url, json=payload, headers=headers, timeout=10)
        res_data = response.json()
        
        if response.status_code == 200 and "error" not in res_data:
            bot.send_message(chat_id, "🔓 Đăng nhập thành công! Đang tiến hành gom voucher...")
            xu_ly_claim_voucher_api(session, chat_id)
        elif "error" in res_data and res_data.get("error") == "login_need_otp":
            bot.send_message(chat_id, "❌ Thất bại: Shopee đòi OTP. Lý do: SOCKS5 bị đưa vào danh sách đen (Blacklist) hoặc `spc_f` không trùng khớp.")
        else:
            reason = res_data.get("msg", "Tài khoản hoặc mật khẩu không chính xác.")
            bot.send_message(chat_id, f"❌ Đăng nhập lỗi: {reason}")
            
    except Exception as e:
        bot.send_message(chat_id, f"💥 Lỗi kết nối (Vui lòng kiểm tra lại trạng thái Proxy SOCKS5): {str(e)}")

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
            
            if error_code == 0:
                bot.send_message(chat_id, f"✅ Đã lưu thành công: *{code}*", parse_mode="Markdown")
            elif error_code == 2:
                bot.send_message(chat_id, f"🔁 Mã *{code}* đã sở hữu từ trước.", parse_mode="Markdown")
            else:
                msg = res_json.get("error_msg", "Hết lượt hoặc không hợp lệ.")
                bot.send_message(chat_id, f"❌ Mã *{code}* thất bại: {msg}", parse_mode="Markdown")
                
            time.sleep(1.2) # Giãn cách an toàn cho SOCKS5 tránh bị nghẽn dòng dữ liệu
            
        except Exception:
            bot.send_message(chat_id, f"⚠️ Lỗi kết nối khi gửi mã: {code}")

if __name__ == "__main__":
    print("Bot API SOCKS5 đang trực chiến...")
    bot.infinity_polling()
