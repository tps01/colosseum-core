FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://colosseum-sshd.conf"

do_install:append() {
    install -d ${D}${sysconfdir}/ssh/sshd_config.d
    install -m 0644 ${WORKDIR}/colosseum-sshd.conf ${D}${sysconfdir}/ssh/sshd_config.d/colosseum.conf
}
