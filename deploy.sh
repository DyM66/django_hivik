#!/bin/bash

# Set the server details
SERVER="ubuntu@got.serport.co"
REMOTE_PATH="/home/ubuntu/got/django_hivik"
LOCAL_PATH="/c/Users/medin/Desktop/Dylan/django_hivik"
cd "$LOCAL_PATH"
git add .
git commit -m "$(date +"%Y-%m-%d %H:%M:%S")"
git push
# ssh -i GOT-SERPORT.pem "$SERVER" "cd '$REMOTE_PATH' && git pull"
ssh -i  ~/.ssh/GOT-SERPORT.pem "$SERVER" "cd '$REMOTE_PATH' && git pull"
