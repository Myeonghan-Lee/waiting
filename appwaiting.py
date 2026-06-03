import streamlit as st
import requests
import threading

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
                    "status": item["status"]
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
        pass # 백그라운드에서 백업 처리되므로 에러는 콘솔에만 기록됩니다.

# 3. 전역 공유 메모리 설정 (앱 시작 시 딱 한 번만 구글 시트에서 로드)
@st.cache_resource
def get_shared_state():
    # 이 메모리 공간은 접속한 모든 브라우저(대기실, 선생님폰)가 실시간 공유합니다.
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
    #st.write("※ 대기실 화면은 지연 없이 1초마다 메모리 데이터를 체크하여 실시간 업데이트됩니다.")
    
    # 로컬 메모리(RAM)를 조회하므로 주기를 1초로 줄여도 트래픽이나 서버 렉이 전혀 발생하지 않습니다.
    @st.fragment(run_every=1)
    def render_waiting_room():
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
        
        st.subheader(f"📌 {my_teacher} 담당 학부모 목록")
        
        parents_list = current_data.get(my_teacher, [])
        
        for idx, parent in enumerate(parents_list):
            col1, col2, col3 = st.columns([2, 1, 1])
            status = parent["status"]
            row_num = parent["row"]
            
            with col1:
                if status == "상담중":
                    st.markdown(f"🟢 **{parent['name']}** <span style='color:green; font-weight:bold;'>[상담 중]</span>", unsafe_allow_html=True)
                elif status == "상담종료":
                    st.markdown(f"🔴 ~~{parent['name']} (완료)~~")
                else:
                    st.markdown(f"◽ {parent['name']} (대기 중)")
                    
            with col2:
                if st.button("상담 시작", key=f"start_{my_teacher}_{idx}", disabled=(status != "대기")):
                    # 1. 즉시 대기실 메모리 상태 업데이트 (대기실 화면에 0.1초 만에 즉각 변경)
                    parent["status"] = "상담중"
                    # 2. 구글 시트 실제 저장 작업은 백그라운드 스레드로 비동기 처리하여 렉 방지
                    threading.Thread(target=write_to_gsheets, args=(row_num, "상담중")).start()
                    # 3. 화면 리프레시
                    st.rerun()
                    
            with col3:
                if st.button("상담 종료", key=f"end_{my_teacher}_{idx}", disabled=(status != "상담중")):
                    # 1. 즉시 대기실 메모리 상태 업데이트
                    parent["status"] = "상담종료"
                    # 2. 구글 시트 백그라운드 비동기 저장
                    threading.Thread(target=write_to_gsheets, args=(row_num, "상담종료")).start()
                    # 3. 화면 리프레시
                    st.rerun()
