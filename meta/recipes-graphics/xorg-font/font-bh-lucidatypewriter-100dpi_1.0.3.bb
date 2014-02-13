DESCRIPTION = "Bigelow & Holmes Lucida Typewriter 100 DPI fonts"

require xorg-font-common.inc

LICENSE = "Custom"
LIC_FILES_CHKSUM = "file://COPYING;md5=0d221a9cd144806cb469735cc4775939"

DEPENDS = "util-macros-native font-util-native"
RDEPENDS_${PN} = "encodings font-util"
RDEPENDS_${PN}_class-native = "font-util-native"

PR = "1"

SRC_URI[md5sum] = "c8b73a53dcefe3e8d3907d3500e484a9"
SRC_URI[sha256sum] = "62a83363c2536095fda49d260d21e0847675676e4e3415054064cbdffa641fbb"
