#!/bin/bash

namespace=$1

kubectl apply -n $namespace -f argo_install.yaml
kubectl delete ns $namespace