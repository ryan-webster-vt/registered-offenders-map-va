#!/bin/bash

# Run the Docker container (detach mode)
docker run --platform linux/amd64 -d -p 9000:8080 --name lambda-local docker-image:test

# Wait a few seconds to let Lambda start
sleep 3

# Invoke the Lambda function locally
curl -s "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'

# Optionally, stop and remove the container after invocation
docker stop lambda-local
docker rm lambda-local
