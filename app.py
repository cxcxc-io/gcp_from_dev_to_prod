from google.auth.credentials import AnonymousCredentials
from google.cloud import storage
from flask import Flask, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
load_dotenv()

# 載入環境變數
if os.getenv("CONFIGURATION") != "develop":
    print("建立生產用客戶端")
    client= storage.Client() 
else:
        # 指定 gcs-emulator host
    print("確認模擬環境端點")
    print(os.getenv("STORAGE_EMULATOR_HOST"))
    print("建立模擬用客戶端")
    client = storage.Client(
        # credentials=AnonymousCredentials(),
        project="test",
        client_options={'api_endpoint': os.getenv("STORAGE_EMULATOR_HOST")}
    )

app = Flask(__name__)


# 資料庫 URI 資訊
DB_USERNAME = os.getenv("DB_USERNAME")
print(DB_USERNAME)
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_SCHEMA = os.getenv("DB_SCHEMA")
# print(f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_SCHEMA}')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_SCHEMA}'
db = SQLAlchemy(app)

# 設定資料表物件
class File(db.Model):
    __tablename__ = 'app1-web-storage'
    _id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    file_name = db.Column(db.String(255), index=True)
    file_url = db.Column(db.String(255))

# 若無資料庫與表格，則建立
# db.create_all()

# 檢測bucket是否存在，若無
bucket_name=os.getenv("GCS_BUCKET_NAME")
print(f"目前要操作的bucket為 {os.getenv('GCS_BUCKET_NAME')}")



def store_file_in_gcs(file):

    print("connect "+os.getenv("GCS_BUCKET_NAME"))
    
    bucket = client.get_bucket(os.getenv("GCS_BUCKET_NAME"))
    # 讀取檔案
    print("指定檔案")
    blob = bucket.blob(file.filename)
    print("上傳檔案")
    blob.upload_from_string(
        file.read(),
        content_type=file.content_type
    )

    url = blob.public_url

    return url

def store_in_db(file_name, url):
    file = File(file_name=file_name, file_url=url)
    db.session.add(file)
    db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        print("接收到用戶傳來的POST")
        file = request.files['file']
        print("解析封包內容")
        if file:
            print("檔案名為"+file.filename)
            file_name = file.filename
            print(file_name)
            url = store_file_in_gcs(file)
            print("已將檔案上傳到cloud storage")
            store_in_db(file_name, url)

            return redirect(url_for('upload_file', file_name=file_name))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


app.run(host=os.getenv("FLASK_RUN_HOST", "0.0.0.0"), port=int(os.getenv("FLASK_RUN_PORT", 8082)), debug=bool(os.getenv("FLASK_DEBUG", True)))