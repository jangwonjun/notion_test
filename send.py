import requests
from env import NOTION
import json

def get_notion_data(database_id):
    NOTION_API_KEY = NOTION.API_KEY
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    response = requests.post(url, headers=headers)
    data = response.json()

    students_info = []
    for page in data["results"]:
        student_info = {}
        
        # 노션의 속성에서 값을 추출 (속성명은 실제 노션에서 확인한 이름으로 교체)
        student_info["이름"] = page["properties"].get("이름", {}).get("rich_text", [{}])[0].get("text", {}).get("content")
        student_info["진도"] = page["properties"].get("진도", {}).get("rich_text", [{}])[0].get("text", {}).get("content")
        student_info["과제"] = page["properties"].get("과제내용", {}).get("rich_text", [{}])[0].get("text", {}).get("content")
        student_info["과제수행"] = page["properties"].get("과제수행등급", {}).get("rich_text", [{}])[0].get("text", {}).get("content")
        student_info["테스트점수"] = page["properties"].get("TEST 점수", {}).get("rich_text", [{}])[0].get("text", {}).get("content")
        
        students_info.append(student_info)
    
    return students_info



def create_message(student_data):
    template = """
    안녕하세요! 노원구 No.1 수학학원 Q.E.D입니다.
    금일 학습 내용을 알려드리겠습니다.
    
    진도: {진도}
    과제: {과제}
    이전 과제수행: {과제수행}
    테스트 점수: {테스트점수}

    감사합니다!
    문의가 있다면 언제든 연락주세요!
    """
    
    message = template.format(
        진도=student_data["진도"],
        과제=student_data["과제"],
        과제수행=student_data["과제수행"],
        테스트점수=student_data["테스트점수"]
    )

    return message



# def send_bulk_sms(students_info):
#     send = []  # 학생들의 전화번호를 저장할 리스트

#     # 학생 데이터로 메시지 생성
#     for student in students_info:
#         message = create_message(student)
#         phone_number = "받는_전화번호"  # 실제 전화번호로 대체
#         send.append(phone_number)

#         data = {
#             'messages': [
#                 {
#                     'to': phone_number,
#                     'from': 'SEND.SENDNUMBER',  # 발신자 전화번호
#                     'subject': '금일 학습 내용 안내',
#                     'text': message  # 생성된 맞춤형 메시지
#                 }
#             ]
#         }

#         res = message.send_many(data)  # 여러 명에게 문자 보내기
#         print(json.dumps(json.loads(res.text), indent=2, ensure_ascii=False))  # 전송 결과 출력



DATABASE_ID = NOTION.DB_ID_CARE
students_data = get_notion_data(DATABASE_ID)




for student in students_data:
    print(student)

    message = create_message(student)
    print("생성된 메시지:")
    print(message)
    print("="*30)  
# 문자 전송
#send_bulk_sms(students_data)
