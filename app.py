import os
from flask import Flask, request, render_template, jsonify
import requests
import json
from datetime import datetime, timezone
from env import NOTION

app = Flask(__name__)

# Notion API 설정
NOTION_API_KEY = NOTION.API_KEY
DATABASE_ID = NOTION.DB_ID

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_homework', methods=['POST'])
def add_homework():
    # HTML에서 보내는 데이터를 받음
    data = request.form
    print("Received data:", data)
    
    # 시스템 시간으로 업로드 시간 자동 처리 (timezone-aware UTC datetime 사용)
    upload_time = datetime.now(timezone.utc).isoformat()  # UTC 기준으로 현재 시간

    # 과제 데이터 처리
    homework_data = {
        "과제 제목": data["homework_title"],
        "학생 이름": data["student_name"],
        "반명": data["class_name"],  # 반명 추가
        "제출 여부": data["submission_status"] == 'true',
        # 제출 여부가 Yes일 경우 마감일은 None으로 처리
        "제출 마감일": data["due_date"] if data["submission_status"] == 'false' and data["due_date"] else None,
        "업로드 시간": upload_time,
        "첨부 파일": []  # 첨부파일을 처리하지 않음
    }

    # Notion API를 통해 데이터 추가
    url = f"https://api.notion.com/v1/pages"
    properties = {
        "과제 제목": {
            "title": [
                {"text": {"content": homework_data["과제 제목"]}}
            ]
        },
        "학생 이름": {
            "rich_text": [{"text": {"content": homework_data["학생 이름"]}}]
        },
        "반명": {
            "rich_text": [{"text": {"content": homework_data["반명"]}}]  # 반명 필드 추가
        },
        "제출 여부": {"checkbox": homework_data["제출 여부"]},
        # 제출 마감일이 None이면 해당 필드 아예 제거
        "제출 마감일": {"date": {"start": homework_data["제출 마감일"]}} if homework_data["제출 마감일"] else {},
        "업로드 시간": {"date": {"start": upload_time}},
        "첨부 파일": {"files": []}  # 첨부파일 필드에 빈 리스트
    }

    # 빈 필드는 아예 제외하거나 적절하게 처리합니다
    properties = {key: value for key, value in properties.items() if value}

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
    app.run(debug=True)
