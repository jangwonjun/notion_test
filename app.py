import os
import boto3  
from flask import Flask, request, render_template, jsonify, redirect, url_for
import requests
import json
from datetime import datetime, timezone
from env import NOTION, S3, FLASK_ENUM, SQL
import pymysql
from subprocess import run
from timetable import load_timetable

app = Flask(__name__)

NOTION_API_KEY = NOTION.API_KEY
DATABASE_ID = NOTION.DB_ID

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

AWS_ACCESS_KEY = S3.ACCESS_KEY
AWS_SECRET_KEY = S3.SECRET_KEY
S3_BUCKET_NAME = S3.NAME
S3_REGION = S3.REGION  

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=S3_REGION
)

def upload_to_s3(image):
    """ S3에 이미지를 업로드하고 URL을 반환하는 함수 """
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}"  # 파일명 변경 (타임스탬프 추가)
    
    try:
        # S3에 파일 업로드
        s3.upload_fileobj(image, S3_BUCKET_NAME, filename)  
        
        # S3 URL 생성
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{filename}"
        print(f"Image uploaded to S3: {s3_url}")
        return s3_url

    except Exception as e:
        print(f"S3 Upload Failed: {str(e)}")
        return None

def get_student_phone_number(student_name, class_name):
    """학생 이름과 반을 기준으로 전화번호 찾기"""
    connection = pymysql.connect(
        host=SQL.HOST,
        user=SQL.ID,
        password=SQL.PASSWORD,
        port=SQL.PORT,
        database=SQL.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

    cursor = connection.cursor()
    query = "SELECT student_phone FROM students WHERE name=%s AND class=%s"
    cursor.execute(query, (student_name, class_name))
    results = cursor.fetchall()
    print("전화번호",student_name,results)

    cursor.close()
    connection.close()
    
    if results:
        return [result[0] for result in results]
    else:
        return None

def send_sms(phone_number, message):
    """문자 전송 함수"""
    api_url = "https://api.solapi.com/messages/v4/send"
    payload = {
        "to": phone_number,
        "message": message
    }
    headers = {
        "Authorization": "Bearer YOUR_API_KEY"
    }
    response = requests.post(api_url, data=payload, headers=headers)
    return response.status_code == 200

def get_homework_status():
    """✅ 노션 API에서 숙제 제출 여부 가져오기"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/databases/{NOTION.DB_ID}/query"
    response = requests.post(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])

        homework_status = {}
        for entry in results:
            properties = entry.get("properties", {})
            class_name = properties.get("반명", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            student_name = properties.get("학생 이름", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            submission = properties.get("제출 여부", {}).get("checkbox", False)


            print(submission)

            # ✅ 제출 여부 체크
            homework_status[(class_name, student_name)] = "✔" if submission else "❌"

        print(homework_status)
        return homework_status
    
    else:
        print("❌ 노션 API 요청 실패:", response.status_code, response.text)
        return {}

def send_homework_reminder():
    """숙제를 제출하지 않은 학생들에게 문자 전송"""
    #노션에 제출조차 안한 학생들의 경우 어떻게 처리할지 고민 -> 학생이름 검색후 보내는걸로! 해결예정.

    homework_status = get_homework_status()  # 노션에서 제출한 학생들 조회
    print("숙제상태", homework_status)

    # DB에서 모든 학생 정보 가져오기
    students = get_students()  # DB에서 학생 정보 가져오기

    # 학생별로 숙제 제출 여부 확인 후, 문자 전송
    for student in students:
        student_tuple = (student['class'], student['name'])
        
        # 노션에 숙제 제출 여부가 없거나, 제출하지 않은 경우에 문자 전송
        if homework_status.get(student_tuple) != "✅":  # 노션에서 제출하지 않은 학생
            phone_number = get_student_phone_number(student['name'], student['class'])
            
            print("핸드폰 번호", student['name'], phone_number)
            if phone_number:
                message = f"학생 {student['name']}님, 숙제를 아직 제출하지 않았습니다. 빨리 제출해 주세요!"
                success = send_sms(phone_number, message)
                
                if success:
                    print(f"✅ {student['name']}님에게 문자 전송 완료")
                else:
                    print(f"❌ {student['name']}님에게 문자 전송 실패")
            else:
                print(f"❌ {student['name']}님의 전화번호를 찾을 수 없습니다.")

def get_students():
    """✅ MySQL에서 학생 목록 가져오기"""
    connection = pymysql.connect(
        host=SQL.HOST,
        user=SQL.ID,
        password=SQL.PASSWORD,
        port=SQL.PORT,
        database=SQL.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

    cursor = connection.cursor()
    cursor.execute("SELECT name, class FROM students")
    students = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    print(students)
    return students

@app.route('/homework/<class_name>')
def homework_status(class_name):
    """✅ 특정 반의 학생별 숙제 제출 현황 페이지"""
    students = get_students()
    homework_data = get_homework_status()

    # ✅ 해당 반의 학생 필터링
    filtered_students = [
        {"name": student["name"], "status": homework_data.get((class_name, student["name"]), "❓")}
        for student in students if student["class"] == class_name
    ]

    return render_template('homework.html', class_name=class_name, students=filtered_students)

@app.route('/')
def index():
    """ 학생 페이지 렌더링 (과제 올리기) """
    return render_template('index.html')

@app.route('/admin')
def admin():
    """ 관리자 페이지 렌더링 """
    return render_template('main.html')

@app.route('/time_table')
def time_table():
    timetable = load_timetable("timetable.xlsx")  # timetable 데이터 로드

    # 템플릿에 데이터 전달
    return render_template('table.html', timetable=timetable)


@app.route("/class/<class_name>")
def class_detail(class_name):
    """✅ 수업 상세 정보 및 숙제 제출 현황 페이지"""
    # 시간표 데이터 로드
    timetable = load_timetable("timetable.xlsx")  # 다시 데이터 로드

    # 수업 이름에 맞는 시간표 항목을 찾아서 상세 정보 처리
    timetable_entry = next(
        (entry for entry in timetable if entry['수업명'] == class_name), None
    )

    if not timetable_entry:
        return "수업을 찾을 수 없습니다.", 404  # 수업명이 없을 경우 처리

    # 해당 수업의 학생들 가져오기
    students = get_students()
    homework_data = get_homework_status()

    # 해당 반의 학생 필터링
    filtered_students = [
        {"name": student["name"], "status": homework_data.get((class_name, student["name"]), "❓")}
        for student in students if student["class"] == class_name
    ]

    # 템플릿에 데이터 전달
    return render_template('class_detail.html', 
                           class_name=class_name.replace('_', ' '), 
                           timetable_entry=timetable_entry,
                           students=filtered_students)


@app.route("/class-detail", methods=["GET", "POST"])
def class_detail2():
    # GET 요청 시: 학생 목록과 숙제 제출 여부 가져오기
    students = get_students()  # MySQL에서 학생 데이터 가져오기
    homework_status = get_homework_status()  # 노션 API에서 숙제 제출 여부 가져오기

    # 숙제 제출 여부 업데이트
    for student in students:
        student_tuple = (student['class'], student['name'])
        student['status'] = homework_status.get(student_tuple, "❌")
    
    # POST 요청 시: 숙제 미제출 학생들에게 문자 전송
    if request.method == "POST":
        send_homework_reminder()  # 숙제 미제출 학생들에게 문자 전송
        return redirect(url_for('time_table'))  # 문자 전송 후 페이지 새로고침

    return render_template("class_detail.html", students=students, class_name="반명")  # '반명'은 동적으로 변경될 수 있음


@app.route('/run-care', methods=['POST'])
def run_care():
    try:

        result = run(['python3', 'care.py'], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "전화번호 매칭 완료"})
        else:
            return jsonify({"status": "error", "message": f"care.py 오류: {result.stderr}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"오류 발생: {str(e)}"})


@app.route('/run-send', methods=['POST'])
def run_send():
    try:
        result = run(['python3', 'send.py'], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "문자 전송 완료"})
        else:
            return jsonify({"status": "error", "message": f"send.py 오류: {result.stderr}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"오류 발생: {str(e)}"})

@app.route('/add_homework', methods=['POST'])
def add_homework():
    data = request.form
    files = request.files.getlist("attachment")
    print("Received data:", data)

    upload_time = datetime.now(timezone.utc).isoformat()

    s3_urls = []
    for file in files:
        s3_url = upload_to_s3(file)
        if s3_url:
            s3_urls.append({"name": file.filename, "url": s3_url})

    # 과제 데이터 처리
    homework_data = {
        "과제 제목": data.get("homework_title", ""),
        "학생 이름": data.get("student_name", ""),
        "반명": data.get("class_name", ""),  
        "제출 여부": data.get("submission_status") == 'true',
        "제출 마감일": data.get("due_date") if data.get("submission_status") == 'false' and data.get("due_date") else None,
        "업로드 시간": upload_time,
        "첨부 파일": s3_urls
    }

    url = "https://api.notion.com/v1/pages"
    properties = {
        "과제 제목": {"title": [{"text": {"content": homework_data["과제 제목"]}}]},
        "학생 이름": {"rich_text": [{"text": {"content": homework_data["학생 이름"]}}]},
        "반명": {"rich_text": [{"text": {"content": homework_data["반명"]}}]},
        "제출 여부": {"checkbox": homework_data["제출 여부"]},
        "업로드 시간": {"date": {"start": upload_time}}
    }

    if homework_data["제출 마감일"]:
        properties["제출 마감일"] = {"date": {"start": homework_data["제출 마감일"]}}

    if s3_urls:
        properties["첨부 파일"] = {
            "files": [{"name": img["name"], "external": {"url": img["url"]}} for img in s3_urls]
        }

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    }

    response = requests.post(url, headers=HEADERS, data=json.dumps(payload))

    if response.status_code == 200:
        return jsonify({"status": "success", "message": "Homework added to Notion."})
    else:
        return jsonify({"status": "error", "message": response.text})

if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=FLASK_ENUM.PORT)
