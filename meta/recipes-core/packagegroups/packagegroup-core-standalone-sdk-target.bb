SUMMARY = "Target packages for the standalone SDK"
PR = "r8"

inherit packagegroup

RDEPENDS_${PN} = "\
    libgcc \
    libgcc-dev \
    libatomic \
    libatomic-dev \
    libstdc++ \
    libstdc++-dev \
    libstdc++-staticdev \
    ${LIBC_DEPENDENCIES} \
    "

RRECOMMENDS_${PN} = "\
    libssp \
    libssp-dev \
    "
