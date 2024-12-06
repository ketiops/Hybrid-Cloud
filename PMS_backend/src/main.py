import os
import re
import time
import json
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
from argo_workflows.model.io_argoproj_workflow_v1alpha1_workflow_create_request import IoArgoprojWorkflowV1alpha1WorkflowCreateRequest

# .env 파일에서 환경 변수 불러오기
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api*": {"origins": "*"}})

# MySQL 데이터베이스 연결 함수
def get_next_mlid():
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    cursor = connection.cursor()
    table=os.getenv('TABLE_NAME')
    
    # mlId를 가져오고 가장 큰 값을 선택
    cursor.execute("SELECT mlid FROM {} ORDER BY mlid DESC LIMIT 1".format(table))
    result = cursor.fetchone()
    
    if result:
        # 가장 큰 mlId 값에서 1 증가
        next_mlid = int(result[0]) + 1
        return f'{next_mlid:03}'  # 세자리로 맞추기
    else:
        return "001"  # 만약 값이 없다면 001 반환

# 데이터베이스에 response 데이터를 저장하는 함수
def save_response_to_db(mlid, yaml_data, metadata):
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    cursor = connection.cursor()
    table=os.getenv('TABLE_NAME')
    
    # 데이터베이스에 데이터 삽입
    insert_query = """
    INSERT INTO {} (mlid, yaml, data)
    VALUES (%s, %s, %s)
    """.format(table)
    
    cursor.execute(insert_query, (mlid, yaml_data, metadata))
    connection.commit()
    connection.close()

# Argo Workflow API 불러오는 함수
def load_argo_info(argo_ip, argo_port):
    configuration = argo_workflows.Configuration(host="https://" + argo_ip + ":" + argo_port)
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

def factorization_dict(_dict):
    request_set = {'limits','requests'}
    resource_list = {'cpu','memory'}
    
    for i in _dict:
        if 'container' in i.keys():
            # item.container.resources가 존재할 경우 추론 처리
            # item.container.resources가 존재할 경우 limits or requests 둘 중 하나는 반드시 있다.
            if  'resources' in i['container'].keys():
                cpu_ram = random.uniform(0.00, 0.70)
                memory_ram = random.randint(0,500)
                # limits, requests가 둘 다 있는지, 1개만 있는지 확인
                if len(request_set)==len(i['container']['resources']):
                    # request, limits 별 연산 처리를 위한 for문
                    # req : limits or requests
                    for req in i['container']['resources']:
                        # resource를 전부다 가지고 있는지?

                        if len(resource_list) == len(i['container']['resources'][req]):
                            if req=='requests':
                                result = float(i['container']['resources'][req]['cpu'])-cpu_ram
                                i['container']['resources'][req]['cpu']= str(round(result,2))
                                mem = i['container']['resources'][req]['memory']
                                nums, unit = re.findall(r'\d+|[A-Za-z]+', mem)
                                nums = int(''.join(nums))
                                if unit=='G':
                                    nums *= 1000
                                result = str(int(nums)-memory_ram)
                                i['container']['resources'][req]['memory']= result+'M'
                            else:
                                result = float(i['container']['resources'][req]['cpu'])+cpu_ram
                                i['container']['resources'][req]['cpu']= str(round(result,2))
                                mem = i['container']['resources'][req]['memory']
                                nums, unit = re.findall(r'\d+|[A-Za-z]+', mem)
                                nums = int(''.join(nums))
                                if unit=='G':
                                    nums *= 1000
                                result = str(int(nums)+memory_ram)
                                i['container']['resources'][req]['memory']= result+'M'
                        # cpu, memory중 1개만 가지고 있을 경우..
                        else:
                            ele_resources_key = [*i['container']['resources'][req]]
                            diff_resource = list(resource_list - set(ele_resources_key))[0]
                            if req=='requests':
                                # req: requests
                                if diff_resource == 'cpu':
                                    result = round(cpu_ram,2)
                                    # print(result)
                                    i['container']['resources'][req][diff_resource]= str(result)
                                    print(result, cpu_ram)
                                    print(i['container']['resources'][req])
                                    if i['container']['resources'][req]['memory'][-1]=="G":
                                        mem = i['container']['resources'][req]['memory']
                                        nums, unit = re.findall(r'\d+|[A-Za-z]+', mem)
                                        nums = int(nums)
                                        nums *= 1000
                                        i['container']['resources'][req]['memory']= str(nums)+'M'
                                else:
                                    result = str(memory_ram)
                                    i['container']['resources'][req][diff_resource]= result+'M'
                            else:
                                # req: limits
                                if diff_resource == 'cpu':
                                    result = round(cpu_ram + 1.29,2)
                                    i['container']['resources'][req][diff_resource]= str(result)
                                    print(result, cpu_ram, req)
                                    print(i['container']['resources'][req])
                                else:
                                    result = str(memory_ram)
                                    i['container']['resources'][req][diff_resource]= result+'M'
                    # print(i['container']['resources'])
                    # print('\n') 
                # limits, requests 둘 중 하나가 없을때
                else:
                    ele_request_key= [*i['container']['resources']]
                    diff_request = list(request_set - set(ele_request_key))[0]
                    i['container']['resources'][diff_request] = {'cpu' : str(round(cpu_ram,2)), 'memory': str(memory_ram)+'M'}
            # item.container.resources가 존재하지 않을 경우 처리
            # todo : 아무것도 없는 리소스들은 db에서 각 컴포넌트별 데이터셋의 평균 +- @ 값 처리
            # limits : +@, request : -@
            else:
                # cpu_ram, memory_ram 지역 변수로 할당
                cpu_ram = random.uniform(0.00, 2.00)
                memory_ram = random.randint(0, 500)
                i['container']['resources'] = {'requests': 
                                               {'cpu':str(round(cpu_ram,2)), 
                                                'memory': str(memory_ram)+'M'}, 
                                               'limits': 
                                               {'cpu': str(round(cpu_ram+ 1.18,2)) , 
                                                'memory': str(memory_ram+ 259)+'M'}}
            print(i['container']['resources'])
    return _dict

# 첫 번째 엔드포인트: 데이터베이스에 POST 요청 결과 저장
@app.route('/api/v1/strato', methods=['POST'])
def ml_post():
    url = os.getenv('URL')
    # 요청 데이터에서 cluster와 base64 인코딩된 yaml 가져오기
    request_data = request.get_json()
    cluster_idx = request_data.get("cluster", 1)  # cluster 기본값 1
    encoded_yaml = request_data.get("yaml")  # 요청에서 인코딩된 yaml 가져오기
    
    # MySQL에서 mlId 가져오기
    mlid = get_next_mlid()

    data = {
        "clusterIdx": cluster_idx,
        "description": "keti-ml-workload-test",
        "mlId": mlid,
        "mlStepCode": [
            "ml-step-100",
            "ml-step-200",
            "ml-step-400"
        ],
        "name": "keti-ml",
        "namespace": "keti-crd",
        "userId": "jhpark",
        "yaml": encoded_yaml
    }
    
    token = os.getenv('TOKEN')
    headers = {
        "Authorization": token,
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get("code") == "10001":  # 정상처리 확인
            metadata = json.dumps(data)  # metadata로 저장
            save_response_to_db(mlid, encoded_yaml, metadata)
            return "Data saved successfully."
        else:
            return f"Error: {response_data.get('message')}"
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

# Informer Prediction
@app.route('/api/v1/predict', methods=['POST'])
def predict_resources():
    url = os.getenv('URL')
    # 요청 데이터에서 cluster와 base64 인코딩된 yaml 가져오기
    request_data = request.get_json()
    # cluster_idx = request_data.get("cluster", 1)  # cluster 기본값 1
    # encoded_yaml = request_data.get("json")  # 요청에서 인코딩된 yaml 가져오기
    result = factorization_dict(request_data)
    
    try:
        return {"status": "succeeded", "items": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}    
    
if __name__ == '__main__':
    port = os.getenv("PYTHON_SERVER_PORT")
    app.run(host='0.0.0.0', port=port, debug=True)