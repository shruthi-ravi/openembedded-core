SUMMARY = "Initscript for hwclock utility"
DESCRIPTION = "\
Installs an initscript that updates the system clock based on the available \
hwclock implementation."

SECTION = "base"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://hwclock.sh"

S = "${WORKDIR}"

inherit update-rc.d

INITSCRIPT_PACKAGES = "${PN}"

INITSCRIPT_NAME_${PN} = "hwclock.sh"
INITSCRIPT_PARAMS_${PN} = "defaults"

do_install () {
	install -d ${D}${sysconfdir}/init.d
	install -m 0755 ${WORKDIR}/hwclock.sh ${D}${sysconfdir}/init.d/
}

PACKAGES = "${PN}"

PACKAGE_ARCH = "all"

FILES_${PN} = "${sysconfdir}/init.d/hwclock.sh"
