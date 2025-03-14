![Image](https://github.com/user-attachments/assets/e8442910-7b73-4f04-b642-fba14ceb9a30)

https://github.com/user-attachments/assets/3e32cbfe-f7ce-425e-8065-d6b5b2cff9a5

남은기능



| Method | Endpoint                  | Description                                   |
|--------|---------------------------|-----------------------------------------------|
| GET, POST    | `/upload-timetable`  | 시간표를 업로드 하는 기능입니다. |
| GET   | `/view-timetable`  | DB에서 시간표를 조회하는 기능입니다.             |
| GET    | `/homework/<class_name>`  | 특정 반의 학생별 숙제 제출 현황 페이지 입니다. 동적으로 관리됩니다             |
| POST | `/time_table`  | 메인화면으로서 사용됩니다. 기타부가기능을 사용할 수 있습니다.                   |
| POST, GET    | `/login`  | E2G에 접속하기 위한 Login 페이지입니다. |
| POST   | `/logout`  | 로그아웃 기능입니다.             |
| PUT    | `/view-students`  | DB에서 등록된 학생을 조회하는 기능입니다.              |
| PUT | `/add-student`  | DB에 원생을 등록하는 기능입니다.                   |
| POST, GET    | `/delete-student`  | DB에 원생을 삭제하는 기능입니다. |
| POST   | `/class/<class_name>/send-homework-reminder/`  | 숙제를 제출하지 않은 학생들에게 알림톡을 전송하는 기능입니다.      |
| PUT    | `/class/<class_name>`  | 수업 상세 정보 및 숙제 제출 현황 페이지입니다.             |
| PUT | `/class-detail`  | 학생 목록과 Notion에서 숙제 제출 여부 가져오는 기능입니다.                 |
| POST, GET    | `/add_homework`  | 스마트 과제 업로드 기능입니다. |



1. Solapi 연동
2. 독촉 문자기능 완성
3. S3버킷 용량 변경
4. 서버 이동
5. 완전히 세팅
6. 결제 정보 옴기기
7. UI 변경

8. 언제다 해?
