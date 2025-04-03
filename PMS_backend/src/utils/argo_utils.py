import time
import datetime
import argo_workflows
from argo_workflows.api import workflow_service_api

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