# Animated OLED screens (src/air75_oled). The C renderer is checked against the viewer by cad/oled_check.py.
if(CONFIG_AIR75_OLED_SCREEN)
  zephyr_library_named(air75_oled)
  zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)
  zephyr_library_include_directories(src/air75_oled)
  zephyr_library_sources(src/air75_oled/render.c src/air75_oled/status_screen.c)
endif()
