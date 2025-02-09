import pandas as pd
import pymysql
from env import SQL
import numpy as np

#학생들 Information 삽입 자동화

df = pd.read_excel("sewonmath.xlsx")


conn = pymysql.connect(host=SQL.HOST, user=SQL.ID, password=SQL.PASSWORD, db=SQL.DB_NAME, charset='utf8')
cursor = conn.cursor()

df = df.replace({np.nan: None})

for _, row in df.iterrows():
    sql = "INSERT INTO students (name, class, student_phone, parent_phone) VALUES (%s, %s, %s, %s)"
    cursor.execute(sql, (row['이름'], row['반'], row['학생전화번호'], row['부모님전화번호']))

conn.commit()
conn.close()
