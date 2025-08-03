# Use a slim Python image for smaller size
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for Playwright
# This is crucial for Playwright to run headless Chrome
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libnss3 \
    libxss1 \
    libappindicator1 \
    libindicator7 \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxi6 \
    libsm6 \
    libice6 \
    libcurl4 \
    libdbus-glib-1-2 \
    libexpat1 \
    libffi7 \
    libgcrypt20 \
    libgmp10 \
    libgnutls30 \
    libgpg-error0 \
    libgssapi-krb5-2 \
    libhogweed6 \
    libidn2-0 \
    libk5crypto3 \
    libkeyutils1 \
    libkrb5-3 \
    libkrb5support0 \
    liblz4-1 \
    libnettle8 \
    libp11-kit0 \
    libpsl5 \
    librtmp1 \
    libsecret-1-0 \
    libssh2-1 \
    libssl1.1 \
    libtasn1-6 \
    libunistring2 \
    libwebp6 \
    libxml2 \
    libxslt1.1 \
    libzstd1 \
    # Add any missing Playwright dependencies if tests fail
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium for this project)
# This command is critical for Playwright to work inside Docker
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Expose the port Flask runs on
EXPOSE 5000

# Set Flask environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["flask", "run"]