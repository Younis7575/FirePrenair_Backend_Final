#!/bin/bash
export PATH="/Users/apple/Desktop/Fireprenair-main/prenair/venv/bin:$PATH"
cd /Users/apple/Desktop/Fireprenair-main/prenair
exec python manage.py runserver 0.0.0.0:8000
