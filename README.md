# 模擬本地開發

##

打開cloud shell, 複製源碼
```
git clone https://github.com/cxcxc-io/gcp_from_dev_to_prod.git
```

將workspace切換成該專案資料夾, 進行開發用環境檔的追加，新建一個 .env

.env

```
# 開發時轉換
CONFIGURATION="develop"
STORAGE_EMULATOR_HOST="http://localhost:4443"

DB_HOST="localhost"
DB_SCHEMA="app1-web"
DB_USERNAME="root"
DB_PASSWORD="123456"

# GCS_BUCKET_NAME="app1-web-bucket"
GCS_BUCKET_NAME="george-and-lbh"

FLASK_RUN_HOST="0.0.0.0"
FLASK_RUN_PORT="5000"
FLASK_DEBUG="True"
```

環境安裝
```
pip3 install -r requirements.txt
```

啟用開發環境
```
docker compose up -d
```

透過網頁預覽功能，先訪問db-adminer, 預覽port為8081。

```
伺服器位置: mysqldb.cxcxc.pri 
帳號: root
密碼: 123456
```

啟用app.py，並透過網頁預覽訪問，試傳檔案
```
python3 app.py
```

上傳檔案後，透過adminer，確認資料有進入本地端的資料庫。

# 開始在本地串接Cloud Storage

切換到cloud storage管理頁面，並建立bucket，並將建立好的bucket名字 貼回.env

</br>


找到 `.env`檔案中的 `GCS_BUCKET_NAME` 更改為剛剛建立的bucket名

```
# 開發時轉換
# CONFIGURATION="develop"
# STORAGE_EMULATOR_HOST="http://localhost:4443"

DB_HOST="localhost"
DB_SCHEMA="app1-web"
DB_USERNAME="root"
DB_PASSWORD="123456"

# GCS_BUCKET_NAME="app1-web-bucket"
GCS_BUCKET_NAME="george-and-lbh"

FLASK_RUN_HOST="0.0.0.0"
FLASK_RUN_PORT="5000"
FLASK_DEBUG="True"
```

確認操作的project，打開terminal進行切換
</br>
重新啟用app.py，並透過網頁預覽訪問，試傳檔案
```
gcloud config set project YOUR-PROJECT-ID
python3 app.py
```

上傳檔案後，觀測cloud storage 的bucket內是否有檔案

# 串接雲端資料庫

切換到cloud sql，建立資料庫
```
規格選擇為沙盒
把防刪除保護刪除
由於練習，把密碼設為123456
```

把先前的開發環境完整關閉
```
docker compose down
```

啟用 cloud sql proxy，把cloud sql變成私有本機連線，並連入把表格建立好。
```
cloud_sql_proxy -instances=cxcxc-demo-2023-06-03-lbh:asia-east1:app1-db=tcp:3308
```

再開一個terminal，連入mysql
```
# 密碼輸入123456
mysql -u root -p --host 127.0.0.1 --port 3308

CREATE DATABASE `app1-web`;

CREATE TABLE `app1-web-storage` (
  `_id` int NOT NULL AUTO_INCREMENT,
  `file_name` varchar(255) NOT NULL,
  `file_url` varchar(255) NOT NULL,
  PRIMARY KEY (`_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

```

重新啟用app.py，並透過網頁預覽訪問，試傳檔案
```
python3 app.py
```

透過mysql命令，檢視資料
```
use `app1-web`;
select * from `app1-web-storage`;
```

透過console端檢查cloud storage 

# 透過GCP列管 DB User

切換到`Cloud SQL Console`，並點入該db的使用者管理介面

</br>

新增一名`user`為`cxcxc`，此用戶預設就是超級管理員，為了確保大家以後知道要變更權限

</br>

切換回mysql terminal, 為用戶進行一次代表性操作

```
GRANT ALL PRIVILEGES ON `app1-web.*` TO 'cxcxc'@'%';
```

# 將應用部屬至測試環境

## 將應用打包成Container Image

確認我們所在的Project, 將源碼打包成container image

```
gcloud config set project YOUR-PROJECT-ID
gcloud builds submit  --region asia-east1 --tag gcr.io/$GOOGLE_CLOUD_PROJECT/cxcxc-dev-to-prod:0.0.1
```

## Cloud SQL 開放測試環境的網路串接

<br/>

切換回cloud sql console，編輯該database，選用連線，指定私人ip，指定為default網路

<br/>

## 應用部屬

<br/>

### 建立 APP1 專屬的IAM Service Account

<br/>

切換到IAM Console, 選擇服務帳戶並建立，名字為
<br/>
`app1-web-sa`
<br/>

角色為
```
Storage Admin
Monitoring Metric Writer
Logs Writer
```

### 在測試環境內，建立機器

切換到Compute Console，建立機器

```
Image選擇官方預設的debian
設定防火牆開放 http
Service account 選擇為 app1-web-sa
```
### Metadata 內容值
```
# Cloud SQL相關內容
DB_HOST="DB的私有IP"
DB_SCHEMA="app1-web"
DB_USERNAME="cxcxc"
DB_PASSWORD="123456"

# Cloud Storage相關內容
GCS_BUCKET_NAME="剛剛建的bucket名"

# Flask AP應用
FLASK_RUN_HOST="0.0.0.0"
FLASK_RUN_PORT="80"
FLASK_DEBUG="False"
```

###  設定startup-script

```
#!/bin/bash

curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
service docker start

# Cloud SQL
DB_HOST=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_HOST" -H "Metadata-Flavor: Google")
DB_SCHEMA=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_SCHEMA" -H "Metadata-Flavor: Google")
DB_USERNAME=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_USERNAME" -H "Metadata-Flavor: Google")
DB_PASSWORD=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_PASSWORD" -H "Metadata-Flavor: Google")
DB_CONNECT_NAME=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_CONNECT_NAME" -H "Metadata-Flavor: Google")

# Cloud Storage
GCS_BUCKET_NAME=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/GCS_BUCKET_NAME" -H "Metadata-Flavor: Google")

# AP
FLASK_RUN_HOST=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/FLASK_RUN_HOST" -H "Metadata-Flavor: Google")
FLASK_RUN_PORT=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/FLASK_RUN_PORT" -H "Metadata-Flavor: Google")
FLASK_DEBUG=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/FLASK_DEBUG" -H "Metadata-Flavor: Google")


gcloud auth configure-docker -q
docker pull gcr.io/cxcxc-demo-2023-06-03-lbh/cxcxc-dev-to-prod:0.0.1

docker run -d -p 80:80  -e DB_HOST=$DB_HOST -e DB_SCHEMA=$DB_SCHEMA -e DB_USERNAME=$DB_USERNAME -e GCS_BUCKET_NAME=$GCS_BUCKET_NAME  -e FLASK_RUN_HOST=$FLASK_RUN_HOST -e FLASK_RUN_PORT=$FLASK_RUN_PORT -e FLASK_DEBUG=False -e DB_PASSWORD=$DB_PASSWORD --network host gcr.io/cxcxc-demo-2023-06-03-lbh/cxcxc-dev-to-prod:0.0.3
```

### 在測試環境內，測試壓力

連入機器，進行燒機

```
sudo apt-get install -y stress
nohup stress --cpu 1 --vm 1 --vm-bytes 1G --timeout 600s &
```

# 搭建生產網路環境

### 搭建VPC

### 設定防火牆依照Service account

### 串接Cloud SQL

### 開啟compute engine



