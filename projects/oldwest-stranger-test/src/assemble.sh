#!/usr/bin/env bash
# Encode rendered PNG frames + final audio mix into the delivery MP4 (1280x720, 30 fps, H.264 + AAC).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p final
ffmpeg -y -v error -framerate 30 -i renders/frames/f%04d.png -i audio/final_mix.wav \
  -filter_complex "[0:v]eq=contrast=1.10:saturation=1.18:gamma=0.97,colorbalance=rs=0.03:bs=-0.03:rh=0.02:bh=-0.03,\
vignette=angle=PI/5,noise=alls=5:allf=t,fade=t=out:st=15.35:d=0.65,format=yuv420p[v]" \
  -map "[v]" -map 1:a -c:v libx264 -preset slow -crf 17 -r 30 -s 1280x720 \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest final/oldwest_stranger_test.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,sample_rate,channels \
  -show_entries format=duration -of compact final/oldwest_stranger_test.mp4
