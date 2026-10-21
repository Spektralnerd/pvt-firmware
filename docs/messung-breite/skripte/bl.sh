#!/usr/bin/env bash
# Quality inside the band the camera can deliver (<= ~4.95 MHz): both decoded and source
# pass the same low-pass L = 720->528->720 (Lanczos) before PSNR/SSIM.
cd "$(dirname "$0")"
L='scale=528:576:flags=lanczos+accurate_rnd,scale=720:576:flags=lanczos+accurate_rnd'
for f in enc_$1_*.mkv; do
  read -r p s < <(ffmpeg -i "$f" -i "$1.mkv" -lavfi \
   "[0:v]scale=720:576:flags=lanczos+accurate_rnd,$L,format=yuv420p,split[a][b];[1:v]$L,format=yuv420p,split[c][d];[a][c]psnr;[b][d]ssim" \
   -f null - 2>&1 | awk '/PSNR y:/{for(i=1;i<=NF;i++) if($i ~ /^y:/){sub("y:","",$i); p=$i}} /SSIM Y:/{for(i=1;i<=NF;i++) if($i ~ /^Y:/){sub("Y:","",$i); s=$i}} END{print p, s}')
  echo "$f band_psnrY=$p band_ssimY=$s" | tee -a band_results.txt
done
