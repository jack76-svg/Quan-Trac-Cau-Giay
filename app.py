import streamlit as st
import paho.mqtt.client as mqtt
import json
import requests
import pandas as pd
import os
import time      
import random  
import math  
from datetime import datetime, time as dt_time, timedelta, timezone
import plotly.graph_objects as go
import plotly.express as px

# --- CẤU HÌNH TELEGRAM ---
TELEGRAM_TOKEN = "8752315179:AAEMeMcS9FizpK6zEIpw_DWJ7rCznlB0MMY"
CHAT_ID = "6296506766"

# --- TỪ ĐIỂN CẤU HÌNH TAG & CÁC CẤP ĐỘ CẢNH BÁO ---
CAU_HINH_TAG = {
    "BoardIO:AI_0": {
        "ten": "Bụi mịn",
        "don_vi": "AQI", 
        "cap_do": [
            {"nguong": 200, "muc": "Rất có hại (200-300)", "icon": "🆘", "bao_dong": True, "mau": "#9b59b6", "size": 100}, 
            {"nguong": 150, "muc": "Có hại (151-200)", "icon": "🔴", "bao_dong": True, "mau": "#e74c3c", "size": 50},  
            {"nguong": 100, "muc": "Kém (101-150)", "icon": "🟠", "bao_dong": True, "mau": "#e67e22", "size": 50},  
            {"nguong": 50,  "muc": "Trung bình (51-100)", "icon": "🟡", "bao_dong": True, "mau": "#f1c40f", "size": 50},  
            {"nguong": 0,   "muc": "Tốt (0-50)", "icon": "🟢", "bao_dong": False, "mau": "#2ecc71", "size": 50}   
        ]
    },
    "BoardIO:AI_1": {
        "ten": "Tiếng ồn",
        "don_vi": "dB",
        "cap_do": [
            {"nguong": 90, "muc": "Suy giảm thính lực (>90)", "icon": "🆘", "bao_dong": True, "mau": "#9b59b6", "size": 30}, 
            {"nguong": 80, "muc": "Nguy hiểm (80-90)", "icon": "🔴", "bao_dong": True, "mau": "#e74c3c", "size": 10}, 
            {"nguong": 70, "muc": "Khó chịu (70-80)", "icon": "🟠", "bao_dong": True, "mau": "#e67e22", "size": 10}, 
            {"nguong": 0,  "muc": "An toàn (<70)", "icon": "🟢", "bao_dong": False, "mau": "#2ecc71", "size": 70}  
        ]
    },
    "BoardIO:AI_2": {
        "ten": "Khí CO",
        "don_vi": "ppm",
        "cap_do": [
            {"nguong": 800, "muc": "Nguy hiểm tính mạng (>800)", "icon": "🆘", "bao_dong": True, "mau": "#9b59b6", "size": 200}, 
            {"nguong": 400, "muc": "Nguy hiểm (400-800)", "icon": "🔴", "bao_dong": True, "mau": "#e74c3c", "size": 400}, 
            {"nguong": 100, "muc": "Bắt đầu ngộ độc (100-400)", "icon": "🟠", "bao_dong": True, "mau": "#e67e22", "size": 300}, 
            {"nguong": 50,  "muc": "Mức cảnh giác (50-100)", "icon": "🟡", "bao_dong": True, "mau": "#f1c40f", "size": 50},  
            {"nguong": 0,   "muc": "An toàn (0-50)", "icon": "🟢", "bao_dong": False, "mau": "#2ecc71", "size": 50}   
        ]
    }
}

# --- CẤU HÌNH HIVEMQ CLOUD ---
MQTT_BROKER = "089b478fa58e49308b8038acdce36015.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "huynh"
MQTT_PASS = "Adam3600"
MQTT_TOPIC = "data/R"

DATA_FILE = "data_log.csv"

if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=["ThoiGian", "Tag", "GiaTri"])
    df_init.to_csv(DATA_FILE, index=False)

def get_vietnam_time():
    return datetime.now(timezone(timedelta(hours=7)))

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        pass 

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[{get_vietnam_time().strftime('%H:%M:%S')}] Đã kết nối MQTT thành công!")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        
        if "d" in data:
            for item in data["d"]:
                tag_name = item["tag"]
                
                if tag_name in CAU_HINH_TAG: 
                    gia_tri = float(item["value"])
                    thoi_gian = get_vietnam_time().strftime("%Y-%m-%d %H:%M:%S")
                    
                    new_data = pd.DataFrame({"ThoiGian": [thoi_gian], "Tag": [tag_name], "GiaTri": [gia_tri]})
                    new_data.to_csv(DATA_FILE, mode='a', header=False, index=False)
                    
                    ten_chi_so = CAU_HINH_TAG[tag_name]["ten"]
                    
                    for cap in CAU_HINH_TAG[tag_name]["cap_do"]:
                        if gia_tri >= cap["nguong"]:
                            if cap["bao_dong"]:
                                canh_bao = (
                                    f"{cap['icon']} <b>BÁO ĐỘNG NHÀ GA CẦU GIẤY!</b>\n"
                                    f"⚠️ Thông số: <b>{ten_chi_so}</b>\n"
                                    f"📈 Mức đo được: <b>{gia_tri}</b>\n"
                                    f"🛑 Đánh giá: <b>{cap['muc']}</b>"
                                )
                                send_telegram_message(canh_bao)
                            break 
    except Exception as e:
        pass

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

try:
    df = pd.read_csv(DATA_FILE)
    if not df.empty:
        latest_data = {}
        latest_df = df.sort_values('ThoiGian').groupby('Tag').tail(1)
        for _, row in latest_df.iterrows():
            latest_data[row['Tag']] = row['GiaTri']

        def draw_donut(value, title, unit, cap_do_list):
            reversed_cap = cap_do_list[::-1] 
            labels = [c["muc"] for c in reversed_cap]
            values = [c["size"] for c in reversed_cap]
            colors = [c["mau"] for c in reversed_cap]
            
            fig = go.Figure()
            
            # 1. VÒNG TRÒN DẢI MÀU (Lớp dưới)
            fig.add_trace(go.Pie(
                labels=labels, 
                values=values, 
                hole=0.55, 
                marker_colors=colors,
                textinfo='none', 
                hoverinfo='label',
                sort=False, 
                direction='clockwise',
                rotation=0,
                domain=dict(x=[0, 1], y=[0, 1]) # Ép chặt khung hình
            ))
            
            # 2. CÂY KIM (Lớp trên: Thực chất là một lát cắt cực mỏng của Pie thứ 2)
            total_range = sum(values)
            v_clamped = min(max(value, 0), total_range)
            needle_size = total_range * 0.008 # Độ mỏng của kim = 0.8% tổng dải
            
            val_before = v_clamped - needle_size / 2
            val_after = total_range - v_clamped - needle_size / 2
            
            # Xử lý ngoại lệ nếu kim nằm kịch ở vạch số 0 hoặc vạch cuối cùng
            if val_before < 0:
                val_after += val_before
                val_before = 0
            elif val_after < 0:
                val_before += val_after
                val_after = 0
                
            fig.add_trace(go.Pie(
                labels=['', f'Giá trị hiện tại: {value}', ''],
                values=[val_before, needle_size, val_after],
                hole=0.45, # Kim đâm từ sát chữ số ra tận mép ngoài vòng tròn
                marker_colors=['rgba(0,0,0,0)', '#2c3e50', 'rgba(0,0,0,0)'], # Chỉ hiện mỗi màu của lát cắt kim
                textinfo='none',
                hoverinfo='label',
                sort=False,
                direction='clockwise',
                rotation=0,
                domain=dict(x=[0, 1], y=[0, 1]) # Ép chặt vào cùng khung với vòng Donut
            ))
            
            # 3. TEXT CHỮ SỐ Ở GIỮA
            fig.update_layout(
                showlegend=False,
                margin=dict(l=20, r=20, t=50, b=20),
                height=350, 
                title={'text': title, 'x': 0.5, 'xanchor': 'center', 'font': {'size': 24, 'color': '#333'}},
                annotations=[dict(
                    text=f"<b style='font-size:55px; color:#333;'>{value}</b><br><span style='font-size:22px; color:#666;'>{unit}</span>", 
                    x=0.5, y=0.5, 
                    showarrow=False
                )]
            )
            return fig

        def draw_legend(cap_do_list):
            html = "<div style='font-size: 22px; margin-top: 15px; padding-left: 20px;'>" 
            for c in cap_do_list: 
                html += f"<div style='display: flex; align-items: center; margin-bottom: 12px;'>"
                html += f"<div style='width: 45px; height: 22px; background-color: {c['mau']}; margin-right: 15px; border-radius: 4px;'></div>"
                html += f"<span style='color: #444; font-weight: 600;'>{c['muc']}</span>"
                html += f"</div>"
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        
        with col1:
            val_bui = latest_data.get("BoardIO:AI_0", 0)
            tag_data = CAU_HINH_TAG["BoardIO:AI_0"]
            st.plotly_chart(draw_donut(val_bui, tag_data["ten"].upper(), tag_data["don_vi"], tag_data["cap_do"]), use_container_width=True)
            draw_legend(tag_data["cap_do"])

        with col2:
            val_on = latest_data.get("BoardIO:AI_1", 0)
            tag_data = CAU_HINH_TAG["BoardIO:AI_1"]
            st.plotly_chart(draw_donut(val_on, tag_data["ten"].upper(), tag_data["don_vi"], tag_data["cap_do"]), use_container_width=True)
            draw_legend(tag_data["cap_do"])

        with col3:
            val_co = latest_data.get("BoardIO:AI_2", 0)
            tag_data = CAU_HINH_TAG["BoardIO:AI_2"]
            st.plotly_chart(draw_donut(val_co, tag_data["ten"].upper(), tag_data["don_vi"], tag_data["cap_do"]), use_container_width=True)
            draw_legend(tag_data["cap_do"])

        st.markdown("---")

        st.subheader("📈 Biểu đồ biến thiên thời gian thực")
        df_chart = df.tail(60) 
        fig_line = px.line(df_chart, x="ThoiGian", y="GiaTri", color="Tag", markers=True)
        
        newnames = {'BoardIO:AI_0':'Bụi mịn', 'BoardIO:AI_1': 'Tiếng ồn', 'BoardIO:AI_2': 'Khí CO'}
        fig_line.for_each_trace(lambda t: t.update(name = newnames[t.name],
                                                legendgroup = newnames[t.name],
                                                hovertemplate = t.hovertemplate.replace(t.name, newnames[t.name])))
        
        fig_line.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0), xaxis_title="Thời gian", yaxis_title="Giá trị đo")
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")

        st.subheader("📊 Dữ liệu Log ")
        df_display = df.sort_values(by=["ThoiGian", "Tag"], ascending=[False, False]).head(3)
        st.dataframe(df_display, width="stretch")
        
        # --- PHẦN TRA CỨU LỊCH SỬ VÀ TẢI DỮ LIỆU ---
        st.write("**🕰️ TRA CỨU LỊCH SỬ VÀ TẢI DỮ LIỆU:**")
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        now_vn = get_vietnam_time() 
        
        with col_f1:
            d_start = st.date_input("Từ ngày", now_vn - timedelta(days=1))
            t_start = st.time_input("Từ giờ", dt_time(0, 0, 0))
            
        with col_f2:
            d_end = st.date_input("Đến ngày", now_vn)
            t_end = st.time_input("Đến giờ", dt_time(23, 59, 59))
            
        dt_start = datetime.combine(d_start, t_start)
        dt_end = datetime.combine(d_end, t_end)
        
        # Lọc dữ liệu theo thời gian
        df['ThoiGian_dt'] = pd.to_datetime(df['ThoiGian'])
        df_filtered = df[(df['ThoiGian_dt'] >= dt_start) & (df['ThoiGian_dt'] <= dt_end)]
        df_clean = df_filtered.drop(columns=['ThoiGian_dt']) 
        
        # 1. VẼ BIỂU ĐỒ LỊCH SỬ DỰA TRÊN THỜI GIAN ĐÃ LỌC
        if not df_filtered.empty:
            st.markdown(f"**📉 Biểu đồ dữ liệu từ `{dt_start}` đến `{dt_end}`**")
            fig_hist = px.line(df_filtered, x="ThoiGian", y="GiaTri", color="Tag", markers=True)
            
            fig_hist.for_each_trace(lambda t: t.update(name = newnames.get(t.name, t.name),
                                                    legendgroup = newnames.get(t.name, t.name),
                                                    hovertemplate = t.hovertemplate.replace(t.name, newnames.get(t.name, t.name))))
            fig_hist.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Thời gian", yaxis_title="Giá trị đo")
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.warning("Không có dữ liệu trong khoảng thời gian bạn chọn!")

        # 2. NÚT TẢI FILE CSV
        with col_f3:
            st.markdown("<br><br>", unsafe_allow_html=True) 
            if not df_clean.empty:
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
    st.error(f"Chưa có file dữ liệu hoặc lỗi: {e}")

if auto_refresh:
    time.sleep(2)  
    st.rerun()