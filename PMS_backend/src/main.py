import os
import re
import time
import json
import yaml
import base64
import random
import pymysql
import requests
import datetime
import argo_workflows
from flask_cors import CORS
from flask import Flask, request
from dotenv import load_dotenv
from argo_workflows.api import workflow_service_api

# .env 파일에서 환경 변수 불러오기
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api*": {"origins": "*"}})

def get_db_info():
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    cursor = connection.cursor()
    table=os.getenv('TABLE_NAME')
    return connection,cursor,table

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
    if response_data.get("code",{}) == str(10001):
        result = response_data.get("result",{})
    return result

def update_mldb(json_data:list):
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
            mlid VARCHAR(255) PRIMARY KEY,
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
        print(f"There is no data on '{table}'.")
    insert_ml_workload_info(json_data)


def insert_ml_workload_info(json_data:list):
    
    if not json_data:
        print("No data received for update.")
        return
    
    connection, cursor, table = get_db_info()
    
    # 데이터 삽입 쿼리
    insert_query = f"""
    INSERT INTO {table}
    (id, mlId, name, namespace, description, mlStepCode, status, userId, clusterIdx)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        id = VALUES(id),
        mlId = VALUES(mlId),
        name = VALUES(name),
        namespace = VALUES(namespace),
        description = VALUES(description),
        mlStepCode = VALUES(mlStepCode),
        status = VALUES(status),
        userId = VALUES(userId),
        clusterIdx = VALUES(clusterIdx)
    """

    # JSON 데이터 반복 삽입
    for item in json_data:
        cursor.execute(insert_query, (
            item["id"],
            item["mlId"],
            item["name"],
            item["namespace"],
            item["description"],
            json.dumps(item["mlStepCode"]),  # 리스트를 JSON 문자열로 변환하여 저장
            item["status"],
            item["userId"],
            item["clusterIdx"]
        ))

    connection.commit()
    connection.close()
    
    return f"ML data insert successfuly on '{table}'."

def remove_ml(name:str):
    connection, cursor, table = get_db_info()

    
    # mlId 파싱 후 DB에 해당 데이터 삭제
    select_query = f"SELECT mlid FROM {table} WHERE name = %s"
    cursor.execute(select_query, (name,))
    result = cursor.fetchone()
    
    if result:
        mlid = result[0] # result:tuple
        delete_query = f"DELETE FROM {table} WHERE name = %s"
        cursor.execute(delete_query, (name,))
        result = cursor.fetchone()
    
    # STRATO Workload 삭제 API 호출을 위한 metadata 파싱
    db_get_url = os.getenv('URL') + '/interface/api/v2/ml/delete'
    token = os.getenv('TOKEN')
    headers = {
        "Authorization": token,
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    
    # STRATO Workload 삭제 API 호출
    response = requests.post(db_get_url, headers=headers, data=json.dumps({
        "mlID":mlid
    }))
    response_data = response.json()
    if response_data.get("code",{}) == str(10001):
        return f"ML Workload retry execution successfully. ({response_data.get("message", {})})"
    else:
        return f"Error: Failed to communicate with the server, status code {response_data.get("message", {})}"


# MySQL 데이터베이스 연결 함수
def get_next_mlid():
    connection, cursor, table = get_db_info()

    
    # mlId를 가져오고 가장 큰 값을 선택
    cursor.execute(f"SELECT mlid FROM {table} WHERE mlid LIKE 'keti%' ORDER BY mlid DESC LIMIT 1")
    result = cursor.fetchone()
    if result:
        # 가장 큰 mlId 값에서 숫자 부분 추출 후 1 증가
        current_num = int(result[0][4:])  # 'keti' 이후의 숫자 부분 추출
        next_num = current_num + 1
        return f'keti{next_num:03}'  # 세자리로 맞추기
    else:
        return "keti001"  # 만약 값이 없다면 keti001 반환

# Argo Workflow API 불러오는 함수
def load_argo_info(argo_ip, argo_port=None):
    # 포트가 존재하지 않을 경우 경로를 직접 설정
    if argo_port == "" or argo_port is None:
        host_url = f"https://{argo_ip.rstrip('/')}/argo-server"
    else:
        host_url = f"https://{argo_ip}:{argo_port}"

    configuration = argo_workflows.Configuration(host=host_url)
    configuration.verify_ssl = False

    api_client = argo_workflows.ApiClient(configuration)
    api_instance = workflow_service_api.WorkflowServiceApi(api_client)
    return api_instance

# Argo Workflow 정보 가져오기
def get_workflow_info_from_instance(api_instance, namespace):
    workflow_list = api_instance.list_workflows(namespace, _check_return_type=False).to_dict()
    
    argo_table = {}
    if workflow_list['items']:
        for i in range(len(workflow_list['items'])):
            workflow_name = workflow_list['items'][i]['metadata']['name']
            workflow_status = workflow_list['items'][i]['status']['phase']
            target = workflow_list['items'][i]['status']['finishedAt']

            start_time = time.mktime(datetime.datetime.strptime(workflow_list['items'][i]['status']['startedAt'], '%Y-%m-%dT%H:%M:%SZ').timetuple()) 
            if target:
                end_time = time.mktime(datetime.datetime.strptime(workflow_list['items'][i]['status']['finishedAt'], '%Y-%m-%dT%H:%M:%SZ').timetuple()) 
            else:
                now = str(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
                end_time = time.mktime(datetime.datetime.strptime(now, '%Y-%m-%dT%H:%M:%SZ').timetuple())

            split_duration = str(datetime.timedelta(seconds=end_time - start_time)).split(':')
            
            # 시간 형식 조정
            if ' day' in split_duration[0]:
                days_hours = split_duration[0].split()
                days = int(days_hours[0])
                hours = int(days_hours[2]) + (days * 24)
                split_duration[0] = str(hours)
                
            split_duration = [str(int(x)) for x in split_duration]
            if split_duration[0] == '0':
                if split_duration[1] == '0':
                    workflow_duration = split_duration[2] + 's'
                else:
                    workflow_duration = split_duration[1] + 'm ' + split_duration[2] + 's'
            else:
                workflow_duration = split_duration[0] + 'h ' + split_duration[1] + 'm ' + split_duration[2] + 's'
            
            argo_table[i] = {
                'name': workflow_name,
                'status': workflow_status,
                'duration': workflow_duration
            }
    return argo_table

def parse_recommand(_dict):
    resource_list = {'cpu', 'memory', 'nvidia.com/gpu'}
    predict_url = os.getenv("RECOMMAND_SERVER")
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    for i in _dict:
        if 'container' in i.keys():
            if 'ml.workload' in i['metadata']['labels'].keys():
                workload_label = i['metadata']['labels']['ml.workload']
                inference_req = {"case" : workload_label}
                recommand_resources = requests.post(predict_url, headers=headers, data=json.dumps(inference_req))
                resource_req, resource_lim = recommand_resources.json()['result']['requests'], recommand_resources.json()['result']['limits']
                req_cpu = resource_req[0][0][0]/100
                req_mem = resource_req[0][0][1]
                lim_cpu = resource_lim[0][0][0]/100
                lim_mem = resource_lim[0][0][1]
                if 'resources' in i['container'].keys():
                    # `requests`와 `limits` 각각 처리
                    for req in i['container']['resources']:
                        current_resources = set(i['container']['resources'][req].keys())
                        missing_resources = resource_list - current_resources
                        # 누락된 리소스 처리
                        for resource in missing_resources:
                            if resource == 'nvidia.com/gpu' and workload_label != "preprocess":
                                if req == 'limits':
                                    i['container']['resources'][req]['nvidia.com/gpu'] = '1'  # 기본값 설정
                            elif resource == 'cpu':
                                i['container']['resources'][req]['cpu'] = str(round(req_cpu, 2))
                            elif resource == 'memory':
                                i['container']['resources'][req]['memory'] = str(req_mem) + 'Mi'
                        # 기존 리소스 처리
                        if req == 'requests':
                            i['container']['resources'][req].pop('nvidia.com/gpu', None)  # GPU 제거
                            if 'cpu' in i['container']['resources'][req]:
                                i['container']['resources'][req]['cpu'] = str(round(req_cpu, 2))
                            if 'memory' in i['container']['resources'][req]:
                                i['container']['resources'][req]['memory'] = str(round(req_mem,2)) + 'Mi'
                        elif req == 'limits':
                            if 'cpu' in i['container']['resources'][req]:
                                i['container']['resources'][req]['cpu'] = str(round(lim_cpu, 2))
                            if 'memory' in i['container']['resources'][req]:
                                i['container']['resources'][req]['memory'] = str(round(lim_mem,2)) + 'Mi'
                else:
                    # resources가 없는 경우 기본값 추가
                    i['container']['resources'] = {
                        'requests': {
                            'cpu': str(round(req_cpu, 2)),
                            'memory': str(req_mem) + 'Mi',
                        },
                        'limits': {
                            'cpu': str(round(lim_cpu, 2)),
                            'memory': str(lim_mem) + 'Mi',
                            'nvidia.com/gpu': '1'
                        }
                    }
                print("Current ML Workload Label: ",workload_label)
                print("Recommand Resources : \n", i['container']['resources'])
            else:
                i['container']['resources'] = {
                        'requests': {
                            'cpu': None,
                            'memory': None,
                        },
                        'limits': {
                            'cpu': None,
                            'memory': None,
                        }
                    }
                print("There is no label for ML workloads. Recommand does not occur")
    return _dict

# 첫 번째 엔드포인트: 데이터베이스에 POST 요청 결과 저장
@app.route('/api/v1/strato', methods=['POST'])
def ml_post():
    ml_workload_list = get_current_ml_list()
    update_mldb(ml_workload_list)

    # 요청 데이터에서 cluster와 base64 인코딩된 yaml 가져오기   
    request_data = request.get_json()
    cluster_idx = request_data.get("cluster", 1)  # cluster 기본값 1
    encoded_yaml = request_data.get("yaml")  # 요청에서 인코딩된 yaml 가져오기
    retry = request_data.get("retry")
    
    # MySQL에서 mlId 가져오기
    mlid = get_next_mlid()
    decoded_yaml = base64.b64decode(encoded_yaml).decode("utf-8")
    parsed_yaml = yaml.safe_load(decoded_yaml)

    # 변수 추출
    metadata = json.loads(parsed_yaml['metadata']['annotations']['pipelines.kubeflow.org/pipeline_spec'])
    name = metadata['name']
    description = metadata['description']
    userid = "jhpark"
    
    # ml.workload.id 컴포넌트 별 추가
    if 'spec' in parsed_yaml and 'templates' in parsed_yaml['spec']:
        for template in parsed_yaml['spec']['templates']:
            if 'metadata' in template:
                labels = template['metadata'].setdefault('labels', {})
                labels['ml.workload.id'] = userid  # 라벨 형식으로 추가
    
    # 수정된 YAML을 다시 base64로 인코딩
    updated_yaml = yaml.dump(parsed_yaml, sort_keys=False)
    updated_encoded_yaml = base64.b64encode(updated_yaml.encode('utf-8')).decode('utf-8')
    
    if retry:
        remove_ml(name)
        data = {
            "clusterIdx": cluster_idx,
            "description": description,
            "mlId": mlid,
            "mlStepCode": [
                "ml-step-100",
                "ml-step-200",
                "ml-step-400"
            ],
            "name": name,
            "namespace": "keti-crd",
            "userId": "jhpark",
            "yaml": updated_encoded_yaml,
            "overwrite": 1
        }

    else:
        data = {
            "clusterIdx": cluster_idx,
            "description": description,
            "mlId": mlid,
            "mlStepCode": [
                "ml-step-100",
                "ml-step-200",
                "ml-step-400"
            ],
            "name": name,
            "namespace": "keti-crd",
            "userId": "jhpark",
            "yaml": updated_encoded_yaml,
            "overwrite": 0
            }
        
    data_json = json.dumps(data,ensure_ascii=False)
    print("ML Workload data : ")
    print(data_json)
    
    token = os.getenv('TOKEN')
    headers = {
        "Authorization": token,
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    
    ml_post_url = os.getenv('URL') + '/interface/api/v2/ml/apply'
    response = requests.post(ml_post_url, headers=headers, data=data_json)
    response_data = response.json()
    print(response_data)
    if response_data.get("code",{}) == str(10001):
        result = response_data.get("result", {})
        if result.get("success") is True:
            insert_ml_workload_info([result.get("workload")])
            # metadata = json.dumps(data)  # metadata로 저장
            # save_response_to_db(mlid, encoded_yaml, metadata)
            return "ML Workload running was successfully."
        else:
            return f"Error: {response_data}"
    elif response_data.get("code",{}) == str(10002):
        return F"Error: Server error : {response_data.get("message", {})}"
    else:
        return f"Error: Failed to communicate with the server, status code {response.status_code}"

# 두 번째 엔드포인트: Argo Workflow 정보 가져오기
@app.route('/api/v1/info', methods=['GET'])
def get_workflow_info():
    argo_ip = request.args.get('ip')
    argo_port = request.args.get('port', default="30103")
    namespace = request.args.get('namespace', default='argo-test')

    if not argo_ip or not namespace:
        return {"status": "failure", "error": "IP and namespace are required query parameters."}, 400
    try:
        api_instance = load_argo_info(argo_ip, argo_port)
        workflows_info = get_workflow_info_from_instance(api_instance, namespace)
        return {"status": "succeeded", "items": workflows_info}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# 세 번째 엔드포인트: Informer Prediction
@app.route('/api/v1/predict', methods=['POST'])
def predict_resources():
    # 요청 데이터에서 cluster와 base64 인코딩된 yaml 가져오기
    request_data = request.get_json()
    result = parse_recommand(request_data)
    try:
        return {"status": "succeeded", "items": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}    
    
if __name__ == '__main__':
    port = os.getenv("PYTHON_SERVER_PORT")
    app.run(host='0.0.0.0', port=port, debug=True)