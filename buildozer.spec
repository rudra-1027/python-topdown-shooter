[app]

title = Last Teen Standing

package.name = lastteenstanding
package.domain = org.ritik

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,wav,mp3,json,tmx,txt

version = 1.0

requirements = python3,kivy,pillow,pytmx,pygame

orientation = landscape

fullscreen = 1

# Android
android.api = 35
android.minapi = 24
android.ndk = 27b

# Use latest stable build tools
android.sdk = 35

# Permissions
android.permissions = INTERNET,VIBRATE,WAKE_LOCK

# Assets
presplash.filename = gameAsset/icon/presplash.png
icon.filename = gameAsset/icon/icon.png

# Keep all assets
source.exclude_dirs = .git,.github,bin,.buildozer,__pycache__

# Android entrypoint
android.entrypoint = org.kivy.android.PythonActivity

# Better memory
android.gradle_dependencies =

# Architecture
android.archs = arm64-v8a,armeabi-v7a

# Audio
android.enable_androidx = True

# Logging
log_level = 2

# App behavior
android.allow_backup = True

[buildozer]

warn_on_root = 0

log_level = 2
