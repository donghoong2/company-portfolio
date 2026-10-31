#!/usr/bin/env bash
# PPTX → 슬라이드별 PNG (시각 검수용)
# 사용법: bash scripts/preview.sh output/<slug>_portfolio.pptx
# 출력: output/preview/<파일명>/slide.NNN.png
# 임시 폴더에 렌더하고, 성공했을 때만 기존 미리보기를 교체한다 (렌더 실패 시 이전 PNG 보존)
set -euo pipefail
src="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
name="$(basename "$1" .pptx)"
dest="$(pwd)/output/preview/$name"
out="$dest.tmp.$$"
trap 'rm -rf "$out"' EXIT
mkdir -p "$out"

if command -v soffice >/dev/null 2>&1 && command -v pdftoppm >/dev/null 2>&1; then
  soffice --headless --convert-to pdf --outdir "$out" "$src" >/dev/null
  pdftoppm -png -r 80 "$out/$name.pdf" "$out/slide"
  rm -f "$out/$name.pdf"
elif [ -d "/Applications/Keynote.app" ] || mdfind "kMDItemCFBundleIdentifier == 'com.apple.Keynote'" | grep -q .; then
  osascript <<OSA
with timeout of 600 seconds
  tell application id "com.apple.Keynote"
    set d to open POSIX file "$src"
    export d to POSIX file "$out" as slide images with properties {image format:PNG, skipped slides:false}
    close d saving no
  end tell
end timeout
OSA
  i=1; for f in $(ls "$out"/*.png | sort); do mv "$f" "$out/slide.$(printf %03d $i).png"; i=$((i+1)); done
else
  echo "렌더러 없음: LibreOffice(brew install --cask libreoffice && brew install poppler) 또는 Keynote 필요" >&2
  exit 2
fi
ls "$out"/*.png >/dev/null 2>&1 || { echo "렌더 실패: PNG가 만들어지지 않았다 (기존 미리보기 유지)" >&2; exit 1; }
rm -rf "$dest" && mv "$out" "$dest"
ls "$dest"
