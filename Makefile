# Air75 Split: rebuild everything from the Python sources in cad/.
#   make            models, checks, drawings, docs and the 3D viewer
#   make renders    the README images (needs node, Playwright and ffmpeg)
PY ?= python3

.PHONY: all firmware-src models check images docs viewer renders clean

all: models check images docs viewer

firmware-src:                      ## keymap, shield and OLED data for firmware/zmk-config
	cd cad && $(PY) gen_zmk.py

models: firmware-src               ## STL + STEP for every part, wire routes
	cd cad && $(PY) layout.py > /dev/null && $(PY) build.py && $(PY) routing.py

check:                             ## geometry, printability, STEP, screens (C vs JavaScript)
	cd cad && $(PY) verify.py && $(PY) check_step.py && $(PY) oled_check.py

images:                            ## top views, wiring sheets, thickness section
	cd cad && $(PY) drawings.py && $(PY) wiring.py && $(PY) profile.py

docs:                              ## README.md and docs/BUILD.md
	cd cad && $(PY) guide.py

viewer:                            ## viewer/index.html
	cd viewer && $(PY) build_viewer.py

renders: viewer                    ## docs/images/render_*.jpg and turntable.gif
	node viewer/render.js

clean:
	rm -rf build cad/__pycache__ viewer/__pycache__
