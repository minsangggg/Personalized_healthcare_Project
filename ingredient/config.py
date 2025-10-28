"""
Configuration for Ingredient Pipeline
"""

# 데이터베이스 연결 설정
DB_CONFIG = {
    'host': '211.51.163.232',
    'port': 19306,
    'user': 'lgup3',
    'password': 'lgup3P@ssw0rd',  # %40으로 인코딩 필요
    'database': 'lgup3'
}

# DB 연결 문자열 생성
DB_CONNECTION_STRING = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password'].replace('@', '%40')}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Logging 설정
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR

# Table 설정
TABLE_NAME = 'ingredient'

# CSV 파일 설정
CSV_ENCODING = 'utf-8-sig'

