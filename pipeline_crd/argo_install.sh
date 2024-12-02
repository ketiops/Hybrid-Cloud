#!/bin/bash

nodeport=$1
namespace=$2

# create ns & install argo workflow
kubectl create namespace $namespace

# namespace & nodeport apply on argo_cluster_resource_tem.yaml & argo_install_tmp.yaml
export NAMESPACE=$namespace
export NODEPORT=$nodeport
envsubst < argo_cluster_resource.yaml > argo_cluster_resource_tmp.yaml
envsubst < argo_install.yaml > argo_install_tmp.yaml

kubectl apply -f argo_cluster_resource_tmp.yaml
kubectl apply -n $namespace -f argo_install_tmp.yaml
rm argo_cluster_resource_tmp.yaml argo_install_tmp.yaml

# pipeline runner crd install
kubectl apply -f ./pipeline_runner/pipeline-runner-role.yaml -f ./pipeline_runner/pipeline-runner-rolebinding.yaml -f ./pipeline_runner/pipeline-runner-sa.yaml -n $namespace