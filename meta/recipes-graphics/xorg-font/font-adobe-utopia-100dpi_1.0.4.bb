DESCRIPTION = "Adobe Utopia 100 DPI fonts"

require xorg-font-common.inc

LICENSE = "Custom"
LIC_FILES_CHKSUM = "file://COPYING;md5=fa13e704b7241f60ef9105cc041b9732"

DEPENDS = "util-macros-native font-util-native"
RDEPENDS_${PN} = "encodings font-util"
RDEPENDS_${PN}_class-native = "font-util-native"

PR = "1"

SRC_URI[md5sum] = "66fb6de561648a6dce2755621d6aea17"
SRC_URI[sha256sum] = "d16f5e3f227cc6dd07a160a71f443559682dbc35f1c056a5385085aaec4fada5"

