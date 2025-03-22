from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
import uuid
import tempfile
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

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

# SSL証明書の取得
SSL_CA_CERT = os.getenv("SSL_CA_CERT")
if not SSL_CA_CERT:
    raise ValueError(":x: SSL_CA_CERT が設定されていません！")

# SSL証明書の一時ファイル作成
def create_ssl_cert_tempfile():
    pem_content = SSL_CA_CERT.replace("\\n", "\n").replace("\\", "")
    temp_pem = tempfile.NamedTemporaryFile(delete=False, suffix=".pem", mode="w")
    temp_pem.write(pem_content)
    temp_pem.close()
    return temp_pem.name

SSL_CA_PATH = create_ssl_cert_tempfile()

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

        # 一時ファイルを削除
        os.remove(file_path)

        return {"message": "画像が正常にアップロードされました", "filename": filename}

    except Exception as e:
        return {"error": str(e)}

# 追加: ルートエンドポイント
# @app.get("/")
# async def root():
#     return {"message": "FastAPI is running!"}
