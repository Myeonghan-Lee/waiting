import streamlit as st
import requests
import threading
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="2026 강서양천 진로학업 팝업 데스크 대기 현황", layout="wide")

# =======================================================
# [설정] 구글 앱스 스크립트 배포 후 복사한 웹앱 URL을 입력하세요.
# =======================================================
API_URL = "https://script.google.com/macros/s/AKfycbxIMVJhXiish8irtUha4wgMx7N-0AF4M4z8DO0j13pArg71XZFS6qCXyP53tDTTSpFi/exec"
# =======================================================

# 1. 구글 시트에서 전체 데이터를 원본 그대로 읽어오는 함수 (느림: 1~2초 소요)
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
                    "alert_triggered": False,   # 7분 30초 경고 활성화 여부 (RAM)
                    "flash_start_time": None    # 깜빡임 애니메이션 시작 시각 (RAM)
                })
            return grouped
    except Exception as e:
        st.error(f"구글 시트 읽기 실패: {e}")
    return {}

# 2. 구글 시트에 상태를 업데이트하는 함수 (느림: 1~2초 소요)
def write_to_gsheets(row, next_status):
    try:
        params = {"action": "update", "row": row, "status": next_status}
        requests.get(API_URL, params=params)
    except Exception as e:
        pass

# 3. 전역 공유 메모리 설정 (앱 시작 시 딱 한 번만 구글 시트에서 로드)
@st.cache_resource
def get_shared_state():
    return {"data": fetch_from_gsheets()}

state = get_shared_state()

# 사이드바 설정 영역
st.sidebar.title("설정")
role = st.sidebar.selectbox("모드 선택", ["📢 대기실 화면", "🛠️ 선생님용 관리 패널"])

# 구글 시트의 원본 명단을 중간에 직접 수정했을 때 사용하는 새로고침 버튼
if st.sidebar.button("🔄 구글 시트 명단 새로고침"):
    state["data"] = fetch_from_gsheets()
    st.sidebar.success("구글 시트의 최신 명단을 동기화했습니다!")
    st.rerun()

# --- 모드 A: 대기실 화면 ---
if role == "📢 대기실 화면":
    st.title("📢 2026 강서양천 진로학업 팝업 데스크 대기 현황판")
    
    # 1초마다 시계와 대기실 전체를 새로 그리는 프래그먼트
    @st.fragment(run_every=1)
    def render_waiting_room():
        # 기본 배경색 지정 (경고 후 색상 잔상 초기화용)
        st.markdown("<style>.stApp { background-color: #f8f9fa !important; }</style>", unsafe_allow_html=True)
        
        # 1. 실시간 시계 표시
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
        st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
        st.markdown("---")
        
        current_data = state["data"]
        if not current_data:
            st.warning("데이터를 불러오는 중이거나 구글 시트에 명단이 비어 있습니다.")
            return
            
        teachers = list(current_data.keys())
        cols = st.columns(min(len(teachers), 5))
        
        for idx, t_key in enumerate(teachers):
            col_idx = idx % 5
            with cols[col_idx]:
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

# --- 모드 B: 선생님용 관리 패널 ---
else:
    st.title("🛠️ 선생님용 상담 관리 패널")
    
    current_data = state["data"]
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("명단을 불러올 수 없습니다. 사이드바의 새로고침 버튼을 눌러보세요.")
    else:
        my_teacher = st.sidebar.selectbox("본인 성함을 선택하세요", teachers_list)
        
        # 1초마다 선생님 패널의 시계 및 개별 타이머를 실시간 갱신하는 프래그먼트
        @st.fragment(run_every=1)
        def render_teacher_panel():
            parents_list = current_data.get(my_teacher, [])
            
            # 깜빡임 알림 제어용 변수
            active_flash = False
            flash_phase = False  # True일 때 오렌지색 배경, False일 때 기본 배경
            
            # 1. 상담 시간 체크 및 경고 시점(7분 30초 = 450초) 계산
            for idx, parent in enumerate(parents_list):
                status = parent["status"]
                start_time = parent.get("start_time")
                
                if status == "상담중" and start_time:
                    elapsed_sec = int((datetime.now() - start_time).total_seconds())
                    
                    # 7분 30초 도달 시 깜빡임 시작 시각 최초 1회 기록
                    if elapsed_sec >= 450 and not parent.get("alert_triggered", False):
                        parent["alert_triggered"] = True
                        parent["flash_start_time"] = datetime.now()
                    
                    # 깜빡임 조건 만족 시 (애니메이션 시작 후 10초 동안 작동: 2초 간격 * 5번 = 10초)
                    if parent.get("flash_start_time"):
                        flash_elapsed = (datetime.now() - parent["flash_start_time"]).total_seconds()
                        if flash_elapsed <= 10:
                            active_flash = True
                            if int(flash_elapsed) % 2 == 0:
                                flash_phase = True
            
            # 2. 오렌지 깜빡임 화면 효과 반영
            if active_flash:
                if flash_phase:
                    st.markdown("""
                        <style>
                        .stApp {
                            background-color: #FFD5A1 !important; 
                            transition: background-color 0.2s ease;
                        }
                        </style>
                        <div style="background-color: #FF8C00; color: white; padding: 15px; text-align: center; font-size: 20px; font-weight: bold; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            ⚠️ 상담 시간 7분 30초 경과! 상담을 마무리해 주세요. ⚠️
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <style>
                        .stApp {
                            background-color: #f8f9fa !important;
                            transition: background-color 0.2s ease;
                        }
                        </style>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<style>.stApp { background-color: #f8f9fa !important; }</style>", unsafe_allow_html=True)

            # 3. 실시간 시계 표시
            current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
            st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
            st.markdown(f"##### 📌 {my_teacher} 담당 학부모 목록")
            st.write("상태 변경 시 구글 스프레드시트 및 대기실 화면에 즉시 반영됩니다.")
            
            for idx, parent in enumerate(parents_list):
                col1, col2, col3 = st.columns([2, 1, 1])
                status = parent["status"]
                row_num = parent["row"]
                start_time = parent.get("start_time")
                
                # 학교명 결합 로직 (학교명 값이 존재할 때만 괄호 추가)
                school_name = f"({parent['school']})" if parent.get("school") else ""
                display_name = f"{parent['name']}{school_name}"
                
                with col1:
                    if status == "상담중":
                        if start_time:
                            elapsed_sec = int((datetime.now() - start_time).total_seconds())
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
                        parent["start_time"] = datetime.now()
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
