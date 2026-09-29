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

ensure_android_sdk() {
  if [[ -n "${ANDROID_HOME:-}" && -d "${ANDROID_HOME}/platforms" ]]; then
    export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"
    return
  fi
  if [[ -n "${ANDROID_SDK_ROOT:-}" && -d "${ANDROID_SDK_ROOT}/platforms" ]]; then
    export ANDROID_HOME="$ANDROID_SDK_ROOT"
    return
  fi
  local candidate
  for candidate in /opt/android-sdk "${HOME}/Android/Sdk" /usr/lib/android-sdk "${ROOT}/.android-sdk"; do
    if [[ -d "${candidate}/platforms" ]]; then
      export ANDROID_HOME="$candidate"
      export ANDROID_SDK_ROOT="$candidate"
      echo "Using Android SDK at ${ANDROID_HOME}"
      return
    fi
  done
  install_android_sdk
}

install_android_sdk() {
  local dest="/opt/android-sdk"
  if [[ ! -w /opt ]]; then
    dest="${ROOT}/.android-sdk"
  fi
  mkdir -p "${dest}/cmdline-tools"
  local zip="${dest}/cmdline-tools.zip"
  echo "Installing Android command-line SDK into ${dest}"
  curl -fsSL -o "${zip}" "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  rm -rf "${dest}/cmdline-tools/latest"
  unzip -q -o "${zip}" -d "${dest}/cmdline-tools"
  mv "${dest}/cmdline-tools/cmdline-tools" "${dest}/cmdline-tools/latest"
  # `yes` exits 141 when sdkmanager closes the pipe. pipefail would fail a successful install.
  set +o pipefail
  yes | "${dest}/cmdline-tools/latest/bin/sdkmanager" --sdk_root="${dest}" "platforms;android-35" "build-tools;35.0.0" "platform-tools"
  local status=$?
  set -o pipefail
  if [[ "${status}" -ne 0 ]]; then
    exit "${status}"
  fi
  export ANDROID_HOME="${dest}"
  export ANDROID_SDK_ROOT="${dest}"
}

ensure_android_sdk
export PATH="${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/cmdline-tools/latest/bin:${PATH}"
cd android
chmod +x ./gradlew
./gradlew assembleDebug
echo "APK: $ROOT/mobile/android/app/build/outputs/apk/debug/app-debug.apk"
