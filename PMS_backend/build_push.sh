#!/bin/bash

version=$1

docker build . -t chromatices/api_wrapper_strato:${version} -f dockerfile_strato 
docker push chromatices/api_wrapper_strato:${version}