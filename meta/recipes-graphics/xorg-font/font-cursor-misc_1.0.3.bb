DESCRIPTION = "Xorg cursor fonts"

require xorg-font-common.inc

LICENSE = "PD"
LIC_FILES_CHKSUM = "file://COPYING;md5=8b32ccac3ad25e75e68478deb7780265"

DEPENDS = "util-macros-native font-util-native"
RDEPENDS_${PN} = "encodings font-util"
RDEPENDS_${PN}_class-native = "font-util-native"

PR = "1"

SRC_URI[md5sum] = "3e0069d4f178a399cffe56daa95c2b63"
SRC_URI[sha256sum] = "17363eb35eece2e08144da5f060c70103b59d0972b4f4d77fd84c9a7a2dba635"
