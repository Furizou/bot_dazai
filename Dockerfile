FROM python:3.12-alpine

WORKDIR /app

# Install a minimal ffmpeg + needed libs for building packages (if necessary)
RUN apk add --no-cache ffmpeg

# For building certain Python packages with C extensions:
# RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]