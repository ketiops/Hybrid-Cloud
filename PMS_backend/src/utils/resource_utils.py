import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def parse_recommend(_dict):
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
                recommend_resources = requests.post(predict_url, headers=headers, data=json.dumps(inference_req))
                resource_req, resource_lim = recommend_resources.json()['result']['requests'], recommend_resources.json()['result']['limits']
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
                print("Current ML Workload Label: ", workload_label)
                print("Recommend Resources : \n", i['container']['resources'])
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
                print("There is no label for ML workloads. Recommend does not occur")
    return _dict