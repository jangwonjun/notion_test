import os
import boto3  
from flask import Flask, request, render_template, jsonify, redirect, url_for
import requests
import json
from datetime import datetime, timezone
from env import NOTION, S3, FLASK_ENUM, SQL, SEND
import pymysql
from subprocess import run
from timetable import load_timetable
import time
from send import create_homework_reminder_message
from src.lib import message, storage
import pandas as pd


app = Flask(__name__)

NOTION_API_KEY = NOTION.API_KEY
DATABASE_ID = NOTION.DB_ID

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

def load_timetable(file_path):
    """엑셀 파일을 읽고 시간표 데이터를 DB에 저장하는 함수"""
    df = pd.read_excel(file_path)

    if isinstance(df["시간"].iloc[0], pd.Timestamp):
        df["시간"] = df["시간"].dt.strftime('%H:%M')

    # DB 연결
    connection = pymysql.connect(
        host=SQL.HOST,
        user=SQL.ID,
        password=SQL.PASSWORD,
        port=SQL.PORT,
        database=SQL.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = connection.cursor()

    for _, row in df.iterrows():
        class_name = row["수업명"]
        time_info = row["시간"]
        teacher = row["담당선생님"]
        days = row["요일"].split("/")  # 요일을 '/'로 구분하여 리스트로 변환

        for day in days:
            cursor.execute("""
                INSERT INTO timetable (class_name, start_time, day, teacher)
                VALUES (%s, %s, %s, %s)
            """, (class_name, time_info, day.strip(), teacher))

    connection.commit()
    cursor.close()
    connection.close()

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
        return [result['student_phone'] for result in results]
    else:
        return None



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
    
def load_timetable_from_db():
    """MySQL 데이터베이스에서 시간표 데이터를 가져오는 함수"""
    
    # DB 연결
    connection = pymysql.connect(
        host=SQL.HOST,
        user=SQL.ID,
        password=SQL.PASSWORD,
        port=SQL.PORT,
        database=SQL.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            # 데이터 조회 쿼리
            cursor.execute("SELECT class_name, start_time, day, teacher FROM timetable")
            # 결과 가져오기
            timetable = cursor.fetchall()
            #print("반영시간표 : ", timetable)
            return timetable
    finally:
        connection.close()


def load_timetable_from_db_for_view():
    conn = pymysql.connect(
        host=SQL.HOST,
        user=SQL.ID,
        password=SQL.PASSWORD,
        port=SQL.PORT,
        database=SQL.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    query = "SELECT subject_name, day_of_week, start_time, end_time FROM timetable"  # 시간표 데이터를 가져오는 SQL
    cursor = conn.cursor()
    cursor.execute(query)
    timetable = cursor.fetchall()
    cursor.close()
    conn.close()

    # 데이터를 딕셔너리 형태로 변환 (예: subject_name을 key로, 나머지 시간표 항목들을 값으로)
    timetable_data = [
        {"수업명": row[0], "요일": row[1], "시작시간": row[2], "종료시간": row[3]} 
        for row in timetable
    ]
    return timetable_data

def send_homework_reminder():
    """숙제를 제출하지 않은 학생들에게 문자 전송"""
    #노션에 제출조차 안한 학생들의 경우 어떻게 처리할지 고민 -> 학생이름 검색후 보내는걸로! 해결예정.

    """숙제를 제출하지 않은 학생들에게 문자 전송"""
    homework_status = get_homework_status()  # 노션에서 제출한 학생들 조회
    print("📌 숙제 상태 데이터:", homework_status)  # ✅ 노션 데이터 확인

    students = get_students()  # DB에서 학생 정보 가져오기
    print("📌 DB 학생 목록:", students)  # ✅ DB 데이터 확인

    for student in students:
        student_tuple = (student['class'], student['name'])
        
        print(f"🔍 체크 중: {student_tuple}")  # ✅ 현재 비교하는 학생 정보
        print(f"📌 해당 학생의 숙제 상태: {homework_status.get(student_tuple)}")  # ✅ 현재 상태 확인

        if homework_status.get(student_tuple, "") != "✔":  # ✅ 기본값 추가
            phone_number = get_student_phone_number(student['name'], student['class'])
            print(f"📌 핸드폰 번호 ({student['name']}):", phone_number)

            if phone_number:
                message_text = create_homework_reminder_message(student)
                data = {
                    'messages': [
                        {
                            'to': phone_number,
                            'from': SEND.SENDNUMBER,
                            'subject': '숙제 미제출 안내',
                            'text': message_text
                        }
                    ]
                }
                res = message.send_many(data)
                print(f"{student['name']}에게 숙제 미제출 알림을 전송했습니다.")
                print(json.dumps(json.loads(res.text), indent=2, ensure_ascii=False))
       
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

@app.route('/upload-timetable', methods=['GET','POST'])
def upload_timetable():
    if request.method == 'GET':
        return render_template('upload_timetable.html')  # 업로드 페이지 렌더링

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "파일이 없습니다."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "파일을 선택하세요."}), 400

    if file and file.filename.endswith('.xlsx'):
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        load_timetable(file_path)  # 엑셀 파일 로드 후 DB에 저장
        return jsonify({"status": "success", "message": "시간표 업로드 및 갱신 완료"})
    else:
        return jsonify({"status": "error", "message": "엑셀 파일만 업로드 가능합니다."}), 400
    
@app.route('/view-timetable', methods=['GET'])
def view_timetable():
    """DB에서 시간표 데이터를 조회하고 화면에 표시하는 함수"""
    # DB 연결
    connection = pymysql.connect(
        host=SQL.HOST,
        user=SQL.ID,
        password=SQL.PASSWORD,
        port=SQL.PORT,
        database=SQL.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = connection.cursor()

    # 시간표 데이터 조회
    cursor.execute("""
        SELECT class_name, start_time, day, teacher
        FROM timetable
        ORDER BY day, start_time
    """)
    timetable_data = cursor.fetchall()

    cursor.close()
    connection.close()

    # 조회된 데이터를 HTML 페이지에서 출력
    return render_template('view_timetable.html', timetable=timetable_data)


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
    timetable = load_timetable_from_db() 

    # 템플릿에 데이터 전달
    return render_template('table.html', timetable=timetable)


@app.route("/class/<class_name>")
def class_detail(class_name):
    """✅ 수업 상세 정보 및 숙제 제출 현황 페이지"""
    # 시간표 데이터 로드
    timetable = load_timetable_from_db() 

    # 수업 이름에 맞는 시간표 항목을 찾아서 상세 정보 처리
    timetable_entry = next(
        (entry for entry in timetable if entry['class_name'] == class_name), None
    )

    print("시간표",timetable_entry)
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


@app.route('/run-care-and-send', methods=['POST'])
def run_care_and_send():
    try:
        # care.py 실행
        result_care = run(['python3', 'care.py'], capture_output=True, text=True)
        if result_care.returncode != 0:
            return jsonify({"status": "error", "message": f"care.py 오류: {result_care.stderr}"})
        
        # care.py가 성공적으로 실행되었으면 send.py 실행
        result_send = run(['python3', 'send.py'], capture_output=True, text=True)
        if result_send.returncode == 0:
            return jsonify({"status": "success", "message": "전화번호 매칭 완료 후 문자 전송 완료"})
        else:
            return jsonify({"status": "error", "message": f"send.py 오류: {result_send.stderr}"})
    
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
