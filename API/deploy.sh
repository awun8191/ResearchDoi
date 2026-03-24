#!/bin/bash

if [ -f .env ]; then
    export $(cat .env | xargs)
    source .env
fi


SERVICE_NAME="research-api"
PROJECT_ID="researchassistant-3446d"
REGION="us-central1"

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated
