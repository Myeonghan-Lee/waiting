import streamlit as st
import requests
import threading
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="2026 강서양천 진로학업 팝업 데스크 대기 현황", layout="wide")

# =======================================================
# [설정] 구글 앱스 스크립트 배포 후 복사한 웹앱 URL을 입력하세요.
# =======================================================
API_URL = "https://script.google.com/macros/s/AKfycbzm4Ss-f8cek8aGdWyBeHeG47cma2w-Kveyv5AczfqcPslHE018yezjqHLGCLIaiB4h/exec"
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
                    "start_time": None  # 상담 시작 시각 기록용 (RAM 메모리에만 보관)
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
    st.title("📢 2026 강서양천 진로학업 팝업 데스크 대기 현황")
    
    # 1초마다 시계와 대기실 전체를 새로 그리는 프래그먼트
    @st.fragment(run_every=1)
    def render_waiting_room():
        # 1. 실시간 시계 표시 (현재 시각만 상단에 표시)
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
                        # 진행 시간 타이머를 생략하고 단순 '상담 중'으로만 표시합니다.
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
            # 1. 실시간 시계 표시
            current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
            st.markdown(f"#### 🕒 현재 시각: **{current_time}**")
            st.markdown(f"##### 📌 {my_teacher} 담당 학부모 목록")
            st.write("상태 변경 시 구글 스프레드시트 및 대기실 화면에 즉시 반영됩니다.")
            
            parents_list = current_data.get(my_teacher, [])
            
            for idx, parent in enumerate(parents_list):
                col1, col2, col3 = st.columns([2, 1, 1])
                status = parent["status"]
                row_num = parent["row"]
                start_time = parent.get("start_time")
                
                with col1:
                    if status == "상담중":
                        # 선생님 패널에서는 여전히 실시간 타이머가 활성화되어 나타납니다.
                        if start_time:
                            elapsed_sec = int((datetime.now() - start_time).total_seconds())
                            mins, secs = divmod(elapsed_sec, 60)
                            time_badge = f"<span style='color:green; font-weight:bold;'>[상담 중] {mins:02d}:{secs:02d}</span>"
                        else:
                            time_badge = "<span style='color:green; font-weight:bold;'>[상담 중]</span>"
                        st.markdown(f"🟢 **{parent['name']}** {time_badge}", unsafe_allow_html=True)
                    elif status == "상담종료":
                        st.markdown(f"🔴 ~~{parent['name']} (완료)~~")
                    else:
                        st.markdown(f"◽ {parent['name']} (대기 중)")
                        
                with col2:
                    if st.button("상담 시작", key=f"start_{my_teacher}_{idx}", disabled=(status != "대기")):
                        parent["status"] = "상담중"
                        parent["start_time"] = datetime.now()  # 타이머 시작을 위해 시작 시간 기록
                        threading.Thread(target=write_to_gsheets, args=(row_num, "상담중")).start()
                        st.rerun()
                        
                with col3:
                    if st.button("상담 종료", key=f"end_{my_teacher}_{idx}", disabled=(status != "상담중")):
                        parent["status"] = "상담종료"
                        threading.Thread(target=write_to_gsheets, args=(row_num, "상담종료")).start()
                        st.rerun()
                        
        render_teacher_panel()
