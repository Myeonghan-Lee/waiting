import streamlit as st
import requests
import threading
from datetime import datetime, timezone, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="진로학업 상담 대기 현황", layout="wide")

# 서울 시간대 설정 (UTC+9) - 해외 서버 구동 시 시간 맞춤용
seoul_tz = timezone(timedelta(hours=9))

# =======================================================
# [설정] 구글 앱스 스크립트 배포 후 복사한 웹앱 URL을 입력하세요.
# =======================================================
API_URL = "여기에_구글_웹앱_URL을_넣으세요"
# =======================================================

# 구글 시트에서 설정값 및 명단을 가져오는 함수
def fetch_from_gsheets():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            res_json = response.json()
            
            # 새 스크립트 포맷 대응 검증
            if "settings" in res_json:
                settings = res_json["settings"]
                raw_list = res_json["list"]
            else:
                settings = {"title": "진로학업 상담 대기 현황", "alert_seconds": 450}
                raw_list = res_json

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
                    "start_time": None,
                    "alert_triggered": False,
                    "flash_start_time": None
                })
            return {"settings": settings, "data": grouped}
    except Exception as e:
        st.error(f"구글 시트 읽기 실패: {e}")
    return {"settings": {"title": "진로학업 상담 대기 현황", "alert_seconds": 450}, "data": {}}

# 구글 시트에 데이터 업데이트 요청
def write_to_gsheets(row, next_status):
    try:
        params = {"action": "update", "row": row, "status": next_status}
        requests.get(API_URL, params=params)
    except Exception as e:
        pass

# 전역 공유 메모리
@st.cache_resource
def get_shared_state():
    return {"payload": fetch_from_gsheets()}

state = get_shared_state()

# 사이드바 설정 영역
st.sidebar.title("🛠️ 시스템 설정")
role = st.sidebar.selectbox("모드 선택", ["📢 대기실 화면", "🛠️ 선생님용 관리 패널", "👑 중간 관리자 화면"])

if st.sidebar.button("🔄 구글 시트 새로고침"):
    state["payload"] = fetch_from_gsheets()
    st.sidebar.success("동기화가 완료되었습니다!")
    st.rerun()

# 전역 설정값 로드
event_title = state["payload"]["settings"].get("title", "진로학업 상담 대기 현황")
alert_seconds_limit = int(state["payload"]["settings"].get("alert_seconds", 450))

# --- 모드 1: 대기실 화면 ---
if role == "📢 대기실 화면":
    st.title(f"📢 {event_title}")
    
    @st.fragment(run_every=1)
    def render_waiting_room():
        st.markdown("<style>.stApp { background-color: #f8f9fa !important; }</style>", unsafe_allow_html=True)
        
        # 서울 시간으로 시계 표시
        current_time = datetime.now(seoul_tz).strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
        st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
        st.markdown("---")
        
        current_data = state["payload"]["data"]
        if not current_data:
            st.warning("등록된 데이터가 없습니다.")
            return
            
        teachers = list(current_data.keys())
        
        # 6명씩 끊어서 2줄로 배치하는 그리드 정렬 알고리즘
        row1_teachers = teachers[:6]
        row2_teachers = teachers[6:12]
        
        def display_column(t_key):
            st.markdown(f"### 🏫 {t_key}")
            for parent in current_data[t_key]:
                name = parent["name"]
                status = parent["status"]
                if status == "상담중":
                    st.info(f"🟢 **{name}** (상담 중)")
                elif status == "상담종료":
                    st.markdown(f"⚪ ~~{name} (종료)~~")
                else:
                    st.markdown(f"◽ {name}")
            st.markdown("---")

        # 첫 번째 줄 출력 (최대 6개)
        cols1 = st.columns(6)
        for idx, t_key in enumerate(row1_teachers):
            with cols1[idx]:
                display_column(t_key)
                
        # 두 번째 줄 출력 (최대 6개)
        if row2_teachers:
            cols2 = st.columns(6)
            for idx, t_key in enumerate(row2_teachers):
                with cols2[idx]:
                    display_column(t_key)
                    
    render_waiting_room()

# --- 모드 2: 선생님용 관리 패널 ---
elif role == "🛠️ 선생님용 관리 패널":
    st.title(f"🛠️ {event_title} - 교사 전용")
    
    current_data = state["payload"]["data"]
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("데이터를 읽어올 수 없습니다.")
    else:
        my_teacher = st.sidebar.selectbox("본인 성함을 선택하세요", teachers_list)
        
        @st.fragment(run_every=1)
        def render_teacher_panel():
            parents_list = current_data.get(my_teacher, [])
            active_flash = False
            flash_phase = False
            
            # 알림 제한 시간에 도달했는지 확인 (구글 시트에서 설정한 값 적용)
            for idx, parent in enumerate(parents_list):
                status = parent["status"]
                start_time = parent.get("start_time")
                
                if status == "상담중" and start_time:
                    elapsed_sec = int((datetime.now(seoul_tz) - start_time).total_seconds())
                    
                    if elapsed_sec >= alert_seconds_limit and not parent.get("alert_triggered", False):
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
            st.markdown(f"#### 🕒 현재 시각 (서울): **{current_time}**")
            st.markdown(f"##### 📌 {my_teacher} 담당 학부모 목록 (경고 임계치: {alert_seconds_limit}초)")
            
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
                        threading.Thread(target=write_to_gsheets, args=(row_num, "상담중")).start()
                        st.rerun()
                        
                with col3:
                    if st.button("상담 종료", key=f"end_{my_teacher}_{idx}", disabled=(status != "상담중")):
                        parent["status"] = "상담종료"
                        threading.Thread(target=write_to_gsheets, args=(row_num, "상담종료")).start()
                        st.rerun()
                        
        render_teacher_panel()

# --- 모드 3: 중간 관리자 화면 ---
else:
    st.title(f"👑 {event_title} - 통합 관제 시스템")
    
    current_data = state["payload"]["data"]
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("데이터를 읽어올 수 없습니다.")
    else:
        # 관제 대상 선생님 선택 (기본적으로 첫 6명 우선 배치)
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
                
            # 화면 레이아웃: 3열씩 2줄 그리드로 정렬하여 효율적으로 6명을 한 화면에 수용
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
                        
                        # 공간 효율을 위해 이름과 버튼을 좌우 분할 정렬
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
                            # 좁은 카드 영역 전용 초미니 버튼식 관리 도구
                            if p_status == "대기":
                                if st.button("시작", key=f"mgr_st_{t_key}_{p_idx}", use_container_width=True):
                                    parent["status"] = "상담중"
                                    parent["start_time"] = datetime.now(seoul_tz)
                                    parent["alert_triggered"] = False
                                    parent["flash_start_time"] = None
                                    threading.Thread(target=write_to_gsheets, args=(p_row_num, "상담중")).start()
                                    st.rerun()
                            elif p_status == "상담중":
                                if st.button("종료", key=f"mgr_en_{t_key}_{p_idx}", use_container_width=True):
                                    parent["status"] = "상담종료"
                                    threading.Thread(target=write_to_gsheets, args=(p_row_num, "상담종료")).start()
                                    st.rerun()
                            else:
                                st.caption("완료됨")
                    st.markdown("---")
                    
        render_manager_panel()
