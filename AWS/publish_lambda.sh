#!/bin/bash
# publish_lambda.sh
# Usage: ./publish_lambda.sh <ECR_REPO_URI> <LAMBDA_FUNCTION_NAME> <IMAGE_TAG>

set -e

ECR_REPO_URI=$1  
LAMBDA_FUNCTION_NAME=$2
IMAGE_TAG=${3:-latest}

echo "Building Docker image..."
docker buildx build --platform linux/amd64 --provenance=false -t docker-image:test .

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_REPO_URI}

echo "Tagging image..."
docker tag docker-image:test ${ECR_REPO_URI}:latest

echo "Pushing image to ECR..."
docker push ${ECR_REPO_URI}:latest

echo "Updating Lambda function..."
aws lambda update-function-code \
    --function-name ${LAMBDA_FUNCTION_NAME} \
    --image-uri ${ECR_REPO_URI}:${IMAGE_TAG} \
    --publish

echo "Lambda function '${LAMBDA_FUNCTION_NAME}' updated successfully with image tag '${IMAGE_TAG}'!"
