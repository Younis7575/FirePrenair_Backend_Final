#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export DJANGO_SETTINGS_MODULE=prenair.settings
export IMAGEIO_FFMPEG_EXE="/opt/homebrew/bin/ffmpeg"
cd /Users/apple/Desktop/Fireprenair-main/prenair
exec /Users/apple/Desktop/Fireprenair-main/prenair/venv/bin/python manage.py runserver 0.0.0.0:8000
