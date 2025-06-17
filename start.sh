#!/bin/bash

# Render.com startup script
echo "Starting Twitter Bot on Render.com..."

# Health server'ı başlat
python health_server.py &

# Ana bot uygulamasını başlat
python main.py
