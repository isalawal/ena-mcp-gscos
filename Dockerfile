# use official Python 3.12 slim image as base
# slim keeps the image small — no unnecessary packages
FROM python:3.12-slim

# set working directory inside the container
WORKDIR /app

# copy requirements first so Docker caches this layer
# only reinstalls packages if requirements.txt changes
COPY requirements.txt .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the code
COPY . .

# tell Docker this container listens on no external port
# MCP uses stdio transport not HTTP
EXPOSE 8000

# command to run when container starts
CMD ["python", "server.py"]