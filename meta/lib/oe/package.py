def runstrip(arg):
    # Function to strip a single file, called from split_and_strip_files below
    # A working 'file' (one which works on the target architecture)
    #
    # The elftype is a bit pattern (explained in split_and_strip_files) to tell
    # us what type of file we're processing...
    # 4 - executable
    # 8 - shared library
    # 16 - kernel module

    import stat, subprocess

    (file, elftype, strip) = arg

    newmode = None
    if not os.access(file, os.W_OK) or os.access(file, os.R_OK):
        origmode = os.stat(file)[stat.ST_MODE]
        newmode = origmode | stat.S_IWRITE | stat.S_IREAD
        os.chmod(file, newmode)

    stripcmd = [strip]

    # kernel module    
    if elftype & 16:
        stripcmd.extend(["--strip-debug", "--remove-section=.comment",
            "--remove-section=.note", "--preserve-dates"])
    # .so and shared library
    elif ".so" in file and elftype & 8:
        stripcmd.extend(["--remove-section=.comment", "--remove-section=.note", "--strip-unneeded"])
    # shared or executable:
    elif elftype & 8 or elftype & 4:
        stripcmd.extend(["--remove-section=.comment", "--remove-section=.note"])

    stripcmd.append(file)
    bb.debug(1, "runstrip: %s" % stripcmd)

    try:
        output = subprocess.check_output(stripcmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        bb.error("runstrip: '%s' strip command failed with %s (%s)" % (stripcmd, e.returncode, e.output))

    if newmode:
        os.chmod(file, origmode)

    return


def file_translate(file):
    ft = file.replace("@", "@at@")
    ft = ft.replace(" ", "@space@")
    ft = ft.replace("\t", "@tab@")
    ft = ft.replace("[", "@openbrace@")
    ft = ft.replace("]", "@closebrace@")
    ft = ft.replace("_", "@underscore@")
    return ft

def filedeprunner(arg):
    import re, subprocess, shlex

    (pkg, pkgfiles, rpmdeps, pkgdest) = arg
    provides = {}
    requires = {}

    file_re = re.compile(r'\s+\d+\s(.*)')
    dep_re = re.compile(r'\s+(\S)\s+(.*)')
    r = re.compile(r'[<>=]+\s+\S*')

    def process_deps(pipe, pkg, pkgdest, provides, requires):
        file = None
        for line in pipe:
            line = line.decode("utf-8")

            m = file_re.match(line)
            if m:
                file = m.group(1)
                file = file.replace(pkgdest + "/" + pkg, "")
                file = file_translate(file)
                continue

            m = dep_re.match(line)
            if not m or not file:
                continue

            type, dep = m.groups()

            if type == 'R':
                i = requires
            elif type == 'P':
                i = provides
            else:
               continue

            if dep.startswith("python("):
                continue

            # Ignore all perl(VMS::...) and perl(Mac::...) dependencies. These
            # are typically used conditionally from the Perl code, but are
            # generated as unconditional dependencies.
            if dep.startswith('perl(VMS::') or dep.startswith('perl(Mac::'):
                continue

            # Ignore perl dependencies on .pl files.
            if dep.startswith('perl(') and dep.endswith('.pl)'):
                continue

            # Remove perl versions and perl module versions since they typically
            # do not make sense when used as package versions.
            if dep.startswith('perl') and r.search(dep):
                dep = dep.split()[0]

            # Put parentheses around any version specifications.
            dep = r.sub(r'(\g<0>)',dep)

            if file not in i:
                i[file] = []
            i[file].append(dep)

        return provides, requires

    try:
        dep_popen = subprocess.Popen(shlex.split(rpmdeps) + pkgfiles, stdout=subprocess.PIPE)
        provides, requires = process_deps(dep_popen.stdout, pkg, pkgdest, provides, requires)
    except OSError as e:
        bb.error("rpmdeps: '%s' command failed, '%s'" % (shlex.split(rpmdeps) + pkgfiles, e))
        raise e

    return (pkg, provides, requires)


def read_shlib_providers(d):
    import re

    shlib_provider = {}
    shlibs_dirs = d.getVar('SHLIBSDIRS').split()
    list_re = re.compile('^(.*)\.list$')
    # Go from least to most specific since the last one found wins
    for dir in reversed(shlibs_dirs):
        bb.debug(2, "Reading shlib providers in %s" % (dir))
        if not os.path.exists(dir):
            continue
        for file in os.listdir(dir):
            m = list_re.match(file)
            if m:
                dep_pkg = m.group(1)
                try:
                    fd = open(os.path.join(dir, file))
                except IOError:
                    # During a build unrelated shlib files may be deleted, so
                    # handle files disappearing between the listdirs and open.
                    continue
                lines = fd.readlines()
                fd.close()
                for l in lines:
                    s = l.strip().split(":")
                    if s[0] not in shlib_provider:
                        shlib_provider[s[0]] = {}
                    shlib_provider[s[0]][s[1]] = (dep_pkg, s[2])
    return shlib_provider


def npm_split_package_dirs(pkgdir):
    """
    Work out the packages fetched and unpacked by BitBake's npm fetcher
    Returns a dict of packagename -> (relpath, package.json) ordered
    such that it is suitable for use in PACKAGES and FILES
    """
    from collections import OrderedDict
    import json
    packages = {}
    for root, dirs, files in os.walk(pkgdir):
        if os.path.basename(root) == 'node_modules':
            for dn in dirs:
                relpth = os.path.relpath(os.path.join(root, dn), pkgdir)
                pkgitems = ['${PN}']
                for pathitem in relpth.split('/'):
                    if pathitem == 'node_modules':
                        continue
                    pkgitems.append(pathitem)
                pkgname = '-'.join(pkgitems).replace('_', '-')
                pkgname = pkgname.replace('@', '')
                pkgfile = os.path.join(root, dn, 'package.json')
                data = None
                if os.path.exists(pkgfile):
                    with open(pkgfile, 'r') as f:
                        data = json.loads(f.read())
                    packages[pkgname] = (relpth, data)
    # We want the main package for a module sorted *after* its subpackages
    # (so that it doesn't otherwise steal the files for the subpackage), so
    # this is a cheap way to do that whilst still having an otherwise
    # alphabetical sort
    return OrderedDict((key, packages[key]) for key in sorted(packages, key=lambda pkg: pkg + '~'))

def archive_dir(dirPath, archivePath):
    ''' Create tar.bz2 archive at archivePath from dirPath '''
    import os, oe, bb

    arDir = os.path.dirname(dirPath)
    arName = os.path.basename(dirPath)

    cmd = 'tar -c -I pbzip2 -f \"%s\" -C \"%s\" -p \"%s\"' % (archivePath, arDir, arName)
    (retval, output) = oe.utils.getstatusoutput(cmd)
    if retval:
        bb.fatal('Failed to archive %s --> %s: %s %s' % (dirPath, archivePath, cmd, output))

def do_install_source(d):
    ''' Stage recipe's source for packaging '''
    import os, oe, bb

    pn = d.getVar("PN", True)

    if d.getVar("ENABLE_SRC_INSTALL_%s" % pn, True) != "1":
        return

    packages = (d.getVar("PACKAGES", True) or "").split()
    if ("%s-src" % pn) not in packages:
        # Some recipes redefine PACKAGES without ${PN}-src. Don't stage
        # anything in this case to avoid installed-vs-shipped warning.
        return

    urls = (d.getVar('SRC_URI', True) or "").split()
    if len(urls) == 0:
        return

    workdir = d.getVar('WORKDIR', True)

    # TODO rm_work() should clean this up
    unpackTempDir = os.path.join(workdir, 'install-source-unpack-temp')
    if os.path.exists(unpackTempDir):
        bb.utils.remove(unpackTempDir, recurse=True)
    os.makedirs(unpackTempDir, 0o755)

    src_d = d.getVar("SRC_D", True)
    if os.path.exists(src_d):
        bb.warn("SRC_D already exist. Removing.")
        bb.utils.remove(src_d, recurse=True)
    os.makedirs(src_d, 0o755)

    fetcher = bb.fetch2.Fetch(urls, d)

    fileManif = []
    for url in urls:
        urlScheme = bb.fetch2.decodeurl(url)[0]
        srcPath = fetcher.localpath(url)
        srcName = os.path.basename(srcPath)

        dstName = srcName
        if os.path.isdir(srcPath):
            dstName += '.tar.bz2'

        dstPath = os.path.join(src_d, dstName)

        # fetch() doesn't retrieve any actual files from git:// URLs,
        # so we do an additional unpack() step to get something useful
        # for these.
        # TODO: May need to pre-process other revision control schemes
        if urlScheme == 'git':
            unpackPath = os.path.join(unpackTempDir, srcName)
            if os.path.exists(unpackPath):
                bb.utils.remove(unpackPath, recurse=True)
            os.makedirs(unpackPath, 0o755)

            fetcher.unpack(unpackPath, [url])

            # unpack() puts actual source in a 'git' subdir
            srcPath = os.path.join(unpackPath, 'git')

        if os.path.exists(dstPath):
            bb.warn('Duplicate file %s in SRC_URI. Overwriting.' % dstName)
            bb.utils.remove(dstPath, recurse=True)

        if not dstName in fileManif:
            fileManif.append(dstName)

        if os.path.isdir(srcPath):
            archive_dir(srcPath, dstPath)
        else:
            bb.utils.copyfile(srcPath, dstPath)

    manifFilePath = os.path.join(src_d, 'manifest')
    if os.path.exists(manifFilePath):
        bb.warn('manifest file found in SRC_URI. Overwriting.')
        bb.utils.remove(manifFilePath, recurse=True)

    with open(manifFilePath, 'w') as manif:
        for fname in fileManif:
            manif.write(fname)
            manif.write('\n')
