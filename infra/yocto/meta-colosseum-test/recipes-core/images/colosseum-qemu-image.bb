require recipes-core/images/core-image-minimal.bb

DESCRIPTION = "QEMU image for Colosseum regression (SSH DUT, offline pip install, X11 GUI)"

IMAGE_INSTALL:append = " \
    python3 \
    python3-pip \
    python3-venv \
    python3-tkinter \
    openssh \
    openssh-sftp-server \
    xauth \
    libx11 \
    libxext \
    libxrender \
    libsm \
    libice \
    grep \
    gawk \
    sed \
    findutils \
    colosseum-guest-identify \
    os-release \
    "

IMAGE_FEATURES += "ssh-server-openssh"
EXTRA_IMAGE_FEATURES += "debug-tweaks"

# Colosseum offline venv + wheels need headroom beyond core-image-minimal.
IMAGE_ROOTFS_EXTRA_SPACE = "1048576"
# Keep /etc/version from write_colosseum_version (reproducible stamp would overwrite it).
ROOTFS_REPRODUCIBLE = "0"

# Dev regression image only: empty root password, root SSH login allowed.
# Do not deploy to production systems.

write_colosseum_version() {
    echo "v0.1.0-colosseum-qemu" > ${IMAGE_ROOTFS}/etc/version
}
ROOTFS_POSTPROCESS_COMMAND:remove = "rootfs_reproducible;"
ROOTFS_POSTPROCESS_COMMAND:append = "write_colosseum_version; "
