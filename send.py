import requests
from env import NOTION, SEND
from src.lib import message, storage
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

        # 노션 속성에서 데이터 추출
        student_info["이름"] = page["properties"].get("이름", {}).get("title", [{}])[0].get("text", {}).get("content", "")
        student_info["진도"] = page["properties"].get("진도", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
        student_info["과제"] = page["properties"].get("과제내용", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
        student_info["과제수행"] = page["properties"].get("과제수행등급", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
        student_info["테스트점수"] = page["properties"].get("TEST 점수", {}).get("number", "")

        # 학생 및 학부모 전화번호 가져오기
        student_info["학생전화번호"] = page["properties"].get("학생전화번호", {}).get("phone_number", "")
        student_info["학부모전화번호"] = page["properties"].get("학부모전화번호", {}).get("phone_number", "")

        students_info.append(student_info)
    
    return students_info

def create_homework_reminder_message(student_data):
    """숙제 독촉 문자 생성"""
    template = """
안녕하세요! 노원구 No.1 수학학원 Q.E.D입니다.

{이름} 학생이 아직 숙제를 제출하지 않았어요! 

얼른 제출해주세요! 😊
궁금한 점이 있다면 언제든 문의 주세요.

감사합니다!
    """

    message = template.format(
        이름=student_data["name"]
    )

    return message

def create_message(student_data):
    template = """
안녕하세요! 노원구 No.1 수학학원 Q.E.D입니다.
금일 학습 내용을 알려드리겠습니다.

학생: {이름}
진도: {진도}
과제: {과제}
이전 과제수행: {과제수행}
테스트 점수: {테스트점수}

감사합니다!
문의가 있다면 언제든 연락주세요!
    """

    message = template.format(
        이름=student_data["이름"],
        진도=student_data["진도"],
        과제=student_data["과제"],
        과제수행=student_data["과제수행"],
        테스트점수=student_data["테스트점수"]
    )

    return message

if __name__ == '__main__':
    DATABASE_ID = NOTION.DB_ID_CARE
    students_data = get_notion_data(DATABASE_ID)

    for student in students_data:
        message_text = create_message(student)

        # 전송할 번호 리스트 (학생 + 학부모)
        recipients = [student["학생전화번호"], student["학부모전화번호"]]
        recipients = [num for num in recipients if num]  # 빈 값 제거

        if recipients:
            data = {
                'messages': [
                    {
                        'to': number,
                        'from': SEND.SENDNUMBER,
                        'subject': '금일 학습 안내',
                        'text': message_text
                    } for number in recipients
                ]
            }

            res = message.send_many(data)
            print(f"{student['이름']}의 학습 내용을 {recipients}에게 성공적으로 전송했습니다.")
            print(json.dumps(json.loads(res.text), indent=2, ensure_ascii=False))
