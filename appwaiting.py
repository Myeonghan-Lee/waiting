import streamlit as st
import requests
import threading
import json
import os
import re
from datetime import datetime, timezone, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="진로학업 상담 대기 현황", layout="wide")

# 서울 시간대 설정 (UTC+9)
seoul_tz = timezone(timedelta(hours=9))

# 영구 저장을 위한 로컬 설정 파일 경로
CONFIG_FILE = "settings_config.json"

# 유튜브 주소에서 11자리 비디오 ID 추출하는 정규식 함수
def extract_yt_id(url):
    if not url:
        return None
    pattern = r'(?:v=|\/embed\/|\/1\/|\/v\/|https:\/\/youtu\.be\/|\/shorts\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# 1. 구글 시트에서 전체 데이터를 원본 그대로 읽어오는 함수
def fetch_from_gsheets(api_url):
    if not api_url:
        return {}
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            raw_list = response.json()
            grouped = {}
            for item in raw_list:
                t = item["teacher"]
                if t not in grouped:
                    grouped[t] = []
                grouped[t].append({
                    "row": item["row"],
                    "name": item["parent"],
                    "status": item["status"],
                    "school": item.get("school", ""),
                    "start_time": None,         # 상담 시작 시각 (RAM)
                    "alert_triggered": False,   # 경고 활성화 여부 (RAM)
                    "flash_start_time": None    # 깜빡임 애니메이션 시작 시각 (RAM)
                })
            return grouped
    except Exception as e:
        st.error(f"구글 시트 읽기 실패: {e}")
    return {}

# 2. 구글 시트에 상태를 업데이트하는 함수
def write_to_gsheets(api_url, row, next_status):
    if not api_url:
        return
    try:
        params = {"action": "update", "row": row, "status": next_status}
        requests.get(api_url, params=params)
    except Exception as e:
        pass

# 3. 로컬 파일에서 설정값을 로드하는 함수
def load_config_from_file():
    default_config = {
        "api_url": "",                            # 구글 앱스 스크립트 웹앱 URL
        "event_title": "진로학업 상담 대기 현황",   # 기본 행사명
        "alert_seconds": 450,                     # 기본 알림 제한 시간 (7분 30초)
        "yt_url_1": "",                           # 유튜브 링크 1
        "yt_url_2": "",                           # 유튜브 링크 2
        "data": {}                                # 로드된 명단 데이터
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                default_config.update(saved_data)
        except Exception:
            pass
    return default_config

# 4. 전역 공유 메모리 초기화
@st.cache_resource
def get_global_config():
    config = load_config_from_file()
    if config["api_url"]:
        config["data"] = fetch_from_gsheets(config["api_url"])
    return config

config = get_global_config()

# 사이드바 설정 영역
st.sidebar.title("🛠️ 모드 선택")
role = st.sidebar.selectbox(
    "원하는 모드를 선택하세요", 
    ["📢 대기실 화면", "🛠️ 선생님용 관리 패널", "👑 중간 관리자 화면", "⚙️ 시스템 설정"]
)

# 구글 API URL 미등록 시 경고 문구 표시 (설정 화면 제외)
if not config["api_url"] and role != "⚙️ 시스템 설정":
    st.warning("⚠️ 구글 앱스 스크립트 URL이 등록되지 않았습니다. 사이드바에서 '⚙️ 시스템 설정'으로 이동하여 최초 설정을 완료해 주세요.")
    st.stop()

# --- 모드 1: 대기실 화면 ---
if role == "📢 대기실 화면":
    st.title(f"📢 {config['event_title']}")
    
    @st.fragment(run_every=1)
    def render_waiting_room():
        # 유튜브 ID 추출 및 임베드 URL 조합 (음소거/자동재생/무한반복 루프 적용)
        yt_id1 = extract_yt_id(config.get("yt_url_1", ""))
        yt_id2 = extract_yt_id(config.get("yt_url_2", ""))
        
        has_video = False
        embed_url = ""
        
        if yt_id1 and yt_id2:
            has_video = True
            embed_url = f"https://www.youtube.com/embed/{yt_id1}?playlist={yt_id1},{yt_id2}&autoplay=1&loop=1&mute=1"
        elif yt_id1:
            has_video = True
            embed_url = f"https://www.youtube.com/embed/{yt_id1}?playlist={yt_id1}&autoplay=1&loop=1&mute=1"
        elif yt_id2:
            has_video = True
            embed_url = f"https://www.youtube.com/embed/{yt_id2}?playlist={yt_id2}&autoplay=1&loop=1&mute=1"

        # 영상 레이아웃 유무에 따른 동적 스타일 설정 및 픽셀 고정 행 스타일 정의
        right_padding = 660 if has_video else 20
        st.markdown(f"""
            <style>
            /* 메인 화면 우측 여백 조절 */
            .block-container {{
                max-width: 100% !important;
                padding-right: {right_padding}px !important;
                background-color: #f8f9fa !important;
                transition: padding-right 0.3s ease;
            }}
            /* 행 높이 고정을 위한 CSS */
            .parent-row-fixed {{
                height: 42px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 6px 12px;
                margin-bottom: 5px;
                border-radius: 6px;
                border: 1px solid #e2e8f0;
                box-sizing: border-box;
                font-size: 0.95em;
            }}
            .waiting-status {{
                background-color: #ffffff;
                color: #4a5568;
            }}
            .processing-status {{
                background-color: #c6f6d5;
                color: #22543d;
                border-color: #9ae6b4;
                font-weight: bold;
            }}
            .done-status {{
                background-color: #edf2f7;
                color: #a0aec0;
                text-decoration: line-through;
                opacity: 0.7;
            }}
            .empty-spacer {{
                border: 1px dashed #e2e8f0;
                background-color: transparent;
                visibility: hidden;
            }}
            </style>
        """, unsafe_allow_html=True)
        
        # 시계 사이즈 소형화 및 아래 마진 제거
        current_time = datetime.now(seoul_tz).strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
        st.markdown(f"""
            <div style="font-size: 13px; color: #4a5568; margin-bottom: 0px; padding-bottom: 0px; line-height: 1;">
                🕒 현재 시각: {current_time}
            </div>
            <hr style="margin-top: 5px; margin-bottom: 12px; border: 0; height: 1px; background: #cbd5e0;">
        """, unsafe_allow_html=True)
        
        current_data = config["data"]
        if not current_data:
            st.warning("등록된 데이터가 없거나 구글 시트 연동 대기 중입니다.")
            return
            
        teachers = list(current_data.keys())
        row1_teachers = teachers[:6]
        row2_teachers = teachers[6:12]
        
        def display_column(t_key):
            st.markdown(f"<h4 style='margin-top:0px; margin-bottom:8px; font-size:1.15em;'>🏫 {t_key}</h4>", unsafe_allow_html=True)
            parents = current_data[t_key]
            
            # 학생 수와 상관없이 항상 정확히 7행을 그리도록 설계 (빈 자리는 투명 Spacer 채움)
            for k in range(7):
                if k < len(parents):
                    parent = parents[k]
                    name = parent["name"]
                    status = parent["status"]
                    
                    if status == "상담중":
                        class_name = "processing-status"
                        status_text = "상담중"
                        bold_style = "font-weight: bold;"
                    elif status == "상담종료":
                        class_name = "done-status"
                        status_text = "종료"
                        bold_style = ""
                    else:
                        class_name = "waiting-status"
                        status_text = ""
                        bold_style = ""
                        
                    st.markdown(f"""
                        <div class="parent-row-fixed {class_name}">
                            <span style="{bold_style}">{name}</span>
                            <span style="font-size: 0.85em; font-weight: bold;">{status_text}</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    # 행 정렬 무너짐 방지용 Invisible Spacer
                    st.markdown("""
                        <div class="parent-row-fixed empty-spacer">
                            &nbsp;
                        </div>
                    """, unsafe_allow_html=True)
            st.markdown("---")

        cols1 = st.columns(6)
        for idx, t_key in enumerate(row1_teachers):
            with cols1[idx]:
                display_column(t_key)
                
        if row2_teachers:
            cols2 = st.columns(6)
            for idx, t_key in enumerate(row2_teachers):
                with cols2[idx]:
                    display_column(t_key)

        # 우측 여백 0, 세로축 중앙 정렬로 고정된 유튜브 컨테이너 마운트
        if has_video:
            st.markdown(f"""
                <div style="
                    position: fixed;
                    right: 0px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 640px;
                    height: 360px;
                    z-index: 10000;
                    background-color: #000;
                    box-shadow: -4px 0px 12px rgba(0,0,0,0.15);
                ">
                    <iframe width="640" height="360" src="{embed_url}" frameborder="0" allow="autoplay; encrypted-media;" allowfullscreen></iframe>
                </div>
            """, unsafe_allow_html=True)
                    
    render_waiting_room()

# --- 모드 2: 선생님용 관리 패널 ---
elif role == "🛠️ 선생님용 관리 패널":
    st.title(f"🛠️ {config['event_title']} - 교사 전용")
    
    current_data = config["data"]
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("데이터를 읽어올 수 없습니다. 설정 창에서 URL 등록과 동기화가 제대로 되었는지 확인하십시오.")
    else:
        my_teacher = st.sidebar.selectbox("본인 성함을 선택하세요", teachers_list)
        
        @st.fragment(run_every=1)
        def render_teacher_panel():
            parents_list = current_data.get(my_teacher, [])
            active_flash = False
            flash_phase = False
            alert_limit = config["alert_seconds"]
            
            # 알림 제한 시간에 도달했는지 확인
            for idx, parent in enumerate(parents_list):
                status = parent["status"]
                start_time = parent.get("start_time")
                
                if status == "상담중" and start_time:
                    elapsed_sec = int((datetime.now(seoul_tz) - start_time).total_seconds())
                    
                    if elapsed_sec >= alert_limit and not parent.get("alert_triggered", False):
                        parent["alert_triggered"] = True
                        parent["flash_start_time"] = datetime.now(seoul_tz)
                    
                    if parent.get("flash_start_time"):
                        flash_elapsed = (datetime.now(seoul_tz) - parent["flash_start_time"]).total_seconds()
                        if flash_elapsed <= 10:
                            active_flash = True
                            if int(flash_elapsed) % 2 == 0:
                                flash_phase = True
            
            # 화면 오렌지색 깜빡임 처리
            if active_flash:
                if flash_phase:
                    st.markdown("""
                        <style>
                        .stApp { background-color: #FFD5A1 !important; transition: background-color 0.2s ease; }
                        </style>
                        <div style="background-color: #FF8C00; color: white; padding: 15px; text-align: center; font-size: 20px; font-weight: bold; border-radius: 8px; margin-bottom: 20px;">
                            ⚠️ 상담 설정 시간 경과! 상담을 정리해 주십시오. ⚠️
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("<style>.stApp { background-color: #f8f9fa !important; transition: background-color 0.2s ease; }</style>", unsafe_allow_html=True)
            else:
                st.markdown("<style>.stApp { background-color: #f8f9fa !important; }</style>", unsafe_allow_html=True)

            current_time = datetime.now(seoul_tz).strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
            st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
            st.markdown(f"##### 📌 {my_teacher} 담당 학부모 목록 (경고 기준: {alert_limit // 60}분 {alert_limit % 60}초)")
            
            for idx, parent in enumerate(parents_list):
                col1, col2, col3 = st.columns([2, 1, 1])
                status = parent["status"]
                row_num = parent["row"]
                start_time = parent.get("start_time")
                
                school_name = f"({parent['school']})" if parent.get("school") else ""
                display_name = f"{parent['name']}{school_name}"
                
                with col1:
                    if status == "상담중":
                        if start_time:
                            elapsed_sec = int((datetime.now(seoul_tz) - start_time).total_seconds())
                            mins, secs = divmod(elapsed_sec, 60)
                            time_badge = f"<span style='color:green; font-weight:bold;'>[상담 중] {mins:02d}:{secs:02d}</span>"
                        else:
                            time_badge = "<span style='color:green; font-weight:bold;'>[상담 중]</span>"
                        st.markdown(f"🟢 **{display_name}** {time_badge}", unsafe_allow_html=True)
                    elif status == "상담종료":
                        st.markdown(f"🔴 ~~{display_name} (완료)~~")
                    else:
                        st.markdown(f"◽ {display_name} (대기 중)")
                        
                with col2:
                    if st.button("상담 시작", key=f"start_{my_teacher}_{idx}", disabled=(status != "대기")):
                        parent["status"] = "상담중"
                        parent["start_time"] = datetime.now(seoul_tz)
                        parent["alert_triggered"] = False
                        parent["flash_start_time"] = None
                        threading.Thread(target=write_to_gsheets, args=(config["api_url"], row_num, "상담중")).start()
                        st.rerun()
                        
                with col3:
                    if st.button("상담 종료", key=f"end_{my_teacher}_{idx}", disabled=(status != "상담중")):
                        parent["status"] = "상담종료"
                        threading.Thread(target=write_to_gsheets, args=(config["api_url"], row_num, "상담종료")).start()
                        st.rerun()
                        
        render_teacher_panel()

# --- 모드 3: 중간 관리자 화면 ---
elif role == "👑 중간 관리자 화면":
    st.title(f"👑 {config['event_title']} - 통합 관제 시스템")
    
    current_data = config["data"]
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("데이터를 읽어올 수 없습니다. 설정 페이지에서 URL 설정 및 데이터 동기화를 진행하십시오.")
    else:
        st.sidebar.subheader("관제 설정")
        selected_teachers = st.sidebar.multiselect(
            "모니터링할 선생님 선택 (최대 6명)",
            teachers_list,
            default=teachers_list[:6]
        )
        
        @st.fragment(run_every=1)
        def render_manager_panel():
            current_time = datetime.now(seoul_tz).strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
            st.markdown(f"#### 🕒 현재 시각 (서울): **{current_time}**")
            st.write("※ 한 번에 6개 부스의 진행 상태와 경과 시간을 제어 및 관리할 수 있습니다.")
            st.markdown("---")
            
            if not selected_teachers:
                st.info("사이드바에서 관제할 선생님을 선택해 주세요.")
                return
                
            m_cols = st.columns(3)
            
            for idx, t_key in enumerate(selected_teachers[:6]):
                col_idx = idx % 3
                with m_cols[col_idx]:
                    st.markdown(f"### 🏫 {t_key}")
                    parents_list = current_data.get(t_key, [])
                    
                    for p_idx, parent in enumerate(parents_list):
                        p_status = parent["status"]
                        p_row_num = parent["row"]
                        p_start_time = parent.get("start_time")
                        
                        school_name = f"({parent['school']})" if parent.get("school") else ""
                        p_display_name = f"{parent['name']}{school_name}"
                        
                        sc1, sc2 = st.columns([1.5, 1])
                        
                        with sc1:
                            if p_status == "상담중":
                                if p_start_time:
                                    elapsed_sec = int((datetime.now(seoul_tz) - p_start_time).total_seconds())
                                    mins, secs = divmod(elapsed_sec, 60)
                                    st.markdown(f"🟢 **{parent['name']}** <span style='color:green; font-weight:bold;'>{mins:02d}:{secs:02d}</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"🟢 **{parent['name']}**", unsafe_allow_html=True)
                            elif p_status == "상담종료":
                                st.markdown(f"🔴 ~~{parent['name']}~~")
                            else:
                                st.markdown(f"◽ {parent['name']}")
                                
                        with sc2:
                            if p_status == "대기":
                                if st.button("시작", key=f"mgr_st_{t_key}_{p_idx}", use_container_width=True):
                                    parent["status"] = "상담중"
                                    parent["start_time"] = datetime.now(seoul_tz)
                                    parent["alert_triggered"] = False
                                    parent["flash_start_time"] = None
                                    threading.Thread(target=write_to_gsheets, args=(config["api_url"], p_row_num, "상담중")).start()
                                    st.rerun()
                            elif p_status == "상담중":
                                if st.button("종료", key=f"mgr_en_{t_key}_{p_idx}", use_container_width=True):
                                    parent["status"] = "상담종료"
                                    threading.Thread(target=write_to_gsheets, args=(config["api_url"], p_row_num, "상담종료")).start()
                                    st.rerun()
                            else:
                                st.caption("완료됨")
                    st.markdown("---")
                    
        render_manager_panel()

# --- 모드 4: 시스템 설정 페이지 (비밀번호 보안) ---
else:
    st.title("⚙️ 시스템 설정 및 초기 환경 세팅")
    
    if "settings_authorized" not in st.session_state:
        st.session_state["settings_authorized"] = False
        
    if not st.session_state["settings_authorized"]:
        st.markdown("### 🔒 권한 보안")
        st.write("본 환경설정 공간은 관리 전용입니다. 비밀번호를 입력해 주십시오.")
        
        pw_input = st.text_input("접근 비밀번호 입력", type="password")
        if st.button("설정 잠금 해제", type="primary", use_container_width=True) or (pw_input and pw_input == "7854"):
            if pw_input == "7854":
                st.session_state["settings_authorized"] = True
                st.success("인증에 성공했습니다!")
                st.rerun()
            elif pw_input:
                st.error("비밀번호가 올바르지 않습니다. 다시 확인하십시오.")
        st.stop()
        
    col_title, col_lock = st.columns([4, 1])
    with col_title:
        st.write("🔧 행사 운영 설정을 수정할 수 있습니다. 저장 시 서버 내부 스토리지에 자동 기재됩니다.")
    with col_lock:
        if st.button("🔒 다시 잠그기(로그아웃)", use_container_width=True):
            st.session_state["settings_authorized"] = False
            st.rerun()
            
    st.markdown("---")
    
    new_title = st.text_input("1. 행사명 설정", value=config["event_title"])
    
    st.write("2. 교사 관리 패널 경고 시간 설정")
    col1, col2 = st.columns(2)
    with col1:
        alert_min = st.number_input("알림 기준 (분)", min_value=0, max_value=60, value=int(config["alert_seconds"] // 60))
    with col2:
        alert_sec = st.number_input("알림 기준 (초)", min_value=0, max_value=59, value=int(config["alert_seconds"] % 60))
        
    new_url = st.text_input(
        "3. 구글 앱스 스크립트 웹앱 URL 입력", 
        value=config["api_url"], 
        placeholder="https://script.google.com/macros/s/.../exec"
    )

    st.write("4. 대기화면 실시간 스트리밍용 유튜브 영상 설정 (최대 2개 링크 등록 가능 / 반복 재생 지원)")
    yt_url_1 = st.text_input("유튜브 링크 1", value=config.get("yt_url_1", ""), placeholder="https://www.youtube.com/watch?v=...")
    yt_url_2 = st.text_input("유튜브 링크 2", value=config.get("yt_url_2", ""), placeholder="https://youtu.be/...")
    
    st.markdown("---")
    if st.button("💾 설정 저장 및 스프레드시트 동기화", use_container_width=True, type="primary"):
        # 전역 메모리 캐시 값 갱신
        config["api_url"] = new_url
        config["event_title"] = new_title
        config["alert_seconds"] = (alert_min * 60) + alert_sec
        config["yt_url_1"] = yt_url_1
        config["yt_url_2"] = yt_url_2
        
        with st.spinner("구글 스프레드시트에서 데이터를 새로 가져오는 중입니다..."):
            fresh_data = fetch_from_gsheets(new_url)
            if fresh_data:
                config["data"] = fresh_data
                
                # 로컬 디스크 파일에 영구 보존용 저장
                try:
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        json.dump({
                            "api_url": new_url,
                            "event_title": new_title,
                            "alert_seconds": (alert_min * 60) + alert_sec,
                            "yt_url_1": yt_url_1,
                            "yt_url_2": yt_url_2
                        }, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    st.error(f"영구 데이터 파일 기록 도중 오류가 발생했습니다: {e}")
                
                st.success("설정 값이 정상적으로 보존되었으며, 스프레드시트 동기화에 성공했습니다!")
                st.rerun()
            else:
                st.warning("설정 값은 기록되었으나 구글 시트 데이터를 로드하지 못했습니다. 입력하신 구글 URL과 권한 설정을 확인해 주십시오.")
