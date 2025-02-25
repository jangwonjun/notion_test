import pandas as pd
import pymysql
from env import SQL

# MySQL 연결 설정
def get_db_connection():
    connection = pymysql.connect(
        host=SQL.HOST,
        user=SQL.ID,
        password=SQL.PASSWORD,
        port=SQL.PORT,
        database=SQL.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

def load_timetable(file_path="timetable.xlsx"):
    """엑셀 데이터를 불러와 시간표 데이터를 DB에 저장 또는 갱신"""
    
    df = pd.read_excel(file_path)

    # '시간' 열이 datetime 객체로 되어 있다면 문자열로 변환
    if isinstance(df["시간"].iloc[0], pd.Timestamp):
        df["시간"] = df["시간"].dt.strftime('%H:%M')  # 'HH:MM' 형식으로 변환
    
    timetable = []
    for _, row in df.iterrows():
        class_name = row["수업명"]
        time_info = row["시간"]  # 시간은 이제 하나의 시작 시간만 있음
        teacher = row["담당선생님"]
        
        # 요일을 '/'로 구분하여 리스트로 만듦
        days = row["요일"].split("/")  # '/'로 구분된 요일 리스트

        # 시작 시간만 추출
        start_time = time_info  # 이제 시간은 이미 시작 시간만 있음

        # 각 수업 정보를 리스트에 저장
        for day in days:
            timetable.append({
                "수업명": class_name,
                "수업시간": start_time,
                "요일": day,
                "선생님": teacher
            })

    # DB에 저장
    connection = get_db_connection()
    cursor = connection.cursor()

    for entry in timetable:
        # 기존 데이터가 있으면 갱신, 없으면 추가
        cursor.execute("""
            INSERT INTO timetable (class_name, start_time, day, teacher)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            start_time = VALUES(start_time), teacher = VALUES(teacher)
        """, (entry["수업명"], entry["수업시간"], entry["요일"], entry["선생님"]))

    connection.commit()  # 커밋하여 변경 사항을 DB에 반영
    cursor.close()
    connection.close()
