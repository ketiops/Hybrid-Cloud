import os
import json
import pymysql
import requests
from dotenv import load_dotenv

load_dotenv()

def get_db_info():
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    cursor = connection.cursor()
    table = os.getenv('TABLE_NAME')
    return connection, cursor, table

def update_mldb(json_data: list):
    if not json_data:
        print("No data received for update.")
        return
    
    connection, cursor, table = get_db_info()
    
    # 테이블 존재 여부 확인
    check_query = "SHOW TABLES LIKE %s"
    cursor.execute(check_query, (table,))
    table_exists = cursor.fetchone()

    # 테이블이 없으면 생성
    if not table_exists:
        create_table_query = f"""
        CREATE TABLE {table} (
            id VARCHAR(50),
            mlId VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255),
            namespace VARCHAR(255),
            description TEXT,
            mlStepCode JSON,  
            status VARCHAR(255),
            userId VARCHAR(255),
            clusterIdx VARCHAR(50)
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
        print(f"Table '{table}' was created.")

    # 테이블이 존재하는 경우 데이터 확인
    get_db_query = f"SELECT * FROM {table}"
    cursor.execute(get_db_query)
    result = cursor.fetchall()

    if not result:  # 테이블이 비어 있음
        print(f"There is no data on '{table}'. Insert initial information.")
        insert_ml_workload_info(json_data)

import json
import traceback

def insert_ml_workload_info(json_data: list):
    if not json_data:
        print("No data received for update.")
        return
    
    connection, cursor, table = get_db_info()

    # 현재 DB에 존재하는 mlId 목록 가져오기
    cursor.execute(f"SELECT mlId FROM {table}")
    existing_mlids = {row[0] for row in cursor.fetchall()}  # Set으로 변환

    # API 리턴값에서 새로운 mlId 목록 추출
    new_mlids = {item["mlId"] for item in json_data}

    # 📌 [수정된 로직] "진짜 삭제해야 할 mlId"만 찾기
    mlids_to_delete = existing_mlids - new_mlids  # 기존 코드 (삭제 대상)
    
    # ✅ [수정된 로직] 기존 mlId가 API에서 누락된 건지 확인하기
    mlids_to_keep = {mlId for mlId in mlids_to_delete if mlId.startswith("workload-")}  
    mlids_to_delete -= mlids_to_keep  # 삭제 목록에서 "workload-" 관련된 것은 제거
    
    if mlids_to_delete:
        try:
            delete_query = f"DELETE FROM {table} WHERE mlId IN ({','.join(['%s'] * len(mlids_to_delete))})"
            cursor.execute(delete_query, tuple(mlids_to_delete))
            print(f"Deleted old mlIds from table: {mlids_to_delete}")
        except Exception as e:
            print(f"Error deleting mlIds: {e}")
            print(traceback.format_exc())

    # 추가할 mlId 찾기 (API에는 있지만 DB에 없는 값)
    mlids_to_insert = new_mlids - existing_mlids

    insert_query = f"""
    INSERT INTO {table}
    (id, mlId, name, namespace, description, mlStepCode, status, userId, clusterIdx)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        namespace = VALUES(namespace),
        description = VALUES(description),
        mlStepCode = VALUES(mlStepCode),
        status = VALUES(status),
        userId = VALUES(userId),
        clusterIdx = VALUES(clusterIdx)
    """

    required_keys = {"id", "name", "namespace", "description", "mlStepCode", "status", "userId", "clusterIdx"}
    
    for item in json_data:
        if item["mlId"] not in mlids_to_insert:
            continue  # 이미 있는 값이면 넘어감

        missing_keys = required_keys - set(item.keys())
        if missing_keys:
            print(f"Skipping item due to missing keys: {missing_keys}")
            continue

        mlId_value = item.get("mlId", "null_mlId")
        if mlId_value is None:
            mlId_value = "null_mlId"
            print(f"mlId is null. Assigning default mlId: {mlId_value}")

        try:
            cursor.execute(insert_query, (
                item["id"],
                mlId_value,
                item["name"],
                item["namespace"],
                item["description"],
                json.dumps(item["mlStepCode"]),
                item["status"],
                item["userId"],
                item["clusterIdx"]
            ))
        except Exception as e:
            print(f"Error inserting item {item['id']}: {e}")
            print(traceback.format_exc())

    connection.commit()
    connection.close()
    
    return f"ML data updated successfully on '{table}'."

def remove_ml(name: str):
    connection, cursor, table = get_db_info()
    
    if name.split('-')[-1] == str(0):
        # existed name : ml-pipeline
        # new name : ml-pipeline-retry-0
        target_name="-".join(name.split('-')[:-2])
        print(f"target_name:{target_name}, case: name.split('-')[-1]==str(0)")
        print(f"Current name on case1 : {name}")
    else:
        # existed name : ml-pipeline-retry-1
        # new name : ml-pipeline-retry-2
        target_name= "-".join(name.split('-')[:-1]) + '-' +str(int(name.split('-')[-1])-1)
        print(f"target_name:{target_name}, case: others")
        print(f"Current name on case2 : {name}")
        
    # mlId 파싱 후 DB에 해당 데이터 삭제
    select_query = f"SELECT mlId FROM {table} WHERE name = %s"
    cursor.execute(select_query, (target_name,))
    result = cursor.fetchone()
    null_mlid= "null_mlid"
    if result:
        mlid = result[0]  # result: tuple
        delete_query = f"DELETE FROM {table} WHERE name = %s"
        cursor.execute(delete_query, (target_name,))
        connection.commit()  # DELETE 후 commit 필요

        # STRATO Workload 삭제 API 호출을 위한 metadata 파싱
        db_get_url = os.getenv('URL') + '/interface/api/v2/ml/delete'
        token = os.getenv('TOKEN')
        headers = {
            "Authorization": token,
            "accept": "*/*",
            "Content-Type": "application/json"
        }
        remove_ml_data=json.dumps({"mlId": mlid})
        
        print("To retry running ML Workload, Current ML Workload delete :")
        print(remove_ml_data)
        
        # STRATO Workload 삭제 API 호출
        response = requests.delete(db_get_url, headers=headers, data=remove_ml_data)
        response_data = response.json()

        if str(response_data.get("code", None)) == "10001":
            print(f"ML Workload retry execution successfully. ({response_data['message']})")
            print(f"Deleted ML Workload mlId : {mlid}")
            return mlid
        else:
            print(f"Error: Failed to delete ML Workload, status code {response_data['message']}")
            print(f"Return default mlid:{null_mlid}")
            return null_mlid
    else:
        print(f"Error: No ML Workload found with name '{name}'.")
        print(f"Return default mlid:{null_mlid}")
        return null_mlid

def get_next_mlid():
    connection, cursor, table = get_db_info()
    # mlId를 가져오고 가장 큰 값을 선택
    cursor.execute(f"SELECT mlId FROM {table} WHERE mlId LIKE 'keti%' ORDER BY mlId DESC LIMIT 1")
    result = cursor.fetchone()
    if result:
        # 가장 큰 mlId 값에서 숫자 부분 추출 후 1 증가
        current_num = int(result[0][4:])  # 'keti' 이후의 숫자 부분 추출
        next_num = current_num + 1
        return f'keti{next_num:03}'  # 세자리로 맞추기
    else:
        return "keti001"  # 만약 값이 없다면 keti001 반환

def get_current_ml_list():
    mlid_get_url = os.getenv('URL') + "/interface/api/v2/ml/ml/list"
    token = os.getenv('TOKEN')
    headers = {
        "Authorization": token,
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    response = requests.post(mlid_get_url, headers=headers, data=json.dumps({}))
    response_data = response.json()
    if response_data.get("code", {}) == str(10001):
        result = response_data.get("result", {})
    return result