[app]

title = Last Teen Standing

package.name = lastteenstanding
package.domain = org.ritik

source.dir = .

source.include_exts = py,kv,png,jpg,jpeg,atlas,wav,mp3,json,tmx

source.exclude_dirs = .git,.github,__pycache__,bin,.buildozer

version = 1.0

requirements = python3==3.11.6,kivy==2.3.0,pillow,pytmx,pygame==2.5.2

orientation = landscape
fullscreen = 1

android.api = 33
android.minapi = 24

android.ndk = 25b

android.archs = arm64-v8a

android.permissions = INTERNET,VIBRATE,WAKE_LOCK

android.accept_sdk_license = True

# Uncomment when files exist
# icon.filename = gameAsset/icon/icon.png
# presplash.filename = gameAsset/icon/presplash.png

# Optional
android.allow_backup = True

[buildozer]

warn_on_root = 0
log_level = 2
