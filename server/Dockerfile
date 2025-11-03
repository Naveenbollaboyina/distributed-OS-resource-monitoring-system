# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code into the container
COPY ./src /app/src

# Expose the port the app will run on
EXPOSE 8000

# The command to run the app is in docker-compose.yml