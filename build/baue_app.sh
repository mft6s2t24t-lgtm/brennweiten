#!/bin/bash
# Baut dist/Brennweiten.dmg und dist/Brennweiten.zip (Apple Silicon und Intel).
# Aufruf: build/baue_app.sh [Cache-Ordner mit arm.tgz und x86.tgz]
# Für die Weitergabe mit Apple-Signatur:
#   SIGN_ID="Developer ID Application: …" BUNDLE_ID="de.deinname.brennweiten" NOTARY_PROFILE="profil" build/baue_app.sh
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$PROJECT/dist"
CACHE="${1:-$(mktemp -d)}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
VERSION="${VERSION:-1.1}"
BUNDLE_ID="${BUNDLE_ID:-local.brennweiten-tool}"
SIGN_ID="${SIGN_ID:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"
REL=https://github.com/astral-sh/python-build-standalone/releases/download/20261110
fetch() { # datei arch sha
  [ -f "$CACHE/$1" ] || curl -fsSL -o "$CACHE/$1" "$REL/cpython-3.12.16%2B20261110-$2-apple-darwin-install_only_stripped.tar.gz"
  echo "$3  $CACHE/$1" | shasum -a 256 -c --quiet
}
fetch arm.tgz aarch64 2f11b8aa3726bdbd87dd9eb76568412faddf4f47e26913fa45d6a2e424972acd
fetch x86.tgz x86_64 b78a4c479f1964ec484880bee567568266f68da102269fb93a05fe8716b45f91

A="$WORK/Brennweiten.app"; C="$A/Contents"; RT="$C/Resources/runtime"
mkdir -p "$C/MacOS" "$RT"
for arch in arm64 x86_64; do
  swiftc -O -swift-version 5 -target "$arch-apple-macos12.0" -framework Cocoa -framework WebKit \
    "$PROJECT/native/main.swift" -o "$WORK/bin-$arch"
done
lipo -create "$WORK/bin-arm64" "$WORK/bin-x86_64" -output "$C/MacOS/Brennweiten"
cp "$PROJECT/build/AppIcon.icns" "$C/Resources/"
rsync -a --exclude __pycache__ --exclude .DS_Store "$PROJECT/app/" "$C/Resources/app/"

NOTARIZED=false; [ -n "$NOTARY_PROFILE" ] && NOTARIZED=true
cat > "$C/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Brennweiten</string>
<key>CFBundleDisplayName</key><string>Brennweiten</string>
<key>CFBundleExecutable</key><string>Brennweiten</string>
<key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
<key>CFBundleIconFile</key><string>AppIcon</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>$VERSION</string>
<key>CFBundleVersion</key><string>$VERSION</string>
<key>CFBundleDevelopmentRegion</key><string>de</string>
<key>CFBundleLocalizations</key><array><string>de</string><string>en</string></array>
<key>LSMinimumSystemVersion</key><string>12.3</string>
<key>LSApplicationCategoryType</key><string>public.app-category.photography</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSPrincipalClass</key><string>NSApplication</string>
<key>BWNotarized</key><$NOTARIZED/>
<key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
<key>NSDesktopFolderUsageDescription</key><string>Brennweiten liest Fotos in den von dir gewählten Ordnern. / Brennweiten reads photos in the folders you choose.</string>
<key>NSDocumentsFolderUsageDescription</key><string>Brennweiten liest Fotos in den von dir gewählten Ordnern. / Brennweiten reads photos in the folders you choose.</string>
<key>NSDownloadsFolderUsageDescription</key><string>Brennweiten liest Fotos in den von dir gewählten Ordnern. / Brennweiten reads photos in the folders you choose.</string>
<key>NSRemovableVolumesUsageDescription</key><string>Brennweiten liest Fotos auf den von dir gewählten Laufwerken. / Brennweiten reads photos on the drives you choose.</string>
<key>NSNetworkVolumesUsageDescription</key><string>Brennweiten liest Fotos auf den von dir gewählten Netzlaufwerken. / Brennweiten reads photos on the network drives you choose.</string>
</dict></plist>
PLIST

/usr/bin/python3 - "$PROJECT" "$C/Resources" <<'PY'
import re, sys
for src, dst, dev, lang in (("LIESMICH.md", "Anleitung.txt", "## Für Entwickler", "**Deutsch** · [English](GUIDE.md)\n\n"),
                            ("GUIDE.md", "Guide.txt", "## For developers", "[Deutsch](LIESMICH.md) · **English**\n\n")):
    s = open(sys.argv[1] + "/" + src, encoding="utf-8").read().replace(lang, "")
    a = s.find(dev)
    if a >= 0:
        s = s[:a].rstrip() + "\n"
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s).replace("`", "")
    s = re.sub(r"^#+ ", "", s, flags=re.M)
    open(sys.argv[2] + "/" + dst, "w", encoding="utf-8").write(s)
PY

for pair in arm.tgz:arm64 x86.tgz:x86_64; do
  f=${pair%%:*}; a=${pair##*:}
  mkdir "$WORK/x"; tar -xzf "$CACHE/$f" -C "$WORK/x"; mv "$WORK/x/python" "$RT/python-$a"; rmdir "$WORK/x"
  L="$RT/python-$a/lib"
  rm -rf "$RT/python-$a/include" "$RT/python-$a/share" "$L/pkgconfig" "$L"/libtcl* "$L"/tcl* "$L"/tk* "$L"/itcl* "$L"/thread*
  rm -rf "$L/python3.12"/{test,idlelib,tkinter,turtledemo,ensurepip,lib2to3,pydoc_data,site-packages} "$L/python3.12"/config-*
  rm -f "$L/python3.12/lib-dynload"/_tkinter*
  mkdir "$L/python3.12/site-packages"
  find "$RT/python-$a" -name __pycache__ -type d -prune -exec rm -rf {} +
done
command -v brew >/dev/null && brew --prefix exiftool >/dev/null 2>&1 || { echo "Bitte zuerst installieren: brew install exiftool"; exit 1; }
EX="$(brew --prefix exiftool)/libexec"
mkdir -p "$RT/exiftool/lib/File"
cp "$EX/bin/exiftool" "$RT/exiftool/exiftool"
cp "$EX/lib/perl5/File/RandomAccess.pm" "$RT/exiftool/lib/File/"
rsync -a --exclude '*.pod' "$EX/lib/perl5/Image" "$RT/exiftool/lib/"
cat > "$RT/exiftool/exiftool-start" <<'SH'
#!/bin/bash
D="$(cd "$(dirname "$0")" && pwd)"
exec /usr/bin/perl -I"$D/lib" "$D/exiftool" "$@"
SH
chmod +x "$RT/exiftool/exiftool-start"
{
  cat "$PROJECT/LICENSE"
  echo; echo "=================================================="; echo
  cat "$PROJECT/THIRD_PARTY_NOTICES.md"
  for f in "$PROJECT"/THIRD_PARTY_LICENSES/*; do
    echo; echo "=================================================="
    basename "$f"
    echo "=================================================="; echo
    cat "$f"
  done
} > "$RT/LIZENZEN.txt"
chmod -R u+w "$A"

if [ -n "$SIGN_ID" ]; then
  ENT="$WORK/ent.plist"
  cat > "$ENT" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
<key>com.apple.security.cs.disable-library-validation</key><true/>
</dict></plist>
XML
  find "$RT" -type f \( -name '*.so' -o -name '*.dylib' -o -perm +111 \) -print0 | while IFS= read -r -d '' x; do
    if file "$x" | grep -q Mach-O; then
      codesign --force --timestamp --options runtime --entitlements "$ENT" --sign "$SIGN_ID" "$x"
    fi
  done
  codesign --force --timestamp --options runtime --entitlements "$ENT" --sign "$SIGN_ID" "$A"
else
  codesign --force --sign - "$C/MacOS/Brennweiten"
fi

rm -rf "$DIST"; mkdir -p "$DIST"
ditto -c -k --norsrc --noextattr --keepParent "$A" "$DIST/Brennweiten.zip"
D="$WORK/dmg"; mkdir "$D"; ditto "$A" "$D/Brennweiten.app"; ln -s /Applications "$D/Applications"
hdiutil create -quiet -fs HFS+ -volname "Brennweiten" -srcfolder "$D" -format UDZO -ov "$DIST/Brennweiten.dmg"
if [ -n "$SIGN_ID" ]; then codesign --force --timestamp --sign "$SIGN_ID" "$DIST/Brennweiten.dmg"; fi
if [ -n "$NOTARY_PROFILE" ]; then
  xcrun notarytool submit "$DIST/Brennweiten.dmg" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DIST/Brennweiten.dmg"
fi
ls -lh "$DIST"
