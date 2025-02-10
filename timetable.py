import pandas as pd

def load_timetable(file_path="timetable.xlsx"):
    """엑셀 데이터를 불러와 시간표 데이터를 생성"""
    
    df = pd.read_excel(file_path)

    # 📌 '시간' 열이 datetime 객체로 되어 있다면 문자열로 변환
    if isinstance(df["시간"].iloc[0], pd.Timestamp):
        df["시간"] = df["시간"].dt.strftime('%H:%M')  # 'HH:MM' 형식으로 변환
    
    timetable = []
    for _, row in df.iterrows():
        class_name = row["수업명"]
        time_info = row["시간"]  # 시간은 이제 하나의 시작 시간만 있음
        teacher = row["담당선생님"]
        
        # 📌 요일을 '/'로 구분하여 리스트로 만듦
        days = row["요일"].split("/")  # '/'로 구분된 요일 리스트

        # 📌 시작 시간만 추출
        start_time = time_info  # 이제 시간은 이미 시작 시간만 있음

        # 📌 각 수업 정보를 리스트에 저장
        for day in days:
            timetable.append({
                "수업명": class_name,
                "수업시간": start_time,
                "요일": day,
                "선생님": teacher
            })

    return timetable
