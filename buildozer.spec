[app]

title = Last Teen Standing

package.name = lastteenstanding
package.domain = org.ritik

source.dir = .

source.include_exts = py,kv,png,jpg,jpeg,atlas,wav,mp3,json,tmx,tsx,ogg

# Include asset folders
source.include_patterns = gameAsset/*

version = 1.0

requirements = python3,kivy,pillow,pytmx

orientation = landscape

fullscreen = 1

# Android settings
android.api = 34
android.minapi = 21

[buildozer]

log_level = 2
warn_on_root = 0
