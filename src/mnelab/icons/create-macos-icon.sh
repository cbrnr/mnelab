#!/bin/bash

cd "mnelab-adaptive.iconset"

LIGHT_SRC="mnelab-iOS-Default-1024x1024@1x.png"
DARK_SRC="mnelab-iOS-Dark-1024x1024@1x.png"

echo "Generating light icons..."
sips -z 16 16 "$LIGHT_SRC" --out icon_16x16.png
sips -z 32 32 "$LIGHT_SRC" --out icon_16x16@2x.png
sips -z 32 32 "$LIGHT_SRC" --out icon_32x32.png
sips -z 64 64 "$LIGHT_SRC" --out icon_32x32@2x.png
sips -z 128 128 "$LIGHT_SRC" --out icon_128x128.png
sips -z 256 256 "$LIGHT_SRC" --out icon_128x128@2x.png
sips -z 256 256 "$LIGHT_SRC" --out icon_256x256.png
sips -z 512 512 "$LIGHT_SRC" --out icon_256x256@2x.png
sips -z 512 512 "$LIGHT_SRC" --out icon_512x512.png
sips -z 1024 1024 "$LIGHT_SRC" --out icon_512x512@2x.png

echo "Generating dark icons..."
sips -z 16 16 "$DARK_SRC" --out icon_16x16~dark.png
sips -z 32 32 "$DARK_SRC" --out icon_16x16@2x~dark.png
sips -z 32 32 "$DARK_SRC" --out icon_32x32~dark.png
sips -z 64 64 "$DARK_SRC" --out icon_32x32@2x~dark.png
sips -z 128 128 "$DARK_SRC" --out icon_128x128~dark.png
sips -z 256 256 "$DARK_SRC" --out icon_128x128@2x~dark.png
sips -z 256 256 "$DARK_SRC" --out icon_256x256~dark.png
sips -z 512 512 "$DARK_SRC" --out icon_256x256@2x~dark.png
sips -z 512 512 "$DARK_SRC" --out icon_512x512~dark.png
sips -z 1024 1024 "$DARK_SRC" --out icon_512x512@2x~dark.png

cd ..
echo "Converting to .icns..."
iconutil -c icns mnelab-macos.iconset -o mnelab-macos.icns
