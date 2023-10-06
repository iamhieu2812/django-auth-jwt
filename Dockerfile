FROM python:3.8-slim-bullseye as base

# Install dependencies
RUN apt-get update -y && apt-get install -y \
    ca-certificates wget jq curl git nano gettext \
    chrpath iputils-ping procps shared-mime-info mime-support
RUN apt-get install -y --no-install-recommends build-essential \
    libxft-dev libfreetype6 libfreetype6-dev libfontconfig1 libfontconfig1-dev \
    libffi-dev libjpeg-dev libpq-dev libssl-dev libtiff-dev libwebp-dev zlib1g-dev
RUN apt-get install -y --no-install-recommends default-libmysqlclient-dev default-mysql-client
# Cleanup apt cache
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Multi Build from base image
FROM base
WORKDIR /app

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install Python packages
RUN pip install --upgrade pip && pip install --no-cache-dir --upgrade wheel pip setuptools
# COPY Pipfile* ./
EXPOSE 8000
COPY requirements.txt /app
RUN pip install -r requirements.txt --no-cache-dir
COPY . /app 
ENTRYPOINT ["python"] 
CMD ["manage.py", "runserver", "0.0.0.0:8000"]
