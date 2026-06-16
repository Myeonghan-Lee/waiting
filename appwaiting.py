import streamlit as st
import requests
import threading
from datetime import datetime, timedelta, timezone

# -----------------------------------------------------------------------------
# 페이지 및 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="진로학업 팝업 데스크 대기 현황", layout="wide")

# 2. 상담 대기 화면의 시간을 서울 시간으로 설정 (KST: UTC+9)
KST = timezone(timedelta(hours=9))

# [설정] 구글 앱스 스크립트 배포 후 복사한 웹앱 URL을 입력하세요.
API_URL = "https://script.google.com/macros/s/AKfycbxIMVJhXiish8irtUha4wgMx7N-0AF4M4z8DO0j13pArg71XZFS6qCXyP53tDTTSpFi/exec"

# -----------------------------------------------------------------------------
# 데이터 통신 함수
# -----------------------------------------------------------------------------
def fetch_from_gsheets():
    try:
        response = requests.get(API_URL)
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
                    "school": item.get("school", ""),  # 구글 시트 D열의 학교명 정보 추가
                    "start_time": None,         # 상담 시작 시각 (RAM)
                    "alert_triggered": False,   # 경고 활성화 여부 (RAM)
                    "flash_start_time": None    # 깜빡임 애니메이션 시작 시각 (RAM)
                })
            return grouped
    except Exception as e:
        st.error(f"구글 시트 읽기 실패: {e}")
    return {}

def write_to_gsheets(row, next_status):
    try:
        params = {"action": "update", "row": row, "status": next_status}
        requests.get(API_URL, params=params)
    except Exception as e:
        pass

# -----------------------------------------------------------------------------
# 전역 상태 관리 (앱 시작 시 또는 새로고침 시 로드)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_shared_state():
    return {
        "data": fetch_from_gsheets(),
        "event_name": "2026 강서양천 진로학업 팝업 데스크", # 기본 행사명
        "alert_seconds": 450 # 기본 경고 알림 시간 (7분 30초 = 450초)
    }

state = get_shared_state()

# -----------------------------------------------------------------------------
# 사이드바 설정 영역
# -----------------------------------------------------------------------------
st.sidebar.title("설정 메뉴")
role = st.sidebar.selectbox("모드 선택", ["📢 대기실 화면", "🛠️ 선생님용 관리 패널", "👑 중간 관리자용 패널"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ 환경 설정 (전체 적용)")

# 1. 행사명 변경 기능
new_event_name = st.sidebar.text_input("행사명 설정", value=state["event_name"])
if new_event_name != state["event_name"]:
    state["event_name"] = new_event_name

# 3. 선생님용 관리 패널 알림 시간 설정
st.sidebar.markdown("**상담 경고 알림 시간 설정**")
col_m, col_s = st.sidebar.columns(2)
with col_m:
    alert_mins = st.number_input("분", min_value=0, max_value=60, value=state["alert_seconds"] // 60)
with col_s:
    alert_secs = st.number_input("초", min_value=0, max_value=59, value=state["alert_seconds"] % 60)

# 알림 시간이 변경되었을 경우 업데이트
new_alert_seconds = alert_mins * 60 + alert_secs
if new_alert_seconds != state["alert_seconds"]:
    state["alert_seconds"] = new_alert_seconds

st.sidebar.markdown("---")
if st.sidebar.button("🔄 구글 시트 명단 새로고침"):
    state["data"] = fetch_from_gsheets()
    st.sidebar.success("구글 시트의 최신 명단을 동기화했습니다!")
    st.rerun()

# -----------------------------------------------------------------------------
# 모드 A: 대기실 화면
# -----------------------------------------------------------------------------
if role == "📢 대기실 화면":
    st.title(f"📢 {state['event_name']} 대기 현황판")
    
    @st.fragment(run_every=1)
    def render_waiting_room():
        st.markdown("<style>.stApp { background-color: #f8f9fa !important; }</style>", unsafe_allow_html=True)
        
        # 실시간 시계 표시 (서울 시간 기준)
        current_time = datetime.now(KST).strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
        st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
        st.markdown("---")
        
        current_data = state["data"]
        if not current_data:
            st.warning("데이터를 불러오는 중이거나 구글 시트에 명단이 비어 있습니다.")
            return
            
        teachers = list(current_data.keys())
        
        # 4. 화면 표시는 6명 2줄 (6개의 컬럼으로 분할)
        for i in range(0, len(teachers), 6):
            cols = st.columns(6)
            for j in range(6):
                if i + j < len(teachers):
                    t_key = teachers[i + j]
                    with cols[j]:
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
                
    render_waiting_room()

# -----------------------------------------------------------------------------
# 모드 B: 선생님용 관리 패널
# -----------------------------------------------------------------------------
elif role == "🛠️ 선생님용 관리 패널":
    st.title(f"🛠️ {state['event_name']} - 선생님용 관리 패널")
    
    current_data = state["data"]
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("명단을 불러올 수 없습니다. 사이드바의 새로고침 버튼을 눌러보세요.")
    else:
        my_teacher = st.sidebar.selectbox("본인 성함을 선택하세요", teachers_list)
        
        @st.fragment(run_every=1)
        def render_teacher_panel():
            parents_list = current_data.get(my_teacher, [])
            
            active_flash = False
            flash_phase = False 
            
            # 상담 시간 체크 및 경고 시점 계산
            for idx, parent in enumerate(parents_list):
                status = parent["status"]
                start_time = parent.get("start_time")
                
                if status == "상담중" and start_time:
                    elapsed_sec = int((datetime.now(KST) - start_time).total_seconds())
                    
                    if elapsed_sec >= state["alert_seconds"] and not parent.get("alert_triggered", False):
                        parent["alert_triggered"] = True
                        parent["flash_start_time"] = datetime.now(KST)
                    
                    if parent.get("flash_start_time"):
                        flash_elapsed = (datetime.now(KST) - parent["flash_start_time"]).total_seconds()
                        if flash_elapsed <= 10:
                            active_flash = True
                            if int(flash_elapsed) % 2 == 0:
                                flash_phase = True
            
            # 오렌지 깜빡임 화면 효과 반영
            if active_flash:
                if flash_phase:
                    st.markdown(f"""
                        <style>
                        .stApp {{
                            background-color: #FFD5A1 !important; 
                            transition: background-color 0.2s ease;
                        }}
                        </style>
                        <div style="background-color: #FF8C00; color: white; padding: 15px; text-align: center; font-size: 20px; font-weight: bold; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            ⚠️ 상담 시간 {state['alert_seconds'] // 60}분 {state['alert_seconds'] % 60}초 경과! 상담을 마무리해 주세요. ⚠️
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("<style>.stApp { background-color: #f8f9fa !important; }</style>", unsafe_allow_html=True)
            else:
                st.markdown("<style>.stApp { background-color: #f8f9fa !important; }</style>", unsafe_allow_html=True)

            # 실시간 시계 표시 (서울 시간 기준)
            current_time = datetime.now(KST).strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
            st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
            st.markdown(f"##### 📌 {my_teacher} 담당 학부모 목록")
            st.write("상태 변경 시 구글 스프레드시트 및 대기실 화면에 즉시 반영됩니다.")
            
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
                            elapsed_sec = int((datetime.now(KST) - start_time).total_seconds())
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
                        parent["start_time"] = datetime.now(KST)
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

# -----------------------------------------------------------------------------
# 모드 C: 중간 관리자용 패널 (전체 보기)
# -----------------------------------------------------------------------------
elif role == "👑 중간 관리자용 패널":
    st.title(f"👑 {state['event_name']} - 전체 관리자 패널")
    
    current_data = state["data"]
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("명단을 불러올 수 없습니다. 사이드바의 새로고침 버튼을 눌러보세요.")
    else:
        @st.fragment(run_every=1)
        def render_admin_panel():
            # 관리자 패널에서는 화면 전체 점멸은 막고, 상단 경고 배너만 띄웁니다.
            over_limit_teachers = []
            
            for t_key in teachers_list:
                for parent in current_data.get(t_key, []):
                    if parent["status"] == "상담중" and parent.get("start_time"):
                        elapsed_sec = int((datetime.now(KST) - parent["start_time"]).total_seconds())
                        if elapsed_sec >= state["alert_seconds"]:
                            if t_key not in over_limit_teachers:
                                over_limit_teachers.append(t_key)
            
            if over_limit_teachers:
                # 2초 주기로 깜빡이는 시각 효과 모방
                if int(datetime.now(KST).timestamp()) % 2 == 0:
                    st.markdown(f"""
                        <div style="background-color: #FF8C00; color: white; padding: 10px; text-align: center; font-size: 16px; font-weight: bold; border-radius: 8px; margin-bottom: 20px;">
                            ⚠️ 시간 초과 상담 진행 중: {", ".join(over_limit_teachers)} 선생님 ⚠️
                        </div>
                    """, unsafe_allow_html=True)

            current_time = datetime.now(KST).strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
            st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
            st.write("각 선생님의 상담 상태를 직접 제어할 수 있습니다. 변경 시 전체 데이터에 즉시 반영됩니다.")
            st.markdown("---")

            # 5. 중간 관리자 화면 역시 6칸 2줄(그리드) 형식으로 일괄 표시
            for i in range(0, len(teachers_list), 6):
                cols = st.columns(6)
                for j in range(6):
                    if i + j < len(teachers_list):
                        t_key = teachers_list[i + j]
                        with cols[j]:
                            st.markdown(f"##### 🏫 {t_key}")
                            parents_list = current_data.get(t_key, [])
                            
                            for idx, parent in enumerate(parents_list):
                                status = parent["status"]
                                row_num = parent["row"]
                                start_time = parent.get("start_time")
                                
                                school_name = f"({parent['school']})" if parent.get("school") else ""
                                display_name = f"{parent['name']}{school_name}"
                                
                                # 상태 표시
                                if status == "상담중":
                                    if start_time:
                                        elapsed_sec = int((datetime.now(KST) - start_time).total_seconds())
                                        mins, secs = divmod(elapsed_sec, 60)
                                        # 초과 시 타이머 색상 빨간색으로 변경
                                        color = "red" if elapsed_sec >= state["alert_seconds"] else "green"
                                        time_badge = f"<br><span style='color:{color}; font-weight:bold;'>[상담 중] {mins:02d}:{secs:02d}</span>"
                                    else:
                                        time_badge = "<br><span style='color:green; font-weight:bold;'>[상담 중]</span>"
                                    st.markdown(f"🟢 **{display_name}** {time_badge}", unsafe_allow_html=True)
                                elif status == "상담종료":
                                    st.markdown(f"🔴 ~~{display_name}~~")
                                else:
                                    st.markdown(f"◽ {display_name}")
                                
                                # 컨트롤 버튼 (버튼 크기를 줄이기 위해 좁은 영역에 배치)
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.button("시작", key=f"adm_s_{t_key}_{idx}", disabled=(status != "대기"), use_container_width=True):
                                        parent["status"] = "상담중"
                                        parent["start_time"] = datetime.now(KST)
                                        parent["alert_triggered"] = False
                                        parent["flash_start_time"] = None
                                        threading.Thread(target=write_to_gsheets, args=(row_num, "상담중")).start()
                                        st.rerun()
                                with c2:
                                    if st.button("종료", key=f"adm_e_{t_key}_{idx}", disabled=(status != "상담중"), use_container_width=True):
                                        parent["status"] = "상담종료"
                                        threading.Thread(target=write_to_gsheets, args=(row_num, "상담종료")).start()
                                        st.rerun()
                                st.markdown("<hr style='margin: 0.5em 0;'>", unsafe_allow_html=True)

        render_admin_panel()
