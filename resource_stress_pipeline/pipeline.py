import os
from kfp.v2 import dsl


os.environ['KF_PIPELINE_VERSION']='1.5'
__PIPELINE_NAME__ = "resource-stress-workload"
__PIPELINE_DESCRIPTION__ = "resource-stress-test"


@dsl.pipeline(name=__PIPELINE_NAME__, description=__PIPELINE_DESCRIPTION__)
def pipeline():
    VERSIlON = os.environ['KF_PIPELINE_VERSION']
    sllm_component1 = dsl.ContainerOp(
        name='resource-stress-workload1',
        image=f'chromatices/resource_stress:{VERSIlON}',
        command='python3',
        arguments=['main.py', '--time', '5', '--cpu_stress', 'True', '--memory_stress', 'True', '--disk_stress','True','--network_stress','True',
                   '--mem_amount','600','--size_mb','100','--net_url','http://localhost','--net_port','30001','--network_mode','preprocess']
    ).add_pod_label("ML.workload","preprocess")
    
    sllm_component2 = dsl.ContainerOp(
        name='resource-stress-workload2',
        image=f'chromatices/resource_stress:{VERSIlON}',
        command='python3',
        arguments=['main.py' ,'--time' ,'40', '--gpu_stress', 'True','--cpu_stress','True']
    ).set_gpu_limit("1").after(sllm_component1).add_pod_label("ML.workload","train")
    
    sllm_component3 = dsl.ContainerOp(
        name='resource-stress-workload3',
        image=f'chromatices/resource_stress:{VERSIlON}',
        command='python3',
        arguments=['main.py' ,'--time', '5', '--cpu_stress', 'True', '--gpu_stress', 'True',
                   '--network_stress','True','--net_url','http://localhost','--net_port','30001','--network_mode','preprocess']
    ).set_gpu_limit("1").after(sllm_component2).add_pod_label("ML.workload","inference")
    
if __name__ == "__main__":
    import kfp.compiler as compiler
    compiler.Compiler().compile(pipeline,
                                f"./stress-test-{os.environ['KF_PIPELINE_VERSION']}.yaml")