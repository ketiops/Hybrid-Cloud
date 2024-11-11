#!/bin/bash

docker build . -t api_wrapper:0.1
docker run --rm -itd --name wrapper_test -p 32000:32000 api_wrapper:0.1