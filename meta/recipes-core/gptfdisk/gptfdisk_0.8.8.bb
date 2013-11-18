DESCRIPTION = "GPT fdisk for modifying GUID Partition Tables"
SECTION = "base"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://COPYING;md5=59530bdf33659b29e73d4adb9f9f6552"

DEPENDS = "popt util-linux icu"

S = "${WORKDIR}/${PN}-${PV}"

PACKAGES =+ "${PN}-gdisk ${PN}-cgdisk ${PN}-sgdisk ${PN}-fixparts"
FILES_${PN}-gdisk = "${sbindir}/gdisk"
FILES_${PN}-cgdisk = "${sbindir}/cgdisk"
FILES_${PN}-sgdisk = "${sbindir}/sgdisk"
FILES_${PN}-fixparts = "${sbindir}/fixparts"

SRC_URI = "http://downloads.sourceforge.net/project/${PN}/${PN}/${PV}/${PN}-${PV}.tar.gz"
SRC_URI[md5sum]="bd47d03ec27bab5613254b5a20f72143"
SRC_URI[sha256sum] = "4c31e9c0e4802079526658947ab236d3b417604a8246a418f41cdc2a8ec2be9a"

do_install() {
	install -m 0755 -d ${D}${sbindir}
	sbinprogs="gdisk cgdisk sgdisk fixparts"
	for f in ${sbinprogs}; do
		install -m 0755 ${S}/${f} ${D}${sbindir}
	done
}
