SUMMARY = "Xorg misc font set"
LICENSE = "PD"
PR = "r1"

inherit packagegroup

PACKAGE_ARCH = "${MACHINE_ARCH}"

RDEPENDS_${PN} = "\
	font-cursor-misc \
	font-misc-misc \
"
