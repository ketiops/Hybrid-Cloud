#!/bin/bash

nodeport=$1
namespace=$2

#customizing nodeport for argo server
python3 nodeport_change.py --port=$nodeport

# create ns & install argo workflow
kubectl create namespace $namespace
kubectl apply -f argo_cluster_resource.yaml
kubectl apply -n $namespace -f argo_install.yaml

# pipeline runner crd install
kubectl apply -f ./pipeline_runner/pipeline-runner-role.yaml -f ./pipeline_runner/pipeline-runner-rolebinding.yaml -f ./pipeline_runner/pipeline-runner-sa.yaml -n $namespace
