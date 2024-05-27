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
kubectl apply \
 -f https://raw.githubusercontent.com/kubeflow/manifests/5b1256f19a728908a7245db7460c3f742b01fb1e/apps/pipeline/upstream/base/pipeline/pipeline-runner-role.yaml \
 -f https://raw.githubusercontent.com/kubeflow/manifests/5b1256f19a728908a7245db7460c3f742b01fb1e/apps/pipeline/upstream/base/pipeline/pipeline-runner-rolebinding.yaml \
 -f https://raw.githubusercontent.com/kubeflow/manifests/5b1256f19a728908a7245db7460c3f742b01fb1e/apps/pipeline/upstream/base/pipeline/pipeline-runner-sa.yaml \
 -n $namespace

