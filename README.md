# 🏫 실시간 진로학업 상담 대기 및 관제 시스템 (유튜브 연동 지원)

구글 스프레드시트(Google Sheets)와 연동하여 학부모 대기실 현황을 실시간으로 안내하고, 각 상담 부스의 선생님들이 스마트폰이나 태블릿으로 간편하게 상태를 제어하는 초경량 웹 애플리케이션입니다.

웹 설정 페이지에서 대기실 우측에 띄울 **유튜브 스트리밍 및 홍보 영상(최대 2개 링크 무한 루프)**을 간편하게 지정할 수 있어 대기 환경을 더욱 쾌적하게 조성할 수 있습니다.

---

## 🌟 주요 기능

1. **📢 대기실 전용 현황판 (유튜브 미디어 아트 결합)**
   * **우측 유튜브 영상 배치**: 가로 640px, 세로 360px 크기의 영상을 화면 우측 세로 중앙에 밀착 배치 (우측 브라우저 여백 `0px`)
   * **무한 루프 플레이리스트**: 링크 2개 등록 시 차례대로 끊김 없이 자동 연속 반복 재생 (음소거 정책을 우회한 자동 재생)
   * **자석식 그리드 정렬**: 상담 인원수와 무관하게 부스별 행 높이가 완벽히 수평 대칭을 이루도록 설계하여 화면 찌그러짐 방지
   * **미니멀 시계**: 대기실 상단에 소형화된 서울 표준시(KST) 시계 적용 (여백 최소화)

2. **🛠️ 선생님용 개별 상담 패널**
   * 각자의 디바이스에서 지정 부스를 선택해 원터치 제어 (`[상담 시작]`, `[상담 종료]`)
   * 상담 시작 후 흐른 시간을 표시해 주는 초 단위 정밀 실시간 타이머 작동
   * **지정 경고 시간(예: 7분 30초) 도달 시, 화면 전체가 2초 간격으로 5번 오렌지색으로 깜빡이며 자동 타이머 시각 알림**

3. **👑 중간 관리자 통합 대시보드**
   * 최대 6명의 선생님 부스를 한 화면(3열 2줄)에 모아두고 일괄 모니터링 및 즉시 상태 제어

4. **⚙️ 보안 설정 및 영구 저장 기능**
   * 비인가자의 접근을 막는 **비밀번호 인증(암호: 7854)** 체계 도입
   * 웹 설정창에서 **행사명**, **교사용 경고 시간**, **구글 웹앱 URL**, **유튜브 재생 주소 1, 2** 실시간 편집
   * 설정값이 서버 전역 로컬 파일(`settings_config.json`)에 영구 보존되어 재부팅 시에도 셋팅값 자동 유지

---

## 🚀 원스톱 구축 및 사용 가이드

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
