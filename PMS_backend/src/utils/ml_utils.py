import os
import json
import yaml
import base64
import requests
from dotenv import load_dotenv
from .db_utils import get_current_ml_list, update_mldb, insert_ml_workload_info, remove_ml, get_next_mlid

load_dotenv()

def ml_post_handler(request):
    ml_workload_list = get_current_ml_list()
    print("Current ML Workload : ")
    print(ml_workload_list)
    update_mldb(ml_workload_list)
    
    # 요청 데이터에서 cluster와 base64 인코딩된 yaml 가져오기   
    request_data = request.get_json()
    cluster_idx = request_data.get("cluster", 1)  # cluster 기본값 1
    encoded_yaml = request_data.get("yaml")  # 요청에서 인코딩된 yaml 가져오기
    retry = request_data.get("retry")
    
    
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
    
    # 재시작 시나리오 -> 기존 mlid 그대로 유지
    if retry:
        mlid = remove_ml(name)
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
    #최초 실행 시나리오 -> DB 기반 mlid (keti001 ~ keti999)
    else:
        mlid = get_next_mlid()
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
        
    data_json = json.dumps(data, ensure_ascii=False)
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
    if response_data.get("code", {}) == str(10001):
        result = response_data.get("result", {})
        if result.get("success") is True:
            insert_ml_workload_info([result.get("workload")])
            return "ML Workload running was successfully."
        else:
            return f"Error: {response_data}"
    elif response_data.get("code", {}) == str(10002):
        return f"Error: Server error : {response_data['message']}"
    else:
        return f"Error: Failed to running ML Workload, status code {response.status_code}"