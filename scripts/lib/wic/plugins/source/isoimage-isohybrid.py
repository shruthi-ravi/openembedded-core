# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# DESCRIPTION
# This implements the 'isoimage-isohybrid' source plugin class for 'wic'
#
# AUTHORS
# Mihaly Varga <mihaly.varga (at] ni.com>

import os
import re
import shutil

from wic import kickstart, msger
from wic.pluginbase import SourcePlugin
from wic.utils.oe.misc import exec_cmd, exec_native_cmd, get_bitbake_var

class IsoImagePlugin(SourcePlugin):
    """
    Create a bootable ISO image

    This plugin creates a hybrid, legacy and EFI bootable ISO image. The generated
    image can be used on optical media as well as USB media.

    Legacy boot uses syslinux and EFI boot uses grub or gummiboot (not implemented yet)
    as bootloader. The plugin creates the directories required by bootloaders and populates them
    by creating and configuring the bootloader files.

    Example kickstart file:
    part /boot --source isoimage-isohybrid --sourceparams="loader=grub-efi,image_name= IsoImage" \
                      --ondisk cd --label LIVECD --fstype=ext2
    bootloader  --timeout=10  --append=" "

    In --sourceparams "loader" specifies the bootloader used for booting in EFI mode, while
    "image_name" specifies the name of the generated image. In the example above, wic creates
    an ISO image named IsoImage-cd.direct (default extension added by direct imeger plugin) and a
    file named IsoImage-cd.iso
    """

    name = 'isoimage-isohybrid'

    @classmethod
    def do_configure_syslinux(self, isodir, cr, cr_workdir):
        """
        Create loader-specific (syslinux) config
        """
        splash = os.path.join(cr_workdir, "/ISO/boot/splash.jpg")
        if os.path.exists(splash):
            splashline = "menu background splash.jpg"
        else:
            splashline = ""

        options = cr.ks.handler.bootloader.appendLine

        timeout = kickstart.get_timeout(cr.ks)
        if not timeout:
            timeout = 10

        syslinux_conf = ""
        syslinux_conf += "PROMPT 0\n"
        syslinux_conf += "TIMEOUT %s \n" % timeout
        syslinux_conf += "\n"
        syslinux_conf += "ALLOWOPTIONS 1\n"
        syslinux_conf += "SERIAL 0 115200\n"
        syslinux_conf += "\n"
        if splashline:
            syslinux_conf += "%s\n" % splashline
        syslinux_conf += "DEFAULT boot\n"
        syslinux_conf += "LABEL boot\n"

        kernel = "/bzImage"
        syslinux_conf += "KERNEL " + kernel + "\n"
        syslinux_conf += "APPEND initrd=/initrd LABEL=boot root=/dev/ram0 %s \n" % options

        msger.debug("Writing syslinux config %s/ISO/isolinux/isolinux.cfg" \
                    % cr_workdir)
        with open("%s/ISO/isolinux/isolinux.cfg" % cr_workdir, "w") as cfg:
            cfg.write(syslinux_conf)

    @classmethod
    def do_configure_grubefi(self, isodir, part, cr, cr_workdir):
        """
        Create loader-specific (grub-efi) config
        """
        splash = os.path.join(cr_workdir, "/EFI/boot/splash.jpg")
        if os.path.exists(splash):
            splashline = "menu background splash.jpg"
        else:
            splashline = ""

        options = cr.ks.handler.bootloader.appendLine

        grubefi_conf = ""
        grubefi_conf += "serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1\n"
        grubefi_conf += "default=boot\n"
        timeout = kickstart.get_timeout(cr.ks)
        if not timeout:
            timeout = 10
        grubefi_conf += "timeout=%s\n" % timeout
        grubefi_conf += "\n"
        grubefi_conf += "search --set=root --label %s " % part.label
        grubefi_conf += "\n"
        grubefi_conf += "menuentry 'boot'{\n"

        kernel = "/bzImage"

        grubefi_conf += "linux %s rootwait %s\n" \
            % (kernel, options)
        grubefi_conf += "initrd /initrd \n"
        grubefi_conf += "}\n"

        msger.debug("Writing grubefi config %s/EFI/BOOT/grub.cfg" \
                        % cr_workdir)
        with open("%s/EFI/BOOT/grub.cfg" % cr_workdir, "w") as cfg:
            cfg.write(grubefi_conf)

    @staticmethod
    def __build_initramfs_path():
        """
        Create path for initramfs image
        """

        initrd = get_bitbake_var("INITRD")
        if not initrd:
            initrd_dir = get_bitbake_var("DEPLOY_DIR_IMAGE")
            if not initrd_dir:
                msger.error("Couldn't find DEPLOY_DIR_IMAGE, exiting.\n")

            image_name = get_bitbake_var("IMAGE_LINK_NAME")
            if not image_name :
                msger.error("Couldn't find IMAGE_LINK_NAME, exiting.\n")

            image_type = get_bitbake_var("INITRAMFS_FSTYPES")
            if not image_type:
                msger.error("Couldn't find INITRAMFS_FSTYPES, exiting.\n")

            initrd = "%s/%s.%s" % (initrd_dir, image_name, image_type)

        if not os.path.exists(initrd):
            msger.error("Couldn't find initrd or %s, exiting.\n" % initrd)
        #TODO: create initrd from rootfs
        return initrd

    @classmethod
    def do_stage_partition(self, part, source_params, cr, cr_workdir,
                           oe_builddir, bootimg_dir, kernel_dir,
                           native_sysroot):
        """
        Special content staging called before do_prepare_partition().
        It cheks if all necessary tools are available, if not
        tries to instal them.
        """
        # Make sure parted is available in native sysroot
        if not os.path.isfile("%s/usr/sbin/parted" % native_sysroot):
            msger.info("Building parted-native...\n")
            exec_cmd("bitbake parted-native")

        # Make sure mkfs.ext2/3/4 is available in native sysroot
        if not os.path.isfile("%s/sbin/mkfs.ext2" % native_sysroot):
            msger.info("Building e2fsprogs-native...\n")
            exec_cmd("bitbake e2fsprogs-native")

        # Make sure syslinux is available in sysroot and in native sysroot
        syslinux_dir = get_bitbake_var("STAGING_DATADIR")
        if not syslinux_dir:
            msger.error("Couldn't find STAGING_DATADIR, exiting.\n")
        if not os.path.exists("%s/syslinux" % syslinux_dir):
            msger.info("Building syslinux...\n")
            exec_cmd("bitbake syslinux")
        if not os.path.exists("%s/syslinux" % syslinux_dir):
            msger.error("Please build syslinux first\n")

        # Make sure syslinux is available in native sysroot
        if not os.path.exists("%s/usr/bin/syslinux" % native_sysroot):
            msger.info("Building syslinux-native...\n")
            exec_cmd("bitbake syslinux-native")

        #Make sure mkisofs is available in native sysroot
        if not os.path.isfile("%s/usr/bin/mkisofs" % native_sysroot):
            msger.info("Building cdrtools-native...\n")
            exec_cmd("bitbake cdrtools-native")

        # Make sure mkfs.vfat is available in native sysroot
        if not os.path.isfile("%s/sbin/mkfs.vfat" % native_sysroot):
            msger.info("Building dosfstools-native...\n")
            exec_cmd("bitbake dosfstools-native")

        # Make sure mtools is available in native sysroot
        if not os.path.isfile("%s/usr/bin/mcopy" % native_sysroot):
            msger.info("Building mtools-native...\n")
            exec_cmd("bitbake mtools-native")

    @classmethod
    def do_configure_partition(self, part, source_params, cr, cr_workdir,
                               oe_builddir, bootimg_dir, kernel_dir,
                               native_sysroot):
        """
        Called before do_prepare_partition(), creates loader-specific config
        """
        isodir = "%s/ISO/" % cr_workdir

        if os.path.exists(cr_workdir):
            shutil.rmtree(cr_workdir)

        install_cmd = "install -d %s " % isodir
        exec_cmd(install_cmd)

        # Overwrite the name of the created image
        msger.debug("%s" % source_params)
        if 'image_name' in  source_params and  source_params['image_name'].strip():
            cr.name = source_params['image_name'].strip()
            msger.debug("The name of the image is: %s" % cr.name)

    @classmethod
    def do_prepare_partition(self, part, source_params, cr, cr_workdir,
                             oe_builddir, bootimg_dir, kernel_dir,
                             rootfs_dir, native_sysroot):
        """
        Called to do the actual content population for a partition i.e. it
        'prepares' the partition to be incorporated into the image.
        In this case, prepare content for a bootable ISO image.
        """

        isodir = "%s/ISO" % cr_workdir

        if part.rootfs is None:
            if not 'ROOTFS_DIR' in rootfs_dir:
                msger.error("Couldn't find --rootfs-dir, exiting.\n")
            rootfs_dir = rootfs_dir['ROOTFS_DIR']
        else:
            if part.rootfs in rootfs_dir:
                rootfs_dir = rootfs_dir[part.rootfs]
            elif part.rootfs:
                rootfs_dir = part.rootfs
            else:
                msg = "Couldn't find --rootfs-dir=%s connection"
                " or it is not a valid path, exiting.\n"
                msger.error(msg % part.rootfs)

        if not os.path.isdir(rootfs_dir):
            rootfs_dir = get_bitbake_var("IMAGE_ROOTFS")
        if not os.path.isdir(rootfs_dir):
            msger.error("Couldn't find IMAGE_ROOTFS, exiting.\n")

        part.set_rootfs(rootfs_dir)

        # Prepare rootfs.img
        hdd_dir = get_bitbake_var("HDDDIR")
        img_iso_dir = get_bitbake_var("ISODIR")

        rootfs_img = "%s/rootfs.img" % hdd_dir
        if not os.path.isfile(rootfs_img):
            rootfs_img = "%s/rootfs.img" % img_iso_dir
        if not os.path.isfile(rootfs_img):
            # check if rootfs.img is in deploydir
            deploy_dir = get_bitbake_var("DEPLOY_DIR_IMAGE")
            image_name = get_bitbake_var("IMAGE_LINK_NAME")
            rootfs_img = "%s/%s.%s" \
                % (deploy_dir, image_name, part.fstype)

        if not os.path.isfile(rootfs_img):
            # create image file with type specified by --fstype which contains rootfs
            du_cmd = "du -bks %s" % rootfs_dir
            out = exec_cmd(du_cmd)
            part.set_size(int(out.split()[0]))
            part.extra_space = 0;
            part.overhead_factor = 1.5
            part.prepare_rootfs(cr_workdir, oe_builddir, rootfs_dir, native_sysroot)
            rootfs_img = part.source_file

        install_cmd = "install -m 0644 %s %s/rootfs.img" \
            % (rootfs_img, isodir)
        exec_cmd(install_cmd)

        # Remove the temporary file created by part.prepare_rootfs()
        if os.path.isfile(part.source_file):
            os.remove(part.source_file)

        # Prepare initial ramdisk
        initrd = "%s/initrd" % hdd_dir
        if not os.path.isfile(initrd):
            initrd = "%s/initrd" % img_iso_dir
        if not os.path.isfile(initrd):
            initrd = self.__build_initramfs_path()

        install_cmd = "install -m 0644 %s %s/initrd" \
            % (initrd, isodir)
        exec_cmd(install_cmd)

        # Install bzImage
        install_cmd = "install -m 0644 %s/bzImage %s/bzImage" % \
            (kernel_dir, isodir)
        exec_cmd(install_cmd)

        #Create bootloader for efi boot
        try:
            if source_params['loader'] == 'grub-efi':
                # Builds grub.cfg if ISODIR didn't exist or didn't contains grub.cfg
                bootimg_dir = img_iso_dir
                if not os.path.exists("%s/EFI/BOOT" % bootimg_dir):
                    bootimg_dir = "%s/bootimg" % cr_workdir
                    if os.path.exists(bootimg_dir):
                        shutil.rmtree(bootimg_dir)
                    install_cmd = "install -d %s/EFI/BOOT" % bootimg_dir
                    exec_cmd(install_cmd)

                if not os.path.isfile("%s/EFI/BOOT/boot.cfg" % bootimg_dir):
                    self.do_configure_grubefi(isodir, part, cr, bootimg_dir)

                # Builds bootx64.efi/bootia32.efi if ISODIR didn't exist or didn't contains it
                target_arch = get_bitbake_var("TARGET_SYS")
                if not target_arch:
                    msger.error("Coludn't find target architecture\n")

                if re.match("x86_64",target_arch):
                     grub_target = 'x86_64-efi'
                     grub_image = "bootx64.efi"
                elif re.match('i.86', target_arch):
                     grub_target = 'i386-efi'
                     grub_image = "bootia32.efi"
                else:
                     msger.error("grub-efi is incompatible with target %s\n" % target_arch)

                if not os.path.isfile("%s/EFI/BOOT/%s" % (bootimg_dir, grub_image)):
                    grub_path = get_bitbake_var("STAGING_LIBDIR")
                    if not grub_path:
                        msger.error("Couldn't find STAGING_LIBDIR, exiting.\n")

                    grub_core = "%s/grub/%s" % (grub_path, grub_target)
                    if not os.path.exists(grub_core):
                        msger.info("Building grub-efi...\n")
                        exec_cmd("bitbake grub-efi")
                    if not os.path.exists(grub_core):
                        msger.error("Please build grub-efi first\n")

                    grub_cmd = "grub-mkimage -p '/EFI/BOOT' "
                    grub_cmd += "-d %s "  % grub_core
                    grub_cmd += "-O %s -o %s/EFI/BOOT/%s " % (grub_target, bootimg_dir, grub_image)
                    grub_cmd += "part_gpt part_msdos ntfs ntfscomp fat ext2 normal chain boot configfile "
                    grub_cmd += "linux multiboot search efi_gop efi_uga font gfxterm gfxmenu terminal minicmd "
                    grub_cmd += "test iorw loadenv echo reboot serial terminfo iso9660 loopback "
                    grub_cmd += "memdisk tar help ls search_fs_uuid udf  btrfs reiserfs xfs lvm ata "
                    exec_native_cmd(grub_cmd, native_sysroot)

            else:
                msger.error("unrecognized bootimg-efi loader: %s" % source_params['loader'])
        except KeyError:
            msger.error("bootimg-efi requires a loader, none specified")

        if os.path.exists("%s/EFI/BOOT" % isodir):
            shutil.rmtree("%s/EFI/BOOT" % isodir)

        shutil.copytree(bootimg_dir+"/EFI/BOOT", isodir+"/EFI/BOOT")

        # If exists, remove cr_workdir/bootimg temporary folder
        if os.path.exists("%s/bootimg" % cr_workdir):
            shutil.rmtree("%s/bootimg" % cr_workdir)

        # Create efi.img that contains bootloader files for EFI booting
        # if ISODIR didn't exist or didn't contains it
        if os.path.isfile("%s/efi.img" % img_iso_dir):
            install_cmd = "install -m 0644 %s/efi.img %s/efi.img" % \
                (img_iso_dir, isodir)
            exec_cmd(install_cmd)
        else:
            du_cmd = "du -bks %s/EFI" % isodir
            out = exec_cmd(du_cmd)
            blocks = int(out.split()[0])
            blocks += 100
            msger.debug("Added 100 extra blocks to %s to get to %d total blocks" % \
                       ( part.mountpoint, blocks))

            # Ensure total sectors is an integral number of sectors per
            # track or mcopy will complain. Sectors are 512 bytes, and we
            # generate images with 32 sectors per track. This calculation is
            # done in blocks, thus the mod by 16 instead of 32.
            blocks += (16 - (blocks % 16))

            # dosfs image for EFI boot
            bootimg = "%s/efi.img" % isodir

            dosfs_cmd = 'mkfs.vfat -n "EFIimg" -S 512 -C %s %d' % (bootimg, blocks)
            exec_native_cmd(dosfs_cmd, native_sysroot)

            mmd_cmd = "mmd -i %s ::/EFI" % bootimg
            exec_native_cmd(mmd_cmd, native_sysroot)

            mcopy_cmd = "mcopy -i %s -s %s/EFI/* ::/EFI/" % (bootimg, isodir)
            exec_native_cmd(mcopy_cmd, native_sysroot)

            chmod_cmd = "chmod 644 %s" % bootimg
            exec_cmd(chmod_cmd)

        # Prepare files for legacy boot
        syslinux_dir = get_bitbake_var("STAGING_DATADIR")
        if not syslinux_dir:
            msger.error("Couldn't find STAGING_DATADIR, exiting.\n")

        if os.path.exists("%s/isolinux" % isodir):
            shutil.rmtree("%s/isolinux" % isodir)

        install_cmd = "install -d %s/isolinux" % isodir
        exec_cmd(install_cmd)

        self.do_configure_syslinux(isodir, cr, cr_workdir)

        install_cmd = "install -m 444 %s/syslinux/ldlinux.sys %s/isolinux/ldlinux.sys" \
            % (syslinux_dir, isodir)
        exec_cmd(install_cmd)

        install_cmd = "install -m 444 %s/syslinux/isohdpfx.bin %s/isolinux/isohdpfx.bin" \
            % (syslinux_dir, isodir)
        exec_cmd(install_cmd)

        install_cmd = "install -m 0644 %s/syslinux/isolinux.bin %s/isolinux/isolinux.bin" \
            % (syslinux_dir, isodir)
        exec_cmd(install_cmd)

        install_cmd = "install -m 0644 %s/syslinux/ldlinux.c32 %s/isolinux/ldlinux.c32" \
            % (syslinux_dir, isodir)
        exec_cmd(install_cmd)

        #create ISO image
        iso_img = "%s/tempiso_img.iso" % cr_workdir
        iso_bootimg = "isolinux/isolinux.bin"
        iso_bootcat = "isolinux/boot.cat"
        efi_img = "efi.img"

        mkisofs_cmd = "mkisofs -V %s " % part.label
        mkisofs_cmd += "-o %s " % iso_img
        mkisofs_cmd += "-U -J -joliet-long -r -iso-level 2 -b %s " % iso_bootimg
        mkisofs_cmd += "-c %s -no-emul-boot -boot-load-size 4 -boot-info-table " % iso_bootcat
        mkisofs_cmd += "-eltorito-alt-boot "
        mkisofs_cmd += "-eltorito-platform 0xEF -eltorito-boot %s " % efi_img
        mkisofs_cmd += "-no-emul-boot %s " % isodir

        msger.debug("running command: %s" % mkisofs_cmd)
        exec_native_cmd(mkisofs_cmd, native_sysroot)

        shutil.rmtree(isodir)

        du_cmd = "du -Lbks %s" % iso_img
        out = exec_cmd(du_cmd)
        isoimg_size = int(out.split()[0])

        part.set_size(isoimg_size)
        part.set_source_file(iso_img)
        self.iso_img = iso_img

    @classmethod
    def do_install_disk(self, disk, disk_name, cr, workdir, oe_builddir,
                        bootimg_dir, kernel_dir, native_sysroot):
        """
        Called after all partitions have been prepared and assembled into a
        disk image.  In this case, we insert/modify the MBR using isohybrid
        utility for booting via BIOS from disk storage devices.
        """

        full_path = cr._full_path(workdir, disk_name, "direct")
        full_path_iso = cr._full_path(workdir, disk_name, "iso")

        isohybrid_cmd = "isohybrid -u %s" % self.iso_img
        msger.debug("running command: %s" % \
                    isohybrid_cmd)
        exec_native_cmd(isohybrid_cmd, native_sysroot)

        msger.debug("Replaceing the image created by direct plugin ")
        os.remove(full_path)
        shutil.copy2(self.iso_img,full_path_iso)
        shutil.copy2(full_path_iso, full_path)

        os.remove(self.iso_img)
