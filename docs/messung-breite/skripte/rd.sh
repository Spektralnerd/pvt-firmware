#!/usr/bin/env bash
# Rate-distortion comparison 720x576i vs 528x576i with x264 restricted to MG1264-like tools
# (Main, CAVLC, no B-frames, 2 refs, GOP 50, interlaced). Quality measured at 720x576 against the source.
set -euo pipefail
S="$(dirname "$0")"; cd "$S"
X264='interlaced=1:tff=1:cabac=0:bframes=0:ref=2:keyint=50:min-keyint=50:scenecut=0'
enc() { # src width kbps
  local src=$1 w=$2 kb=$3 out="enc_${1%.mkv}_${2}_${3}.mkv" vf
  if [[ $w == 720 ]]; then vf="setsar=16/15"; else vf="scale=${w}:576:flags=lanczos+accurate_rnd,setsar=$((16*720)):$((15*w))"; fi
  ffmpeg -v error -y -i "$src" -vf "$vf" -c:v libx264 -preset veryfast -profile:v main -b:v ${kb}k \
    -pass 1 -passlogfile "pl_${out%.mkv}" -x264-params "$X264" -an -f null -
  ffmpeg -v error -y -i "$src" -vf "$vf" -c:v libx264 -preset veryfast -profile:v main -b:v ${kb}k \
    -pass 2 -passlogfile "pl_${out%.mkv}" -x264-params "$X264" -an "$out"
  rm -f pl_${out%.mkv}*
  local rate psnr ssim
  rate=$(ffprobe -v error -show_entries format=duration,size -of csv=p=0 "$out" | awk -F, '{printf "%.0f", $2*8/$1/1000}')
  read -r psnr ssim < <(ffmpeg -i "$out" -i "$src" -lavfi \
    "[0:v]scale=720:576:flags=lanczos+accurate_rnd,format=yuv420p,split[a][b];[1:v]format=yuv420p,split[c][d];[a][c]psnr;[b][d]ssim" \
    -f null - 2>&1 | awk '/PSNR y:/{for(i=1;i<=NF;i++) if($i ~ /^y:/){sub("y:","",$i); p=$i}} /SSIM Y:/{for(i=1;i<=NF;i++) if($i ~ /^Y:/){sub("Y:","",$i); s=$i}} END{print p, s}')
  echo "$src $w $kb real=${rate}k psnrY=$psnr ssimY=$ssim" | tee -a results.txt
}
for src in srcA.mkv srcB.mkv; do
  for kb in 4000 4500 5000; do enc $src 720 $kb; done
  for kb in 3000 3500 4000 4500 5000; do enc $src 528 $kb; done
done
