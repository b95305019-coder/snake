import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import cv2
import difflib
import pandas as pd
import json
import os
from streamlit_cropper import st_cropper

# 資料持久化路徑
DATA_FILE = "challenges_data.json"

# --- 0. 資料持久化函式 ---
def load_data():
    """從本地 JSON 讀取字詞清單，若無則回傳預設值"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    # 初始預設值
    return [
        {"word": "森林", "animal": "🦊"},
        {"word": "大象", "animal": "🐘"},
        {"word": "太陽", "animal": "☀️"}
    ]

def save_data(data):
    """將字詞清單寫入本地 JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 1. 初始化與資源載入 (優化辨識速度) ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['ch_tra', 'en'], gpu=False)

reader = load_ocr()

# --- 2. 核心邏輯函式 ---
def advanced_preprocess(pil_image):
    max_size = 1000
    w, h = pil_image.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        pil_image = pil_image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    img = np.array(pil_image.convert('RGB'))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    processed = clahe.apply(gray)
    return processed

def smart_check(target, detected):
    if not detected: return False
    detected = detected.replace(" ", "").replace("\n", "")
    if target in detected: return True
    count = sum(1 for char in target if char in detected)
    if count >= len(target): return True
    if difflib.SequenceMatcher(None, target, detected).ratio() >= 0.5: return True
    return False

# --- 3. Session State 初始化 ---
if 'challenges' not in st.session_state:
    st.session_state.challenges = load_data()

if 'idx' not in st.session_state:
    st.session_state.idx = 0
    st.session_state.collection = []
    st.session_state.uploader_key = 0
    st.session_state.success_mode = False
    st.session_state.need_crop = False 

# --- 4. 側邊欄：字詞庫管理功能 ---
with st.sidebar:
    st.title("⚙️ 管理後台")
    mode = st.radio("切換模式", ["🎯 學生挑戰", "📚 字詞管理"])
    
    if mode == "📚 字詞管理":
        st.subheader("新增單筆字詞")
        new_word = st.text_input("輸入生字")
        
        # 優化：Emoji 選項清單
        emoji_options = [
            "🦊 狐狸", "🐘 大象", "☀️ 太陽", "🦋 蝴蝶", "🍉 西瓜", 
            "🐰 兔子", "🦁 獅子", "🐼 貓熊", "🍎 蘋果", "🌈 彩虹", 
            "⭐ 星星", "🔥 火火", "🌳 樹木", "🐬 海豚", "🍦 冰淇淋",
            "🎨 自定義..."
        ]
        selected_emoji_raw = st.selectbox("選取代表 Emoji", emoji_options)
        
        # 處理自定義邏輯
        if "自定義" in selected_emoji_raw:
            final_emoji = st.text_input("請輸入自定義 Emoji (單個圖示)", value="⭐")
        else:
            # 取得字串開頭的 Emoji (例如從 "🦊 狐狸" 擷取 "🦊")
            final_emoji = selected_emoji_raw.split(" ")[0]

        if st.button("➕ 加入清單"):
            if new_word:
                st.session_state.challenges.append({"word": new_word, "animal": final_emoji})
                save_data(st.session_state.challenges) # 儲存至檔案
                st.success(f"已新增：{new_word} ({final_emoji})")
                st.rerun()

        st.divider()
        st.subheader("CSV 大量匯入")
        st.caption("格式：第一欄為字詞，第二欄為 Emoji")
        uploaded_csv = st.file_uploader("選擇 CSV 檔案", type=['csv'])
        if uploaded_csv:
            try:
                df = pd.read_csv(uploaded_csv, header=None)
                new_items = []
                for _, row in df.iterrows():
                    new_items.append({"word": str(row[0]), "animal": str(row[1]) if len(row) > 1 else "⭐"})
                
                if st.button("📥 確認匯入內容"):
                    st.session_state.challenges.extend(new_items)
                    save_data(st.session_state.challenges) # 儲存至檔案
                    st.success(f"成功匯入 {len(new_items)} 筆字詞！")
                    st.rerun()
            except Exception as e:
                st.error(f"檔案格式錯誤: {e}")

        st.divider()
        st.subheader("目前清單管理")
        if st.button("🗑️ 清空所有字詞"):
            st.session_state.challenges = []
            save_data(st.session_state.challenges) # 儲存至檔案
            st.session_state.idx = 0
            st.rerun()
            
        for i, item in enumerate(st.session_state.challenges):
            cols = st.columns([3, 1])
            cols[0].write(f"{item['animal']} {item['word']}")
            if cols[1].button("❌", key=f"del_{i}"):
                st.session_state.challenges.pop(i)
                save_data(st.session_state.challenges) # 儲存至檔案
                st.rerun()

# --- 5. 主介面樣式 ---
st.set_page_config(page_title="生字冒險王 11.3", layout="centered")
st.markdown("""
    <style>
    .celebration-box { text-align: center; padding: 40px; background-color: #f0fdf4; border-radius: 30px; border: 5px solid #22c55e; }
    .big-animal { font-size: 150px; margin: 0; }
    .congrat-text { font-size: 36px; color: #166534; font-weight: bold; margin-top: 20px; }
    .target-word-display { font-size: 80px; font-weight: bold; color: #333; letter-spacing: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 6. 遊戲流程 ---
if not st.session_state.challenges:
    st.info("目前字詞庫是空的，請先從左側管理後台新增字詞。")
    st.stop()

if st.session_state.idx >= len(st.session_state.challenges):
    st.session_state.idx = 0

if mode == "🎯 學生挑戰":
    if st.session_state.success_mode:
        target = st.session_state.challenges[st.session_state.idx]
        st.balloons()
        st.markdown(f"""
            <div class="celebration-box">
                <p class="big-animal">{target['animal']}</p>
                <p class="congrat-text">太棒了，繼續挑戰吧！</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🌟 進入下一關 🌟", use_container_width=True):
            st.session_state.idx = (st.session_state.idx + 1) % len(st.session_state.challenges)
            st.session_state.success_mode = False
            st.session_state.need_crop = False
            st.session_state.uploader_key += 1
            st.rerun()
    else:
        st.title("🐾 生字冒險王 Pro 11.3")
        
        cols = st.columns(min(len(st.session_state.challenges), 6))
        for i, c in enumerate(st.session_state.challenges[:6]):
            icon = c['animal'] if c['animal'] in st.session_state.collection else "❓"
            cols[i].write(f"<h3 style='text-align: center;'>{icon}</h3>", unsafe_allow_html=True)

        target = st.session_state.challenges[st.session_state.idx]
        st.markdown(f"""
            <div style="text-align:center; background:white; padding:30px; border-radius:20px; border:2px solid #eee;">
                <p style='color: #888;'>請在紙上寫出：</p>
                <div class="target-word-display">{target['word']}</div>
            </div>
        """, unsafe_allow_html=True)

        st.write("---")
        img_file = st.file_uploader("📸 拍照或上傳生字圖片", type=['png', 'jpg', 'jpeg'], key=f"uploader_{st.session_state.uploader_key}")

        if img_file:
            raw_img = Image.open(img_file)
            if not st.session_state.need_crop:
                processed_img = advanced_preprocess(raw_img)
                st.image(processed_img, caption="AI 正在快速掃描...", use_container_width=True)
                with st.spinner("🔍 辨識中..."):
                    results = reader.readtext(processed_img, detail=0, paragraph=True, decoder='greedy')
                    full_detected_text = "".join(results)
                    if smart_check(target['word'], full_detected_text):
                        if target['animal'] not in st.session_state.collection:
                            st.session_state.collection.append(target['animal'])
                        st.session_state.success_mode = True
                        st.rerun()
                    else:
                        st.error(f"🔍 辨識失敗：認成「{full_detected_text if full_detected_text else '無法辨識'}」")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✂️ 手動截圖區域", use_container_width=True):
                                st.session_state.need_crop = True
                                st.rerun()
                        with c2:
                            if st.button("🙋 人工核准通過", use_container_width=True):
                                if target['animal'] not in st.session_state.collection:
                                    st.session_state.collection.append(target['animal'])
                                st.session_state.success_mode = True
                                st.rerun()
            else:
                st.warning("🎯 請調整紅框對準生字：")
                cropped_img = st_cropper(raw_img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
                st.image(cropped_img, width=200, caption="截圖預覽")
                if st.button("🚀 再次辨識此區域", use_container_width=True):
                    final_img = advanced_preprocess(cropped_img)
                    with st.spinner("🔍 快速比對中..."):
                        new_results = reader.readtext(final_img, detail=0, paragraph=True, decoder='greedy')
                        new_text = "".join(new_results)
                        if smart_check(target['word'], new_text):
                            if target['animal'] not in st.session_state.collection:
                                f"🎉 通過：{target['animal']}"
                                st.session_state.collection.append(target['animal'])
                            st.session_state.success_mode = True
                            st.rerun()
                        else:
                            st.error(f"🔍 區域辨識失敗：認成 「{new_text}」")
                if st.button("⬅️ 返回"):
                    st.session_state.need_crop = False
                    st.rerun()

st.divider()
st.caption("版本：11.3 | 優化 Emoji 選取方式")