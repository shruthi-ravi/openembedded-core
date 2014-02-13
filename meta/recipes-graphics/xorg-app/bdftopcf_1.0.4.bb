require xorg-app-common.inc
DESCRIPTION = "converts BDF fonts to PCF fonts"
DEPENDS += " libxfont"
PR = "1"

LIC_FILES_CHKSUM = "file://COPYING;md5=f9a35333adf75edd1eaef84bca65a490"

SRC_URI[md5sum] = "96a648a332160a7482885800f7a506fa"
SRC_URI[sha256sum] = "eaf59057ba3d7cffe29526562ce50868da7da823487a4cfb3e16946e5ffd2798"

BBCLASSEXTEND = "native"
