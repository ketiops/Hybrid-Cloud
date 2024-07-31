import os
import kfp
from kfp import dsl
from kubernetes import client as k8s_client

os.environ['PIPELINE_VERSION'] = '1.0'
os.environ['OWNER'] = 'rootmo'
__PIPELINE_NAME__ = 'sllm-pipline'
__PIPELINE_DESCRIPTION__ = 'sllm pipeline experiment for resource observation'

@dsl.pipeline(name=__PIPELINE_NAME__, description=__PIPELINE_DESCRIPTION__)
def pipeline(
    dataset_path: str = '/home/slle_pipeline/datasets',
    train_dataset_path: str = '/home/slle_pipeline/datasets/train',
    val_dataset_path: str = '/home/slle_pipeline/datasets/val',
):
    
    OWNER = os.environ['OWNER']
    VERSION = os.environ['PIPELINE_VERSION']
    nfs_source = k8s_client.V1NFSVolumeSource(path='/data/home/nfsroot/sllm_dataset',server='10.0.1.102')

    preprocess = dsl.ContainerOp(
        name = 'preprocessing alpaca datasets',
        image = f'{OWNER}/preprocess:{VERSION}',
    ).add_volume(k8s_client.V1Volume(name = 'data',nfs = nfs_source))\
    .add_volume_mount(k8s_client.V1VolumeMount(mount_path = dataset_path,name='data'))
    
    train = dsl.ContainerOp(
        name = 'training alpaca lora model',
        image = f'{OWNER}/train:{VERSION}',
    ).add_volume(k8s_client.V1Volume(name = 'data',nfs = nfs_source))\
    .add_volume_mount(k8s_client.V1VolumeMount(mount_path = train_dataset_path,name='data')).set_gpu_limit(1)
    train.after(preprocess)
    
    inference = dsl.ContainerOp(
        name = 'inferencing alpaca lora model',
        image = f'{OWNER}/inference:{VERSION}',
    ).add_volume(k8s_client.V1Volume(name = 'data',nfs = nfs_source))\
    .add_volume_mount(k8s_client.V1VolumeMount(mount_path = val_dataset_path,name='data')).set_gpu_limit(1)
    inference.after(train)
    
if __name__ == "__main__":
    import kfp.compiler as compiler
    compiler.Compiler().compile(pipeline_func=pipeline, package_path=f"./sllm-pipeline-{os.environ['PIPELINE_VERSION']}.yaml")
