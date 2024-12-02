#!/bin/bash

namespace=$1

kubectl delete -n $namespace -f argo_install.yaml
kubectl delete ns $namespace
