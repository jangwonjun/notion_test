import os
import boto3  
from flask import Flask, request, render_template, jsonify
import requests
import json
from datetime import datetime, timezone
from env import NOTION, S3, FLASK_ENUM
from subprocess import run

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

@app.route('/')
def index():
    """ 학생 페이지 렌더링 (과제 올리기) """
    return render_template('index.html')

@app.route('/admin')
def admin():
    """ 관리자 페이지 렌더링 """
    return render_template('main.html')

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
