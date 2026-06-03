SUMMARY = "Colosseum QEMU guest identity files for SSH regression"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

PV = "1.0"
PR = "r0"

S = "${WORKDIR}"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

do_install() {
    install -d ${D}${sysconfdir}
    echo "v0.1.0-colosseum-qemu" > ${D}${sysconfdir}/version
}

FILES:${PN} = "${sysconfdir}/version"
