require python.inc
DEPENDS = "python-native bzip2 db gdbm openssl readline sqlite3 zlib"
PR = "${INC_PR}"

DISTRO_SRC_URI ?= "file://sitecustomize.py"
DISTRO_SRC_URI_linuxstdbase = ""
SRC_URI += "\
  file://01-use-proper-tools-for-cross-build.patch \
  file://03-fix-tkinter-detection.patch \
  file://06-avoid_usr_lib_termcap_path_in_linking.patch \
  ${DISTRO_SRC_URI} \
  file://multilib.patch \
  file://cgi_py.patch \
  file://setup_py_skip_cross_import_check.patch \
  file://add-md5module-support.patch \
  file://host_include_contamination.patch \
  file://fix_for_using_different_libdir.patch \
  file://setuptweaks.patch \
  file://check-if-target-is-64b-not-host.patch \
  file://search_db_h_in_inc_dirs_and_avoid_warning.patch \
  file://avoid_warning_about_tkinter.patch \
  file://avoid_warning_for_sunos_specific_module.patch \
  file://python-2.7.3-remove-bsdb-rpath.patch \
  file://fix-makefile-for-ptest.patch \
  file://run-ptest \
  file://parallel-makeinst-create-bindir.patch \
  file://use_sysroot_ncurses_instead_of_host.patch \
  file://use_stdlib_landmark.patch \
"

FILESEXTRAPATHS_prepend:="${THISDIR}/python:"

S = "${WORKDIR}/Python-${PV}"

SUMMARY_${PN}="Python interpreter and core modules (compressed)"

PYTHON_PKG_LIST="libpython2 python python-audio python-codecs python-compile python-compiler python-compression python-core python-crypt python-ctypes python-curses python-datetime python-difflib python-elementtree python-email python-fcntl python-idle python-io python-json python-lang python-logging python-math python-mime python-mmap python-multiprocessing python-netclient python-netserver python-numbers python-pickle python-pprint python-profile python-re python-resource python-subprocess python-shell python-stringold python-terminal python-textutils python-threading python-unixadmin python-xml python-xmlrpc python-zlib python-distutils python-misc"

RPROVIDES_${PN}+="${PYTHON_PKG_LIST}"

RREPLACES_${PN}+="${PYTHON_PKG_LIST}"

RCONFLICTS_${PN}+="${PYTHON_PKG_LIST}"

inherit autotools multilib_header python-dir pythonnative

# The 3 lines below are copied from the libffi recipe, ctypes ships its own copy of the libffi sources
#Somehow gcc doesn't set __SOFTFP__ when passing -mfloatabi=softp :(
TARGET_CC_ARCH_append_armv6 = " -D__SOFTFP__"
TARGET_CC_ARCH_append_armv7a = " -D__SOFTFP__"

# The following is a hack until we drop ac_cv_sizeof_off_t from site files
EXTRA_OECONF += "${@bb.utils.contains('DISTRO_FEATURES', 'largefile', 'ac_cv_sizeof_off_t=8', '', d)} ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no"

do_configure_append() {
	rm -f ${S}/Makefile.orig
	autoreconf -Wcross --verbose --install --force --exclude=autopoint ../Python-${PV}/Modules/_ctypes/libffi
}

do_compile() {
        # regenerate platform specific files, because they depend on system headers
        cd ${S}/Lib/plat-linux2
        include=${STAGING_INCDIR} ${STAGING_BINDIR_NATIVE}/python-native/python \
                ${S}/Tools/scripts/h2py.py -i '(u_long)' \
                ${STAGING_INCDIR}/dlfcn.h \
                ${STAGING_INCDIR}/linux/cdrom.h \
                ${STAGING_INCDIR}/netinet/in.h \
                ${STAGING_INCDIR}/sys/types.h
        sed -e 's,${STAGING_DIR_HOST},,g' -i *.py
        cd -

	# remove hardcoded ccache, see http://bugs.openembedded.net/show_bug.cgi?id=4144
	sed -i -e s,ccache\ ,'$(CCACHE) ', Makefile

	# remove any bogus LD_LIBRARY_PATH
	sed -i -e s,RUNSHARED=.*,RUNSHARED=, Makefile

	if [ ! -f Makefile.orig ]; then
		install -m 0644 Makefile Makefile.orig
	fi
	sed -i -e 's#^LDFLAGS=.*#LDFLAGS=${LDFLAGS} -L. -L${STAGING_LIBDIR}#g' \
		-e 's,libdir=${libdir},libdir=${STAGING_LIBDIR},g' \
		-e 's,libexecdir=${libexecdir},libexecdir=${STAGING_DIR_HOST}${libexecdir},g' \
		-e 's,^LIBDIR=.*,LIBDIR=${STAGING_LIBDIR},g' \
		-e 's,includedir=${includedir},includedir=${STAGING_INCDIR},g' \
		-e 's,^INCLUDEDIR=.*,INCLUDE=${STAGING_INCDIR},g' \
		-e 's,^CONFINCLUDEDIR=.*,CONFINCLUDE=${STAGING_INCDIR},g' \
		Makefile
	# save copy of it now, because if we do it in do_install and 
	# then call do_install twice we get Makefile.orig == Makefile.sysroot
	install -m 0644 Makefile Makefile.sysroot

	export CROSS_COMPILE="${TARGET_PREFIX}"
	export PYTHONBUILDDIR="${S}"

	oe_runmake HOSTPGEN=${STAGING_BINDIR_NATIVE}/python-native/pgen \
		HOSTPYTHON=${STAGING_BINDIR_NATIVE}/python-native/python \
		STAGING_LIBDIR=${STAGING_LIBDIR} \
		STAGING_INCDIR=${STAGING_INCDIR} \
		STAGING_BASELIBDIR=${STAGING_BASELIBDIR} \
		BUILD_SYS=${BUILD_SYS} HOST_SYS=${HOST_SYS} \
		OPT="${CFLAGS}"
}

do_install() {
	# make install needs the original Makefile, or otherwise the inclues would
	# go to ${D}${STAGING...}/...
	install -m 0644 Makefile.orig Makefile

	export CROSS_COMPILE="${TARGET_PREFIX}"
	export PYTHONBUILDDIR="${S}"

	# After swizzling the makefile, we need to run the build again.
	# install can race with the build so we have to run this first, then install
	oe_runmake HOSTPGEN=${STAGING_BINDIR_NATIVE}/python-native/pgen \
		HOSTPYTHON=${STAGING_BINDIR_NATIVE}/python-native/python \
		CROSSPYTHONPATH=${STAGING_LIBDIR_NATIVE}/python${PYTHON_MAJMIN}/lib-dynload/ \
		STAGING_LIBDIR=${STAGING_LIBDIR} \
		STAGING_INCDIR=${STAGING_INCDIR} \
		STAGING_BASELIBDIR=${STAGING_BASELIBDIR} \
		BUILD_SYS=${BUILD_SYS} HOST_SYS=${HOST_SYS} \
		DESTDIR=${D} LIBDIR=${libdir}

	oe_runmake HOSTPGEN=${STAGING_BINDIR_NATIVE}/python-native/pgen \
		HOSTPYTHON=${STAGING_BINDIR_NATIVE}/python-native/python \
		CROSSPYTHONPATH=${STAGING_LIBDIR_NATIVE}/python${PYTHON_MAJMIN}/lib-dynload/ \
		STAGING_LIBDIR=${STAGING_LIBDIR} \
		STAGING_INCDIR=${STAGING_INCDIR} \
		STAGING_BASELIBDIR=${STAGING_BASELIBDIR} \
		BUILD_SYS=${BUILD_SYS} HOST_SYS=${HOST_SYS} \
		DESTDIR=${D} LIBDIR=${libdir} install

	install -m 0644 Makefile.sysroot ${D}/${libdir}/python${PYTHON_MAJMIN}/config/Makefile

	if [ -e ${WORKDIR}/sitecustomize.py ]; then
		install -m 0644 ${WORKDIR}/sitecustomize.py ${D}/${libdir}/python${PYTHON_MAJMIN}
	fi

	oe_multilib_header python${PYTHON_MAJMIN}/pyconfig.h
}

do_install_append() {
        # Remove all the files for the packages python-zip won't provide

        # No need for man pages (-man)
        rm -rf ${D}${datadir}/man
        # No need for static libs (distutils-staticdev)
        rm -f ${D}${libdir}/python2.7/config/lib*.a
        # No need for python 2 to 3 translator
        rm -rf ${D}${bindir}/2to3 ${D}${libdir}/python2.7/lib2to3
        # No need for debugger
        rm -f ${D}${libdir}/python2.7/bdb.* ${D}${libdir}/python2.7/pdb.*
        # No need for development tools
        rm -rf ${D}${includedir} ${D}${libdir}/lib*${SOLIBSDEV} ${D}${libdir}/*.la ${D}${libdir}/*.a ${D}${libdir}/*.o ${D}${libdir}/pkgconfig ${D}${base_libdir}/*.a ${D}${base_libdir}/*.o ${D}${datadir}/aclocal ${D}${datadir}/pkgconfig
        # No need for Berkeley Database bindings
        rm -rf ${D}${libdir}/python2.7/bsddb ${D}${libdir}/python2.7/lib-dynload/_bsddb.so
        # No need for file-based database support
        rm -f ${D}${libdir}/python2.7/anydbm.* ${D}${libdir}/python2.7/dumbdbm.* ${D}${libdir}/python2.7/whichdb.*
        # No need for GNU database support
        rm -f ${D}${libdir}/python2.7/lib-dynload/gdbm.so
        # No need for hotshot performance profiler
        rm -rf ${D}${libdir}/python2.7/hotshot ${D}${libdir}/python2.7/lib-dynload/_hotshot.so
        # No need for HTML processing support
        rm -f ${D}${libdir}/python2.7/formatter.* ${D}${libdir}/python2.7/htmlentitydefs.* ${D}${libdir}/python2.7/htmllib.* ${D}${libdir}/python2.7/markupbase.* ${D}${libdir}/python2.7/sgmllib.* ${D}${libdir}/python2.7/HTMLParser.*
        # No need for Python Integrated Development Environment
        rm -rf ${D}${bindir}/idle ${D}${libdir}/python2.7/idlelib
        # No need for graphical image handling
        rm -f ${D}${libdir}/python2.7/colorsys.* ${D}${libdir}/python2.7/imghdr.* ${D}${libdir}/python2.7/lib-dynload/imageop.so ${D}${libdir}/python2.7/lib-dynload/rgbimg.so
        # No need for import library
        rm -rf ${D}${libdir}/python2.7/importlib
        # No need for mailbox format support
        rm -f ${D}${libdir}/python2.7/mailbox.*
        # No need for package extension utility support
        rm -f ${D}${libdir}/python2.7/pkgutil.*
        # No need for interactive help support
        rm -rf ${D}${bindir}/pydoc ${D}${libdir}/python2.7/pydoc.* ${D}${libdir}/python2.7/pydoc_data
        # No need for readline support
        rm -f ${D}${libdir}/python2.7/lib-dynload/readline.so ${D}${libdir}/python2.7/rlcompleter.*
        # No need for robots.txt parser
        rm -f ${D}${libdir}/python2.7/robotparser.*
        # No need for smtp support
        rm -f ${D}${bindir}/smtpd.* ${D}${libdir}/python2.7/smtpd.*
        # No need for sqlit3 support
        rm -f ${D}${libdir}/python2.7/lib-dynload/_sqlite3.so ${D}${libdir}/python2.7/sqlite3/dbapi2.* ${D}${libdir}/python2.7/sqlite3/__init__.* ${D}${libdir}/python2.7/sqlite3/dump.*
         # No need for tests (-doctest, -sqlite-test, -unittest, -test
        rm -f ${D}${libdir}/python2.7/doctest.*
        rm -rf ${D}${libdir}/python2.7/sqlite3/test/
        rm -rf ${D}${libdir}/python2.7/test/
        rm -rf ${D}${libdir}/python2.7/unittest/
        # No need for syslog interface
        rm -f ${D}${libdir}/python2.7/lib-dynload/syslog.so
        # No need for Tcl/Tk bindings
        rm -rf ${D}${libdir}/python2.7/lib-dynload/_tkinter.so ${D}${libdir}/python2.7/lib-tk

        # Compress the scripts for the packages we do provide (/usr/lib/python27.zip)

        mkdir -p ${D}/zip${libdir}/python2.7
        # Move python to zip sandbox
        mv ${D}${libdir}/python2.7/* ${D}/zip${libdir}/python2.7
        # Move shared libs, etc back to ${libdir}
        mv ${D}/zip${libdir}/python2.7/config ${D}${libdir}/python2.7
        mv ${D}/zip${libdir}/python2.7/lib-dynload ${D}${libdir}/python2.7/
        # Move zlib back to ${libdir} (zipimport won't work without it)
        mkdir -p ${D}${libdir}/python2.7/encodings
        mv ${D}/zip${libdir}/python2.7/encodings/zlib* ${D}${libdir}/python2.7/encodings
        # Move landmark file back to ${libdir}
        mv ${D}/zip${libdir}/python2.7/stdlib_landmark.py ${D}${libdir}/python2.7/
        # Create /usr/lib/python27.zip
        cd ${D}/zip${libdir}/python2.7 ; zip -q -9 -r -y python27.zip . ; cd -
        mv ${D}/zip/${libdir}/python2.7/python27.zip ${D}${libdir}
        rm -rf ${D}/zip
}

# Sysroot already populated by non-compressed python recipe
do_populate_sysroot[noexec]="1"

SSTATE_SCAN_FILES += "Makefile"
PACKAGE_PREPROCESS_FUNCS += "py_package_preprocess"

py_package_preprocess () {
	# copy back the old Makefile to fix target package
	install -m 0644 Makefile.orig ${PKGD}/${libdir}/python${PYTHON_MAJMIN}/config/Makefile

	# Remove references to buildmachine paths in target Makefile
	sed -i -e 's:--sysroot=${STAGING_DIR_TARGET}::g' -e s:'--with-libtool-sysroot=${STAGING_DIR_TARGET}'::g ${PKGD}/${libdir}/python${PYTHON_MAJMIN}/config/Makefile
}

# manual dependency additions
RRECOMMENDS_${PN} = "openssl"

FILES_${PN}="${libdir} ${bindir} ${datadir}"

# catch debug extensions (isn't that already in python-core-dbg?)
FILES_${PN}-dbg += "${libdir}/python${PYTHON_MAJMIN}/lib-dynload/.debug"
