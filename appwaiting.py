import streamlit as st
import requests

# 페이지 설정
st.set_page_config(page_title="진로학업 상담 대기 현황", layout="wide")

# =======================================================
# [설정] 구글 앱스 스크립트 배포 후 복사한 웹앱 URL을 입력하세요.
# =======================================================
API_URL = "여기에_구글_웹앱_URL을_넣으세요"
# =======================================================

# 구글 시트에서 최신 데이터를 가져온 후 선생님별로 묶어주는 함수
def load_data():
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
                    "row": item["row"],      # 구글 시트의 실제 행 위치
                    "name": item["parent"],  # 학부모 이름
                    "status": item["status"] # 상담 상태
                })
            return grouped
    except Exception as e:
        st.error(f"구글 시트에서 데이터를 불러오지 못했습니다: {e}")
    return {}

# 구글 시트의 해당 행의 상태를 업데이트하는 함수
def update_status(row, next_status):
    try:
        params = {
            "action": "update",
            "row": row,
            "status": next_status
        }
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            return True
    except Exception as e:
        st.error(f"상태를 구글 시트에 기록하지 못했습니다: {e}")
    return False

# 화면 분할용 메뉴
role = st.sidebar.selectbox("모드 선택", ["📢 대기실 화면", "🛠️ 선생님용 관리 패널"])

# --- 모드 A: 대기실 화면 ---
if role == "📢 대기실 화면":
    st.title("📢 진로학업 상담 대기 현황판 (구글 시트 연동)")
    st.write("※ 구글 스프레드시트의 원본 명단이 반영되며, 3초마다 화면이 자동 갱신됩니다.")
    
    @st.fragment(run_every=3)
    def render_waiting_room():
        current_data = load_data()
        if not current_data:
            st.warning("등록된 상담 데이터가 없거나 연결 대기 중입니다.")
            return
            
        teachers = list(current_data.keys())
        cols = st.columns(min(len(teachers), 5)) # 등록된 선생님 수에 맞게 최대 5열 생성
        
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
    
    current_data = load_data()
    teachers_list = list(current_data.keys())
    
    if not teachers_list:
        st.warning("구글 시트와 연결되지 않아 선생님 목록을 불러올 수 없습니다.")
    else:
        # 구글 시트에 있는 선생님 목록을 자동으로 인식하여 사이드바에 띄움
        my_teacher = st.sidebar.selectbox("본인 성함을 선택하세요", teachers_list)
        
        st.subheader(f"📌 {my_teacher} 담당 학부모 목록")
        st.write("상태 변경 시 구글 스프레드시트에 즉시 반영됩니다.")
        
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
                # 대기 중일 때만 상담 시작 활성화
                if st.button("상담 시작", key=f"start_{my_teacher}_{idx}", disabled=(status != "대기")):
                    if update_status(row_num, "상담중"):
                        st.rerun()
                        
            with col3:
                # 상담 중일 때만 상담 종료 활성화
                if st.button("상담 종료", key=f"end_{my_teacher}_{idx}", disabled=(status != "상담중")):
                    if update_status(row_num, "상담종료"):
                        st.rerun()
