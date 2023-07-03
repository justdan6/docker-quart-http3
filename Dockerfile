FROM python:3.10-alpine

# Create a user
RUN adduser -D quart
# Set working directory for the purpose of this Dockerfile
WORKDIR /home/quart

# Copy requirements to the app root
COPY requirements.txt ./
RUN apk add --no-cache --virtual .build-deps \
  openssl \
  gcc \
  musl-dev \
  bsd-compat-headers \
  libffi-dev \
  openssl-dev
  
# Create a virtual environment and install the dependecies
RUN openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 -keyout key.pem -out cert.pem -subj "/C=US/ST=VA/L=DC/O=OrgName/OU=IT Department/CN=example.com"
RUN pip install --no-cache-dir -r requirements.txt --upgrade && \
  chown -R quart:quart ./

#RUN openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Copy the app into our user root
COPY src /home/quart/
# Make our entrypoint executable

EXPOSE 8080 8443

# Set the user
USER quart
# Set the entrypoint


#ENTRYPOINT ["sh", "./boot.sh"]
CMD ["hypercorn", "--config", "hypercorn.toml", "app:app"]