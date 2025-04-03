import os
from flask_cors import CORS
from dotenv import load_dotenv
from flask import Flask, request

from utils.ml_utils import ml_post_handler
from utils.resource_utils import parse_recommend
from utils.argo_utils import load_argo_info, get_workflow_info_from_instance
from utils.db_utils import update_mldb, insert_ml_workload_info, remove_ml, get_next_mlid, get_current_ml_list

# .env 파일에서 환경 변수 불러오기
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api*": {"origins": "*"}})

# 첫 번째 엔드포인트: 데이터베이스에 POST 요청 결과 저장
@app.route('/api/v1/strato', methods=['POST'])
def ml_post():
    return ml_post_handler(request)

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
    request_data = request.get_json()
    result = parse_recommend(request_data)
    try:
        return {"status": "succeeded", "items": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}    

if __name__ == '__main__':
    port = os.getenv("PYTHON_SERVER_PORT")
    app.run(host='0.0.0.0', port=port, debug=True)