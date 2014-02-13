DESCRIPTION = "Bitstream 100 DPI fonts"

require xorg-font-common.inc

LICENSE = "Custom"
LIC_FILES_CHKSUM = "file://COPYING;md5=30330812324ff9d9bd9ea645bb944427"

DEPENDS = "util-macros-native font-util-native"
RDEPENDS_${PN} = "encodings font-util"
RDEPENDS_${PN}_class-native = "font-util-native"

PR = "1"

SRC_URI[md5sum] = "6b223a54b15ecbd5a1bc52312ad790d8"
SRC_URI[sha256sum] = "ebe0d7444e3d7c8da7642055ac2206f0190ee060700d99cd876f8fc9964cb6ce"
