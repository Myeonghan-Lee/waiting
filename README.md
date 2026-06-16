# 🏫 실시간 상담 대기 및 관제 시스템

구글 스프레드시트(Google Sheets)와 연동하여 학부모 대기실 현황을 실시간으로 안내하고, 각 상담 부스의 선생님들이 개별 스마트폰이나 태블릿으로 간편하게 상태를 제어할 수 있는 가볍고 안정적인 웹 애플리케이션입니다.

개인 컴퓨터에 파이썬(Python)을 전혀 설치하지 않고도 **GitHub**와 **Streamlit Community Cloud**를 활용하여 웹상에서 즉시 배포 및 무료로 운영하실 수 있습니다.

---

## 🌟 주요 기능

1. **📢 대기실 전용 현황판**
   * 대기실 빔프로젝터/TV 맞춤형 레이아웃 (6열 2줄 배치의 넓고 직관적인 구성)
   * 서울 표준시(KST) 기준 초 단위 실시간 디지털시계 표시
   * 각 부스별 학부모 대기 상태 실시간 업데이트 (0.1초 반응성)
   * 대기실 화면에는 불필요한 상담 소요 시간이 표시되지 않아 대기자의 피로감 최소화

2. **🛠️ 선생님용 개별 상담 패널**
   * 각자의 스마트폰/태블릿으로 지정 부스를 선택해 원터치 제어 (`[상담 시작]`, `[상담 종료]` 버튼)
   * 상담 시작 후 흐른 시간을 표시해 주는 초 단위 정밀 실시간 타이머 작동
   * **지정 경고 시간(예: 7분 30초) 도달 시, 화면 전체가 2초 간격으로 5번 오렌지색으로 깜빡이며 자동 타이머 알림**

3. **👑 중간 관리자 통합 대시보드**
   * 최대 6명의 선생님 부스를 한 화면(3열 2줄)에 모아두고 일괄 모니터링 및 대신 제어 가능

4. **⚙️ 보안 설정 및 영구 저장 기능**
   * 비인가자의 접근을 막는 **비밀번호 인증(암호: 7854)** 체계 도입
   * 웹 설정창에서 **행사명**, **교사용 경고 임계 시간**, **구글 앱스 스크립트 URL** 실시간 편집
   * 설정값이 서버 메모리 및 전역 로컬 파일(`settings_config.json`)에 보존되어 재부팅 시에도 세팅 값 자동 유지

---

## 🚀 원스톱 구축 및 사용 가이드

본 시스템은 **3단계** 설정만으로 빠르게 구축할 수 있습니다.

### 1단계: 구글 스프레드시트 및 앱스 스크립트 세팅

1. 구글 드라이브에서 **새 스프레드시트**를 만듭니다.
2. 첫 번째 탭의 이름을 반드시 **`상담명단`**으로 수정합니다.
3. 시트의 **1행(A1~D1)**에 아래와 같이 머리글을 입력하고 명단을 작성합니다.
   * **A1**: `선생님` | **B1**: `학부모` | **C1**: `상담상태` | **D1**: `학교명`
   * *작성 예시:* A2에 `1번 선생님`, B2에 `홍길동 학부모`, C2에 `대기`, D2에 `한국고등학교` 입력
4. 상단 메뉴의 **[확장 프로그램] ➡️ [Apps Script]**를 클릭합니다.
5. 기존 기본 코드를 지우고 아래의 **구글 앱스 스크립트 코드**를 붙여넣습니다.

```javascript
function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  if (e && e.parameter && e.parameter.action === 'update') {
    var row = parseInt(e.parameter.row);
    var status = e.parameter.status;
    sheet.getRange(row, 3).setValue(status);
    return ContentService.createTextOutput(JSON.stringify({result: "success"}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var data = sheet.getDataRange().getValues();
  var result = [];
  for (var i = 1; i < data.length; i++) {
    result.push({
      row: i + 1,
      teacher: data[i][0],
      parent: data[i][1],
      status: data[i][2],
      school: data[i][3] || ""
    });
  }
  return ContentService.createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}
