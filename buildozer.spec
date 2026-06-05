[app]

title = Last Teen Standing
package.name = lastteenstanding
package.domain = org.ritik

icon.filename = gameAsset/icon.png
presplash.filename = gameAsset/presplash.png

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,wav,mp3,json,tmx,tsx

version = 1.0

requirements = python3,kivy,pillow,pytmx

orientation = landscape
fullscreen = 1

android.api = 33
android.minapi = 24

android.sdk = 34
android.ndk = 25b

android.accept_sdk_license = True

android.archs = arm64-v8a,armeabi-v7a

android.permissions = INTERNET,VIBRATE,WAKE_LOCK

source.exclude_dirs = .git,.github,__pycache__,bin,.buildozer

[buildozer]

warn_on_root = 0
log_level = 2
