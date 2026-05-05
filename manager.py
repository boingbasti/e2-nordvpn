# -*- coding: utf-8 -*-
import os
import json
import ConfigParser

CONFIG_FILE = "/etc/enigma2/nordvpn.conf"
AUTH_FILE = "/etc/openvpn/nordvpn_auth.txt"
PID_FILE = "/var/run/openvpn.nordvpn.pid"
SERVER_FILE = "/tmp/nordvpn_server.txt"
LOG_FILE = "/var/log/nordvpn.log"

CONNECT_CMD = "/usr/sbin/nordvpn-connect"
DISCONNECT_CMD = "/usr/sbin/nordvpn-disconnect"


class NordVPNManager(object):

    def __init__(self):
        self._cfg = None

    @property
    def cfg(self):
        if self._cfg is None:
            self._cfg = ConfigParser.SafeConfigParser()
            self._cfg.read(CONFIG_FILE)
            if not self._cfg.has_section("nordvpn"):
                self._cfg.add_section("nordvpn")
        return self._cfg

    def _get(self, key, default=""):
        try:
            val = self.cfg.get("nordvpn", key)
            if isinstance(val, unicode):
                return val.encode("utf-8")
            return val
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return default

    def _set(self, key, value):
        if isinstance(value, unicode):
            value = value.encode("utf-8")
        self.cfg.set("nordvpn", key, str(value))
        with open(CONFIG_FILE, "w") as f:
            self.cfg.write(f)

    def get_country_id(self):
        try:
            return int(self._get("country_id", "81"))
        except ValueError:
            return 81

    def get_country_name(self):
        return self._get("country_name", "Germany")

    def set_country(self, country_id, country_name):
        self.cfg.set("nordvpn", "country_id", str(country_id))
        self.cfg.set("nordvpn", "country_name", country_name)
        with open(CONFIG_FILE, "w") as f:
            self.cfg.write(f)

    def get_protocol(self):
        return self._get("protocol", "udp")

    def set_protocol(self, proto):
        self._set("protocol", proto)

    def get_autostart(self):
        return self._get("autostart", "0") == "1"

    def set_autostart(self, enabled):
        self._set("autostart", "1" if enabled else "0")

    def save_credentials(self, username, password):
        auth_dir = os.path.dirname(AUTH_FILE)
        if not os.path.isdir(auth_dir):
            os.makedirs(auth_dir)
        with open(AUTH_FILE, "w") as f:
            f.write("%s\n%s\n" % (username.strip(), password.strip()))
        os.chmod(AUTH_FILE, 0o600)

    def has_auth(self):
        return os.path.isfile(AUTH_FILE) and os.path.getsize(AUTH_FILE) > 5

    def get_username(self):
        try:
            with open(AUTH_FILE) as f:
                return f.readline().strip()
        except Exception:
            return ""

    def get_current_server(self):
        try:
            if os.path.isfile(SERVER_FILE):
                with open(SERVER_FILE) as f:
                    return f.read().strip()
        except Exception:
            pass
        return ""

    def is_connected(self):
        if not os.path.isfile(PID_FILE):
            return False
        try:
            with open(PID_FILE) as f:
                pid = f.read().strip()
            return bool(pid) and os.path.isdir("/proc/%s" % pid)
        except Exception:
            return False

    def get_status_text(self):
        if self.is_connected():
            srv = self.get_current_server()
            if srv:
                return "Verbunden mit %s" % srv
            return "Verbunden"
        return "Getrennt"

    def get_recent_countries(self):
        try:
            return json.loads(self._get("recent_countries", "[]"))
        except Exception:
            return []

    def add_recent_country(self, country_id, country_name):
        recent = self.get_recent_countries()
        recent = [c for c in recent if c[0] != country_id]
        recent.insert(0, [country_id, country_name])
        self._set("recent_countries", json.dumps(recent[:5]))

    def get_connect_cmd(self):
        return "%s %d %s" % (
            CONNECT_CMD,
            self.get_country_id(),
            self.get_protocol(),
        )

    def get_disconnect_cmd(self):
        return DISCONNECT_CMD


manager = NordVPNManager()
