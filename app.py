from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
import uuid
import tempfile
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from datetime import datetime
import pytz  # 日本時間の変換用

app = FastAPI()

# .env ファイルを読み込む
# load_dotenv()

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure Blob Storageの接続情報
blob_connection_string = os.getenv('BLOB_CONNECTION_STRING')
container_name = os.getenv('BLOB_CONTAINER_NAME')

# BlobServiceClientの初期化
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
container_client = blob_service_client.get_container_client(container_name)

# データベース接続情報
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

def store_image_metadata(filename: str, blob_url: str):
    """アップロードした画像のメタデータをMySQLに保存する"""
    try:
        ssl_ca_cert_path = os.getenv('SSL_CA_CERT')  # 環境変数から取得（フルパス）
        
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            ssl_ca=ssl_ca_cert_path  # SSL CA証明書を使ったセキュア接続
        )
        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                INSERT INTO upload_images (filename, blob_url, upload_date)
                VALUES (%s, %s, %s)
            """
            # 日本時間 (JST: UTC+9) に変換
            jst = pytz.timezone('Asia/Tokyo')
            upload_date = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(query, (filename, blob_url, upload_date))
            connection.commit()
            cursor.close()
        connection.close()
    except Error as e:
        print(f"Database error: {e}")
    finally:
        if connection.is_connected():
            connection.close()

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        # 画像ファイルを一時的に保存するために、一時ディレクトリを取得
        temp_dir = tempfile.gettempdir()  # OSに依存せず、一時ファイル用のディレクトリを取得
        filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
        file_path = os.path.join(temp_dir, filename)  # 一時ファイルの保存パスを組み立て

        # ファイルを一時保存
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # BlobStorageに画像をアップロード
        blob_client = container_client.get_blob_client(filename)
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        # アップロードしたBlobのURLを取得
        blob_url = blob_client.url

        # データベースに情報を保存
        store_image_metadata(filename, blob_url)

        # 一時ファイルを削除
        os.remove(file_path)

        return {
            "message": "画像が正常にアップロードされました", 
            "filename": filename,
            "blob_url": blob_url}

    except Exception as e:
        return {"error": str(e)}

# 追加: ルートエンドポイント
# @app.get("/")
# async def root():
#     return {"message": "FastAPI is running!"}