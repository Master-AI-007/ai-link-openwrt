# Copyright (C) 2026 AI-LINK OpenWrt Project
# Licensed under the GNU General Public License v3.0.

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-ai-link
PKG_VERSION:=2.0.0
PKG_RELEASE:=r8
PKG_LICENSE:=GPL-3.0-only
PKG_MAINTAINER:=AI-LINK Team <dev@ai-link.org>
PKG_ARCH:=all

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-ai-link
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=AI-LINK Next-Gen Transparent Proxy & Ecosystem Hub
  DEPENDS:=+firewall4 +ip-full +kmod-nft-tproxy +kmod-nft-socket +kmod-tun +ca-bundle +curl +python3-light
  PKGARCH:=all
endef

define Package/luci-app-ai-link/description
  AI-LINK is a next-generation OpenWrt transparent proxy plugin combining a minimal LuCI
  control shell, a full-featured standalone Web dashboard (:9099), an L7 deep semantic
  availability auto-switching engine for AI & streaming platforms, and integrated
  AdGuardHome + Smart Dual-Stack DNS modules.
endef

define Package/luci-app-ai-link/conffiles
/etc/config/ai-link
/etc/ai-link/
endef

define Build/Compile
endef

define Package/luci-app-ai-link/install
	$(INSTALL_DIR) $(1)/etc/ai-link
	$(INSTALL_DATA) ./root/etc/ai-link/version $(1)/etc/ai-link/version
	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_CONF) ./root/etc/config/ai-link $(1)/etc/config/ai-link
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./root/etc/init.d/ai-link $(1)/etc/init.d/ai-link
	$(INSTALL_DIR) $(1)/lib/upgrade/keep.d
	$(INSTALL_DATA) ./root/lib/upgrade/keep.d/ai-link $(1)/lib/upgrade/keep.d/ai-link
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./root/usr/bin/ai-link $(1)/usr/bin/ai-link
	$(INSTALL_DIR) $(1)/usr/share/ai-link/nftables
	$(INSTALL_BIN) ./root/usr/share/ai-link/nftables/apply_nft.sh $(1)/usr/share/ai-link/nftables/apply_nft.sh
	$(INSTALL_BIN) ./root/usr/share/ai-link/nftables/normalize_nft_sets.py $(1)/usr/share/ai-link/nftables/normalize_nft_sets.py
	$(INSTALL_BIN) ./root/usr/share/ai-link/ai-link-daemon.py $(1)/usr/share/ai-link/ai-link-daemon.py
	$(INSTALL_DIR) $(1)/usr/share/ai-link/webui/static
	$(INSTALL_DIR) $(1)/usr/share/ai-link/webui/assets
	$(INSTALL_DIR) $(1)/usr/share/ai-link/webui/vendor
	$(INSTALL_DATA) ./root/usr/share/ai-link/webui/index.html $(1)/usr/share/ai-link/webui/index.html
	$(INSTALL_DATA) ./root/usr/share/ai-link/webui/static/tailwind.css $(1)/usr/share/ai-link/webui/static/tailwind.css
	$(INSTALL_DATA) ./root/usr/share/ai-link/webui/static/qrcode.min.js $(1)/usr/share/ai-link/webui/static/qrcode.min.js
	$(INSTALL_DATA) ./root/usr/share/ai-link/webui/static/three.min.js $(1)/usr/share/ai-link/webui/static/three.min.js
	$(INSTALL_DATA) ./root/usr/share/ai-link/webui/assets/tailwind.css $(1)/usr/share/ai-link/webui/assets/tailwind.css
	$(INSTALL_DATA) ./root/usr/share/ai-link/webui/vendor/qrcode.min.js $(1)/usr/share/ai-link/webui/vendor/qrcode.min.js
	$(INSTALL_DATA) ./root/usr/share/ai-link/webui/vendor/three.min.js $(1)/usr/share/ai-link/webui/vendor/three.min.js
	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d
	$(INSTALL_DATA) ./root/usr/share/luci/menu.d/luci-app-ai-link.json $(1)/usr/share/luci/menu.d/luci-app-ai-link.json
	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./root/usr/share/rpcd/acl.d/luci-app-ai-link.json $(1)/usr/share/rpcd/acl.d/luci-app-ai-link.json
	$(INSTALL_DIR) $(1)/www/luci-static/resources/view/ai-link
	$(INSTALL_DATA) ./htdocs/luci-static/resources/view/ai-link/overview.js $(1)/www/luci-static/resources/view/ai-link/overview.js
endef

define Package/luci-app-ai-link/postinst
#!/bin/sh
if [ -z "$${IPKG_INSTROOT}" ]; then
	chmod +x /etc/init.d/ai-link /usr/bin/ai-link /usr/share/ai-link/ai-link-daemon.py /usr/share/ai-link/nftables/apply_nft.sh /usr/share/ai-link/nftables/normalize_nft_sets.py
	/etc/init.d/ai-link enable >/dev/null 2>&1
	/etc/init.d/ai-link start >/dev/null 2>&1
	/etc/init.d/rpcd reload >/dev/null 2>&1
fi
exit 0
endef

define Package/luci-app-ai-link/prerm
#!/bin/sh
if [ -z "$${IPKG_INSTROOT}" ]; then
	/etc/init.d/ai-link stop >/dev/null 2>&1
	/etc/init.d/ai-link disable >/dev/null 2>&1
fi
exit 0
endef

$(eval $(call BuildPackage,luci-app-ai-link))
