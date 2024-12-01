# Copyright 2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

DISTUTILS_USE_PEP517=setuptools
PYTHON_COMPAT=( python3_{10..13} )

inherit distutils-r1 desktop xdg

if [[ ${PV} == *9999 ]]; then
	inherit git-r3
	EGIT_REPO_URI="https://github.com/justin025/onthespot.git"
else
	SRC_URI="https://github.com/justin025/onthespot/archive/refs/tags/v${PV}.tar.gz
			 -> ${P}.tar.gz"
	KEYWORDS="~amd64"
fi

DESCRIPTION="qt based music downloader written in python"
HOMEPAGE="https://github.com/justin025/onthespot"

LICENSE="GPL-2"
SLOT="0"

BDEPEND="
	dev-python/packaging
"

RDEPEND="
	dev-python/flask
	dev-python/librespot
	dev-python/music-tag
	dev-python/pillow
	dev-python/pyperclip
	dev-python/pyqt6[network,widgets]
	dev-python/requests
	dev-python/urllib3
	media-libs/mutagen
	media-video/ffmpeg[mp3,openssl,sdl]
	net-misc/yt-dlp
"

src_install() {
	distutils-r1_src_install

	domenu "${S}"/src/onthespot/resources/org.onthespot.OnTheSpot.desktop
	newicon -s 256 "${S}"/src/onthespot/resources/icons/onthespot.png onthespot.png
}
