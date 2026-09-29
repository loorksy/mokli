#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"
npm install
npm run build
cd "$ROOT/mobile"
npm install
if [[ ! -d android ]]; then
  npx cap add android
fi
npx cap sync android
if [[ -z "${ANDROID_HOME:-}" && -z "${ANDROID_SDK_ROOT:-}" ]]; then
  echo "Android SDK is not installed. Set ANDROID_HOME, then re-run scripts/build_apk.sh."
  exit 1
fi
cd android
chmod +x ./gradlew
./gradlew assembleDebug
echo "APK: $ROOT/mobile/android/app/build/outputs/apk/debug/app-debug.apk"
