[app]

title = Last Teen Standing

package.name = lastteenstanding
package.domain = org.ritik

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,wav,mp3,ogg,json,tmx,tsx

source.include_patterns = gameAsset/*

version = 1.0

requirements = python3,kivy,pillow,pytmx

orientation = landscape
fullscreen = 1

android.api = 34
android.minapi = 21

# Important:
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 0
