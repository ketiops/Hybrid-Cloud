#!/bin/bash

version=$1

docker build . -t chromatices/api_wrapper_strato:${version}
docker run --rm -itd --name wrapper_test -p 32000:32000 chromatices/api_wrapper_strato:${version}