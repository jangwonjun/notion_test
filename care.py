import pandas as pd
import pymysql
import requests
from env import SQL, NOTION

# 🔹 1. MySQL에서 학생의 전화번호를 가져오는 함수
def get_student_phone_numbers():
    conn = pymysql.connect(host=SQL.HOST, user=SQL.ID, password=SQL.PASSWORD, db=SQL.DB_NAME, charset='utf8')
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # 결과를 딕셔너리 형태로 반환

    query = "SELECT name, class, student_phone, parent_phone FROM students"
    cursor.execute(query)
    student_data = cursor.fetchall()
    
    conn.close()
    return { (row["class"], row["name"]): (row["student_phone"], row["parent_phone"]) for row in student_data }

# 🔹 2. 노션에서 학생 정보 가져오기
def get_notion_data():
    NOTION_API_KEY = NOTION.API_KEY  # 🔥 노션 API 키 입력 필요
    DATABASE_ID = NOTION.DB_ID_CARE # 🔥 노션 데이터베이스 ID 입력 필요

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    response = requests.post(url, headers=headers)
    data = response.json()
    
    students = {}  # 딕셔너리로 선언해야 반, 이름에 해당하는 id를 매핑할 수 있음
    for page in data["results"]:
        student_class = page["properties"]["반"].get("rich_text", [])
        student_name = page["properties"]["이름"].get("rich_text", [])
        
        # 학생의 반과 이름이 있을 경우에만 처리
        if student_class and student_name:
            student_class = student_class[0]["text"]["content"]
            student_name = student_name[0]["text"]["content"]
            students[(student_class, student_name)] = page["id"]  # 반, 이름 -> 노션 ID 매핑
    
    return students

# 🔹 3. 비교 후 노션에 전화번호 업데이트 (전화번호 앞에 0 추가)
def update_notion_phone_numbers(student_dict, notion_students):
    NOTION_API_KEY = NOTION.API_KEY
    
    for (student_class, student_name), page_id in notion_students.items():  # 튜플을 키로 사용하는 딕셔너리에서 순회
        # MySQL에서 학생 이름과 반에 맞는 전화번호 찾기
        if (student_class, student_name) in student_dict:
            student_phone, parent_phone = student_dict[(student_class, student_name)]
            
            # 전화번호 앞에 '0'이 없다면 '0' 추가
            if not student_phone.startswith('0'):
                student_phone = '0' + student_phone  # 0 추가
            if not parent_phone.startswith('0'):
                parent_phone = '0' + parent_phone  # 0 추가
            
            # 노션에 해당 페이지 ID 업데이트
            url = f"https://api.notion.com/v1/pages/{page_id}"  # 페이지 ID 사용
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }

            data = {
                "properties": {
                    "학생전화번호": {
                        "phone_number": student_phone
                    },
                    "학부모전화번호": {
                        "phone_number": parent_phone
                    }
                }
            }
            
            response = requests.patch(url, headers=headers, json=data)
            print(f"Updated phone numbers for {student_name} in {student_class}.")

# 🔹 4. 실행하기
student_dict = get_student_phone_numbers()  # MySQL에서 학생 정보 가져오기
notion_students = get_notion_data()  # 노션에서 학생 이름과 반 가져오기
update_notion_phone_numbers(student_dict, notion_students)  # 전화번호 업데이트

print("📌 노션 데이터 업데이트 완료!")


