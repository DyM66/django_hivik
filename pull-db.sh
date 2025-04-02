#!/bin/bash

# Load environment variables from the .env file
source .env

# Check if the .env file was loaded correctly
if [ -z "$REMOTE_DATABASE_USER" ] || [ -z "$REMOTE_DATABASE_PASSWORD" ] || [ -z "$REMOTE_DATABASE_HOST" ] || [ -z "$REMOTE_DATABASE_NAME" ] || [ -z "$LOCAL_DATABASE_NAME" ] || [ -z "$LOCAL_DATABASE_USER" ] || [ -z "$LOCAL_DATABASE_PASSWORD" ] || [ -z "$LOCAL_DATABASE_HOST" ]; then
  echo "Missing environment variables in the .env file"
  exit 1
fi

# Create the database backup file
DUMP_FILE="db_backup.sql"

# Step 1: Performing the backup of the remote database
echo "Performing backup of the remote database..."

# Use the PGPASSWORD variable to pass the password automatically
docker run --rm -v $(pwd):/backup -e PGPASSWORD=$REMOTE_DATABASE_PASSWORD postgres:latest \
  pg_dump -h $REMOTE_DATABASE_HOST -U $REMOTE_DATABASE_USER -d $REMOTE_DATABASE_NAME -f /backup/$DUMP_FILE

# Check if the pg_dump command was successful
if [ $? -eq 0 ]; then
  echo "Backup completed successfully and saved as $DUMP_FILE"
else
  echo "There was an error while performing the backup of the remote database"
  exit 1
fi

# Step 2: Load the backup into the local database
echo "Loading the backup into the local database..."

docker run --rm -v $(pwd):/backup -e PGPASSWORD=$LOCAL_DATABASE_PASSWORD postgres:latest \
  psql -h host.docker.internal -U $LOCAL_DATABASE_USER -d $LOCAL_DATABASE_NAME -f /backup/$DUMP_FILE

# Check if the load was successful
if [ $? -eq 0 ]; then
  echo "Loading into the local database completed successfully."
else
  echo "There was an error while loading the backup into the local database."
  exit 1
fi

# Clean up the backup file
rm -f $DUMP_FILE

echo "Script executed successfully."
