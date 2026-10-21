#!/usr/bin/env bash
# Control: source shifted by 2 px / 2 lines (breaks the MG's MB/transform grid for BOTH paths),
# then the same 720 vs 528 comparison as rd.sh, quality full-band and in-band (<= 4.95 MHz).
set -euo pipefail
cd "$(dirname "$0")"
X264='interlaced=1:tff=1:cabac=0:bframes=0:ref=2:keyint=50:min-keyint=50:scenecut=0'
L='scale=528:576:flags=lanczos+accurate_rnd,scale=720:576:flags=lanczos+accurate_rnd'
for s in srcA srcB; do
  [[ -f ${s}s.mkv ]] || ffmpeg -v error -y -i $s.mkv -vf "crop=718:574:2:2,pad=720:576:0:0,setsar=16/15" -c:v ffv1 -level 3 ${s}s.mkv
done
enc() { local src=$1 w=$2 kb=$3 out="ctl_${1}_${2}_${3}.mkv" vf
  if [[ $w == 720 ]]; then vf="setsar=16/15"; else vf="scale=${w}:576:flags=lanczos+accurate_rnd,setsar=$((16*720)):$((15*w))"; fi
  for p in 1 2; do
    ffmpeg -v error -y -i "${src}s.mkv" -vf "$vf" -c:v libx264 -preset veryfast -profile:v main -b:v ${kb}k \
      -pass $p -passlogfile "pl_${out%.mkv}" -x264-params "$X264" -an $( [[ $p == 1 ]] && echo "-f null -" || echo "$out" )
  done; rm -f pl_${out%.mkv}*
  read -r p s < <(ffmpeg -i "$out" -i "${src}s.mkv" -lavfi \
   "[0:v]scale=720:576:flags=lanczos+accurate_rnd,format=yuv420p,split[a][b];[1:v]format=yuv420p,split[c][d];[a][c]psnr;[b][d]ssim" \
   -f null - 2>&1 | awk '/PSNR y:/{for(i=1;i<=NF;i++) if($i ~ /^y:/){sub("y:","",$i); p=$i}} /SSIM Y:/{for(i=1;i<=NF;i++) if($i ~ /^Y:/){sub("Y:","",$i); s=$i}} END{print p, s}')
  read -r bp bs < <(ffmpeg -i "$out" -i "${src}s.mkv" -lavfi \
   "[0:v]scale=720:576:flags=lanczos+accurate_rnd,$L,format=yuv420p,split[a][b];[1:v]$L,format=yuv420p,split[c][d];[a][c]psnr;[b][d]ssim" \
   -f null - 2>&1 | awk '/PSNR y:/{for(i=1;i<=NF;i++) if($i ~ /^y:/){sub("y:","",$i); p=$i}} /SSIM Y:/{for(i=1;i<=NF;i++) if($i ~ /^Y:/){sub("Y:","",$i); s=$i}} END{print p, s}')
  echo "$src $w $kb full=$p/$s band=$bp/$bs" | tee -a ctl_results.txt
}
rm -f ctl_results.txt
for src in srcA srcB; do
  for kb in 4000 4500 5000; do enc $src 720 $kb; done
  for kb in 3500 4000 4500 5000; do enc $src 528 $kb; done
done
echo DONE >> ctl_results.txt
