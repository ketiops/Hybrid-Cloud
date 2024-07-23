## Resource Stress Pipeline
---

- Resource별 스트레스 부하 테스트 파이프라인 설계 저장소

### 파일 세부 설명
```
├── Dockerfile : 스트레스 부하 테스트 컨테이너 생성용 도커파일
├── pipeline.py : 스트레스 부하 테스트 파이프라인 설계 파일
├── requirements.txt : 스트레스 부하 테스트에 필요한 파이썬 패키지 목록
└──src
    ├── main.py : 스트레스 테스트 트리거 소스코드
    ├── pystress.py : Python CPU 스트레스 패키지 수정 소스코드 (수정사유 : python2 기준 작성)
    └── gpu_stress.py : GPU 테스트 소스코드
```

- main.py 사용 예시
```
$ python main.py --time 3 --cpu_stress True --memory_stress True --disk_stress True --network_stress True --network_mode preprocess
```

- main.py 인자 설명
```
time : 각 테스트별 소모시간 (분단위)
[cpu, memory, gpu, disk, network]_stress : 각 리소스 별 스트레스 시행 여부 (기본값 : False)
cpu_num : cpu 부하 테스트시 사용할 cpu 코어 갯수 (기본값 12)
mem_amount : RAM 부하 테스트시 사용할 메모리 총 양 (기본값 2000mb)
size_mb : Disk I/O 테스트시 사용할 더미 데이터 크기 (기본값 500mb)
net_url : Network I/O 테스트에 사용할 서버 주소 (기본값 http://localhost)
net_port : Network I/O 테스트에 사용할 서버 포트번호 (기본값 5000)
network_mode : Network I/O 테스트시 Preprocess / inference 중 모드 선택하여 데이터 전송량 결정(기본값 preprocess)
```

- 네트워크 테스트 용 Flask Server 예시코드
```
import argparse
from flask import Flask, request, jsonify

parser = argparse.ArgumentParser(description="Workload Stress Test")
parser.add_argument("--mode",type=str,default='preprocess',help="Decision Test Mode")
parser.add_argument("--port",type=int,default=5000,help="Define Traffic API Port")
args = parser.parse_args()

app = Flask(__name__)

@app.route('/post', methods=['POST'])
def large_post():
    data = request.data
    print(f"Received {len(data)} bytes")
    return jsonify({"status": "success", "received_bytes": len(data)})

@app.route('/get', methods=['GET'])
def large_get():
    if args.mode=="preprocess":
        large_data = 'x' * 10**9  # 10MB 데이터
    else:
        large_data = 'x' * 10**6
    return large_data

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=args.port)
```
- Network I/O 테스트 시행시, 위 Flask 서버를 외부에 열어준 후 main.py의 --net_url, --net_port 인자값 입력후 테스트 진행 필요
- K8s 사용 예시 (Argo workflow 환경 필요)

```
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: resource-stress-workload-4-
  annotations:
    pipelines.kubeflow.org/kfp_sdk_version: 1.8.22
    pipelines.kubeflow.org/pipeline_compilation_time: '2024-06-11.47:09:21.456227'
    pipelines.kubeflow.org/pipeline_spec: '{"description": "resource-stress-test", "name": "resource-stress-workload"}'
  labels:
    pipelines.kubeflow.org/kfp_sdk_version: 1.8.22
spec:
  entrypoint: resource-stress-workload-4
  templates:
  - name: resource-stress-workload
    container:
      command: ["python3"]
      args: ["main.py", "--time", "1", "--cpu_stress", "True", "--memory_stress", "True"]
      image: chromatices/resource_stress:1.4
    metadata:
      labels:
        pipelines.kubeflow.org/kfp_sdk_version: 1.8.22
        pipelines.kubeflow.org/pipeline-sdk-type: kfp
        pipelines.kubeflow.org/enable_caching: "true"
  - name: resource-stress-workload-2
    container:
      command: ["python3"]
      args: ["main.py", "--time", "1", "--gpu_stress", "True"]
      image: chromatices/resource_stress:1.4
      resources:
        limits: {nvidia.com/gpu: '2'}
    metadata:
      labels:
        pipelines.kubeflow.org/kfp_sdk_version: 1.8.22
        pipelines.kubeflow.org/pipeline-sdk-type: kfp
        pipelines.kubeflow.org/enable_caching: "true"
  - name: resource-stress-workload-3
    container:
      command: ["python3"]
      args: ["main.py", "--time", "1", "--cpu_stress", "True", "--memory_stress", "True", "--gpu_stress", "True"]
      image: chromatices/resource_stress:1.4
      resources:
        limits: {nvidia.com/gpu: '1'}
    metadata:
      labels:
        pipelines.kubeflow.org/kfp_sdk_version: 1.8.22
        pipelines.kubeflow.org/pipeline-sdk-type: kfp
        pipelines.kubeflow.org/enable_caching: "true"
  - name: resource-stress-workload-4
    dag:
      tasks:
      - name: resource-stress-workload
        template: resource-stress-workload
      - name: resource-stress-workload-2
        template: resource-stress-workload-2
        dependencies: [resource-stress-workload]
      - name: resource-stress-workload-3
        template: resource-stress-workload-3
        dependencies: [resource-stress-workload-2]
  arguments:
    parameters: []
  serviceAccountName: pipeline-runner
```