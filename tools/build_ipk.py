#!/usr/bin/env python3
# build_ipk.py - Baut das NordVPN Enigma2 IPK-Paket

import os
import tarfile
import io
import xml.etree.ElementTree as ET

PLUGIN_NAME   = "enigma2-plugin-extensions-nordvpn"
ARCHITECTURE  = "all"
MAINTAINER    = "saufsoldat"
DESCRIPTION   = "NordVPN OpenVPN-Client fuer Enigma2"
HOMEPAGE      = "https://github.com/boingbasti/e2-nordvpn"
DEPENDS       = "openvpn"

PLUGIN_DEST = "/usr/lib/enigma2/python/Plugins/Extensions/NordVPN"
SBIN_DEST   = "/usr/sbin"

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

VERSION = ET.parse(os.path.join(PROJECT_DIR, "meta.xml")).findtext("version")
if not VERSION:
    raise SystemExit("FEHLER: Version nicht in meta.xml gefunden")

OUTPUT_FILE = os.path.join(PROJECT_DIR, f"{PLUGIN_NAME}_{VERSION}_{ARCHITECTURE}.ipk")

PLUGIN_FILES = ["__init__.py", "plugin.py", "manager.py", "plugin.png", "meta.xml"]
SBIN_FILES   = ["nordvpn-connect", "nordvpn-disconnect",
                "nordvpn-fetch-countries", "nordvpn-watchdog", "nordvpn-webif"]


POSTINST_SCRIPT = """\
#!/bin/sh
chmod +x /usr/sbin/nordvpn-connect \\
         /usr/sbin/nordvpn-disconnect \\
         /usr/sbin/nordvpn-fetch-countries \\
         /usr/sbin/nordvpn-watchdog \\
         /usr/sbin/nordvpn-webif
rm -f /usr/lib/enigma2/python/Plugins/Extensions/NordVPN/*.pyo
WDOG_PID=/var/run/nordvpn-watchdog.pid
if [ -f "$WDOG_PID" ] && [ -d "/proc/$(cat $WDOG_PID 2>/dev/null)" ]; then
    exit 0
fi
python /usr/sbin/nordvpn-watchdog &
"""

PRERM_SCRIPT = """\
#!/bin/sh
if [ -f /var/run/nordvpn-watchdog.pid ]; then
    kill "$(cat /var/run/nordvpn-watchdog.pid 2>/dev/null)" 2>/dev/null || true
    rm -f /var/run/nordvpn-watchdog.pid
fi
if [ -f /var/run/openvpn.nordvpn.pid ]; then
    kill "$(cat /var/run/openvpn.nordvpn.pid 2>/dev/null)" 2>/dev/null || true
    rm -f /var/run/openvpn.nordvpn.pid
fi
if [ -f /var/run/nordvpn-webif.pid ]; then
    kill "$(cat /var/run/nordvpn-webif.pid 2>/dev/null)" 2>/dev/null || true
    rm -f /var/run/nordvpn-webif.pid
fi
rm -f /etc/openvpn/nordvpn.conf
rm -f /var/log/nordvpn.log
rm -f /tmp/nordvpn_server.txt
rm -f /tmp/nordvpn_countries.json
rm -f /tmp/nordvpn_session
rm -f /tmp/nordvpn_extip.txt
rm -f /etc/resolv.conf.nordvpn.bak
rm -f /tmp/nordvpn_ipv6_states
if [ "$1" != "upgrade" ]; then
    rm -f /etc/openvpn/nordvpn_auth.txt
    rm -f /etc/enigma2/nordvpn.conf
fi
"""


def add_file(tar, src_path, arc_path, mode=0o644):
    with open(src_path, "rb") as f:
        data = f.read()
    info = tarfile.TarInfo(name=arc_path)
    info.size = len(data)
    info.mode = mode
    info.mtime = int(os.path.getmtime(src_path))
    tar.addfile(info, io.BytesIO(data))


def add_script(tar, arc_path, content):
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=arc_path)
    info.size = len(data)
    info.mode = 0o755
    tar.addfile(info, io.BytesIO(data))


def build_control_tar():
    control = (
        f"Package: {PLUGIN_NAME}\n"
        f"Version: {VERSION}\n"
        f"Architecture: {ARCHITECTURE}\n"
        f"Maintainer: {MAINTAINER}\n"
        f"Homepage: {HOMEPAGE}\n"
        f"Depends: {DEPENDS}\n"
        f"Section: misc\n"
        f"Priority: optional\n"
        f"License: GPL-2.0\n"
        f"Description: {DESCRIPTION}\n"
    ).encode("utf-8")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        info = tarfile.TarInfo(name="./control")
        info.size = len(control)
        tar.addfile(info, io.BytesIO(control))
        add_script(tar, "./postinst", POSTINST_SCRIPT)
        add_script(tar, "./prerm",    PRERM_SCRIPT)
    return buf.getvalue()


def build_data_tar():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        # Plugin-Verzeichnis
        dir_info = tarfile.TarInfo(name="./" + PLUGIN_DEST.lstrip("/"))
        dir_info.type = tarfile.DIRTYPE
        dir_info.mode = 0o755
        tar.addfile(dir_info)

        for fname in PLUGIN_FILES:
            src = os.path.join(PROJECT_DIR, fname)
            arc = "./" + PLUGIN_DEST.lstrip("/") + "/" + fname
            add_file(tar, src, arc, mode=0o644)

        # Skripte nach /usr/sbin/
        for fname in SBIN_FILES:
            src = os.path.join(PROJECT_DIR, fname)
            arc = "./" + SBIN_DEST.lstrip("/") + "/" + fname
            add_file(tar, src, arc, mode=0o755)

    return buf.getvalue()


def write_ar(path, members):
    with open(path, "wb") as f:
        f.write(b"!<arch>\n")
        for name, data in members:
            name_b  = name.encode("utf-8").ljust(16)[:16]
            mtime_b = b"0".ljust(12)
            uid_b   = b"0".ljust(6)
            gid_b   = b"0".ljust(6)
            mode_b  = b"100644".ljust(8)
            size_b  = str(len(data)).encode("utf-8").ljust(10)
            magic_b = b"\x60\x0a"
            f.write(name_b + mtime_b + uid_b + gid_b + mode_b + size_b + magic_b)
            f.write(data)
            if len(data) % 2 != 0:
                f.write(b"\n")


def main():
    for fname in PLUGIN_FILES + SBIN_FILES:
        path = os.path.join(PROJECT_DIR, fname)
        if not os.path.isfile(path):
            print(f"FEHLER: Quelldatei nicht gefunden: {path}")
            raise SystemExit(1)

    print("Baue control.tar.gz ...")
    control_tar = build_control_tar()

    print("Baue data.tar.gz ...")
    data_tar = build_data_tar()

    print(f"Schreibe {OUTPUT_FILE} ...")
    write_ar(OUTPUT_FILE, [
        ("debian-binary",  b"2.0\n"),
        ("control.tar.gz", control_tar),
        ("data.tar.gz",    data_tar),
    ])

    size_kb = os.path.getsize(OUTPUT_FILE) // 1024
    print(f"Fertig: {os.path.basename(OUTPUT_FILE)} ({size_kb} KB)")


if __name__ == "__main__":
    main()
