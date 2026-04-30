import streamlit as st
import paho.mqtt.client as mqtt
import json
import requests
import pandas as pd
import os
import time      
import random    
from datetime import datetime, time as dt_time, timedelta

# --- CẤU HÌNH TELEGRAM ---
TELEGRAM_TOKEN = "8752315179:AAEMeMcS9FizpK6zEIpw_DWJ7rCznlB0MMY"
CHAT_ID = "6296506766"

# --- TỪ ĐIỂN CẤU HÌNH TAG & NGƯỠNG CẢNH BÁO ---
CAU_HINH_TAG = {
    "BoardIO:AI_0": {"ten": "Bụi mịn", "nguong": 4.3},
    "BoardIO:AI_1": {"ten": "Tiếng ồn", "nguong": 4.0},
    "BoardIO:AI_2": {"ten": "Khí CO", "nguong": 3.0}
}

# --- CẤU HÌNH HIVEMQ CLOUD ---
MQTT_BROKER = "089b478fa58e49308b8038acdce36015.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "huynh"
MQTT_PASS = "Adam3600"
MQTT_TOPIC = "data/R"

DATA_FILE = "data_log.csv"

# Khởi tạo file CSV nếu chưa có
if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=["ThoiGian", "Tag", "GiaTri"])
    df_init.to_csv(DATA_FILE, index=False)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        pass 

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đã kết nối MQTT thành công!")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        
        if "d" in data:
            for item in data["d"]:
                tag_name = item["tag"]
                
                # Tra cứu tag trong từ điển
                if tag_name in CAU_HINH_TAG: 
                    gia_tri = float(item["value"])
                    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 1. Lưu dữ liệu mới vào file CSV
                    new_data = pd.DataFrame({"ThoiGian": [thoi_gian], "Tag": [tag_name], "GiaTri": [gia_tri]})
                    new_data.to_csv(DATA_FILE, mode='a', header=False, index=False)
                    
                    # 2. Xử lý logic cảnh báo với tin nhắn đã được tùy chỉnh
                    ten_chi_so = CAU_HINH_TAG[tag_name]["ten"]
                    nguong_cho_phep = CAU_HINH_TAG[tag_name]["nguong"]
                    
                    if gia_tri > nguong_cho_phep:
                        # TIN NHẮN ĐÃ ĐƯỢC LÀM SẠCH VÀ CHUYỂN HOÀN TOÀN SANG TIẾNG VIỆT
                        canh_bao = f"🚨 <b>BÁO ĐỘNG NHÀ GA CẦU GIẤY!</b>\n⚠️ Cảnh báo: <b>{ten_chi_so}</b>\n📈 Mức hiện tại: <b>{gia_tri}</b> (Ngưỡng an toàn: {nguong_cho_phep})"
                        send_telegram_message(canh_bao)
    except Exception as e:
        pass

# --- THIẾT LẬP MQTT CHẠY NGẦM ---
@st.cache_resource
def start_mqtt():
    client_id = f"Web_CauGiay_{random.randint(1000, 9999)}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set() 
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start() 
    return client

mqtt_client = start_mqtt()

# ==========================================
# --- GIAO DIỆN WEB (STREAMLIT) ---
# ==========================================

st.set_page_config(page_title="Quan Trắc Nhà Ga Cầu Giấy", layout="wide")

st.title("🚉 Hệ thống quan trắc nhà ga Cầu Giấy")
st.markdown("---")

auto_refresh = st.checkbox("🔄 Tự động cập nhật (Real-time)", value=True)

# Đọc dữ liệu từ file CSV
try:
    df = pd.read_csv(DATA_FILE)
    if not df.empty:
        st.subheader("📊 Bảng dữ liệu thông số")
        st.dataframe(df.sort_values(by="ThoiGian", ascending=False).head(10), width="stretch")
        
        st.markdown("---")
        st.write("**📥 CHỌN KHOẢNG THỜI GIAN ĐỂ TẢI DỮ LIỆU:**")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            d_start = st.date_input("Từ ngày", datetime.now() - timedelta(days=1))
            t_start = st.time_input("Từ giờ", dt_time(0, 0, 0))
            
        with col2:
            d_end = st.date_input("Đến ngày", datetime.now())
            t_end = st.time_input("Đến giờ", dt_time(23, 59, 59))
            
        dt_start = datetime.combine(d_start, t_start)
        dt_end = datetime.combine(d_end, t_end)
        
        df['ThoiGian_dt'] = pd.to_datetime(df['ThoiGian'])
        df_filtered = df[(df['ThoiGian_dt'] >= dt_start) & (df['ThoiGian_dt'] <= dt_end)]
        df_clean = df_filtered.drop(columns=['ThoiGian_dt']) 
        
        with col3:
            st.markdown("<br><br>", unsafe_allow_html=True) 
            csv_data = df_clean.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label=f"📥 Tải dữ liệu ({len(df_clean)} dòng)",
                data=csv_data,
                file_name=f"Data_CauGiay_{d_start}_to_{d_end}.csv",
                mime="text/csv",
            )
    else:
        st.info("Hệ thống đang chờ nhận dữ liệu từ thiết bị ADAM...")
except Exception as e:
    st.error("Chưa có file dữ liệu hoặc lỗi đọc file.")

# ==========================================
# --- VÒNG LẶP THỜI GIAN THỰC ---
# ==========================================
if auto_refresh:
    time.sleep(2)  
    st.rerun()