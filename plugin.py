# -*- coding: utf-8 -*-
import os
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigNothing, ConfigSelection, getConfigListEntry, NoSave
# ConfigListScreen/config imports kept for potential future use
from enigma import eConsoleAppContainer, eTimer

from Tools.Notifications import AddPopup

from Plugins.Extensions.NordVPN.manager import manager


# ---------------------------------------------------------------------------
# Country selection screen
# ---------------------------------------------------------------------------

class NordVPNCountryList(Screen):
    skin = """
        <screen position="center,center" size="700,520" title="Land auswählen">
            <widget name="list"       position="10,10"  size="680,450"
                    font="Regular;26" itemHeight="42" scrollbarMode="showOnDemand"/>
            <widget name="key_red"    position="10,468" size="200,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#9f1313"/>
            <widget name="key_hint"   position="250,468" size="440,44"
                    font="Regular;22" halign="center" valign="center" foregroundColor="#888888"/>
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self._countries = []

        self["list"] = MenuList([])
        self["key_red"] = Label("Abbrechen")
        self["key_hint"] = Label("OK = Auswählen")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {"ok": self._select, "cancel": self.close, "red": self.close},
            -1,
        )


        self._json_file = "/tmp/nordvpn_countries.json"
        self._container = eConsoleAppContainer()
        self._container.appClosed.append(self._on_done)
        self._container.execute("python /usr/sbin/nordvpn-fetch-countries")

    def _on_done(self, retval):
        import json
        try:
            with open(self._json_file) as f:
                data = json.load(f)
            all_countries = sorted(
                [(c["name"].encode("utf-8"), c["id"]) for c in data],
                key=lambda x: x[0],
            )
            recent = manager.get_recent_countries()
            self._countries = []
            display = []
            if recent:
                display.append("  -- Zuletzt gewaehlt --")
                self._countries.append(None)
                for cid, cname in recent:
                    name = cname.encode("utf-8") if isinstance(cname, unicode) else cname
                    self._countries.append((name, cid))
                    display.append("  " + name)
                display.append("  -- Alle Laender --")
                self._countries.append(None)
            for item in all_countries:
                self._countries.append(item)
                display.append(item[0])
            self["list"].setList(display)
        except Exception as e:
            self.session.open(
                MessageBox,
                "Laenderliste konnte nicht geladen werden:\n%s" % str(e),
                MessageBox.TYPE_ERROR,
                timeout=5,
            )

    def _select(self):
        idx = self["list"].getSelectedIndex()
        if 0 <= idx < len(self._countries):
            entry = self._countries[idx]
            if entry is None:
                return
            name, cid = entry
            manager.add_recent_country(cid, name)
            self.close((cid, name))
        else:
            self.close(None)


# ---------------------------------------------------------------------------
# Settings screen
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Credentials entry screen (plain Screen, no ConfigList interference)
# ---------------------------------------------------------------------------

class NordVPNCredentials(Screen):
    skin = """
        <screen position="center,center" size="740,300" title="NordVPN Zugangsdaten">
            <widget name="info"      position="20,20"  size="700,160"
                    font="Regular;23" halign="center" valign="center" foregroundColor="#888888"/>
            <widget name="key_green" position="20,240" size="210,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#1f771f"/>
            <widget name="key_red"   position="510,240" size="210,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#9f1313"/>
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["info"] = Label(
            "Service Credentials eingeben\n"
            "(NICHT Login-Passwort / Access Token!)\n\n"
            "nordvpn.com → Services → NordVPN → Set up manually"
        )
        self["key_green"] = Label("Eingeben")
        self["key_red"]   = Label("Abbrechen")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok":     self._start,
                "green":  self._start,
                "cancel": self.close,
                "red":    self.close,
            },
            -1,
        )

    def _start(self):
        self.session.openWithCallback(
            self._got_username,
            VirtualKeyBoard,
            title="Service Username:",
            text=manager.get_username() or " ",
        )

    def _got_username(self, username):
        if not username or not username.strip():
            return
        self._username = username.strip()
        self.session.openWithCallback(
            self._got_password,
            VirtualKeyBoard,
            title="Service Passwort:",
            text=" ",
        )

    def _got_password(self, password):
        if password and password.strip():
            manager.save_credentials(self._username, password.strip())
            self.session.open(
                MessageBox, "Zugangsdaten gespeichert.",
                MessageBox.TYPE_INFO, timeout=3,
            )
        self.close(True)


# ---------------------------------------------------------------------------
# Settings screen
# ---------------------------------------------------------------------------

class NordVPNSettings(Screen):
    skin = """
        <screen position="center,center" size="800,560" title="NordVPN Einstellungen">
            <widget name="list"    position="20,20"  size="760,390"
                    font="Regular;26" itemHeight="42" scrollbarMode="showOnDemand"/>
            <widget name="hint"    position="20,428" size="760,76"
                    font="Regular;20" foregroundColor="#888888"/>
            <widget name="key_red" position="20,516" size="180,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#9f1313"/>
        </screen>
    """

    _IDX_CREDS   = 0
    _IDX_COUNTRY = 1
    _IDX_PROTO   = 2
    _IDX_AUTO    = 3

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"]    = MenuList([])
        self["hint"]    = Label(
            "OK = Auswählen/Ändern   links/rechts = Protokoll/Autostart\n"
            "Credentials: nordvpn.com → Services → NordVPN → Set up manually"
        )
        self["key_red"] = Label("Zurück")
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok":     self._keyOK,
                "cancel": self.close,
                "red":    self.close,
                "left":   self._keyLeft,
                "right":  self._keyRight,
            },
            -1,
        )
        self._refresh()

    def _entries(self):
        creds = "*** gesetzt ***" if manager.has_auth() else "(nicht gesetzt)"
        proto = manager.get_protocol().upper()
        auto  = "Ein" if manager.get_autostart() else "Aus"
        return [
            "Zugangsdaten:   " + creds,
            "Land:           " + manager.get_country_name(),
            "Protokoll:      " + proto,
            "Autostart:      " + auto,
        ]

    def _refresh(self):
        self["list"].setList(self._entries())

    def _keyOK(self):
        idx = self["list"].getSelectedIndex()
        if idx == self._IDX_CREDS:
            self.session.openWithCallback(self._refresh_cb, NordVPNCredentials)
        elif idx == self._IDX_COUNTRY:
            self.session.openWithCallback(self._country_chosen, NordVPNCountryList)
        elif idx == self._IDX_PROTO:
            self._toggle_proto()
        elif idx == self._IDX_AUTO:
            self._toggle_auto()

    def _refresh_cb(self, result=None):
        self._refresh()

    def _country_chosen(self, result=None):
        if result:
            country_id, country_name = result
            manager.set_country(country_id, country_name)
        self._refresh()

    def _toggle_proto(self):
        manager.set_protocol("tcp" if manager.get_protocol() == "udp" else "udp")
        self._refresh()

    def _toggle_auto(self):
        manager.set_autostart(not manager.get_autostart())
        self._refresh()

    def _keyLeft(self):
        idx = self["list"].getSelectedIndex()
        if idx == self._IDX_PROTO:
            self._toggle_proto()
        elif idx == self._IDX_AUTO:
            self._toggle_auto()

    def _keyRight(self):
        self._keyLeft()


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------

class NordVPNMain(Screen):
    skin = """
        <screen position="center,center" size="900,510" title="NordVPN">
            <widget name="status_lbl"  position="20,20"  size="860,56"
                    font="Regular;38" halign="center" valign="center"/>
            <widget name="server_lbl"  position="20,84"  size="860,34"
                    font="Regular;26" halign="center" foregroundColor="#888888"/>
            <widget name="ip_lbl"      position="20,120" size="860,30"
                    font="Regular;22" halign="center" foregroundColor="#888888"/>
            <widget name="country_lbl" position="20,156" size="860,34"
                    font="Regular;24" halign="center" foregroundColor="#4488ff"/>
            <widget name="log_lbl"     position="20,198" size="860,178"
                    font="Regular;20" foregroundColor="#aaaaaa"/>

            <widget name="key_red"     position="20,420"  size="205,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#9f1313"/>
            <widget name="key_green"   position="245,420" size="205,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#1f771f"/>
            <widget name="key_yellow"  position="470,420" size="205,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#a07000"/>
            <widget name="key_blue"    position="695,420" size="185,44"
                    font="Regular;24" halign="center" valign="center" backgroundColor="#18188b"/>
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self._con_container = eConsoleAppContainer()
        self._con_container.dataAvail.append(self._on_output)
        self._con_container.appClosed.append(self._on_connect_done)
        self._dc_container = eConsoleAppContainer()
        self._dc_container.dataAvail.append(self._on_output)
        self._dc_container.appClosed.append(self._on_disconnect_done)
        self._ip_container = eConsoleAppContainer()
        self._ip_container.appClosed.append(self._on_ip_done)
        self._log_buf = ""
        self._prev_connected = None

        self["status_lbl"] = Label("")
        self["server_lbl"] = Label("")
        self["ip_lbl"]     = Label("")
        self["country_lbl"] = Label("")
        self["log_lbl"] = Label("")
        self["key_red"] = Label("")
        self["key_green"] = Label("")
        self["key_yellow"] = Label("Einstellungen")
        self["key_blue"] = Label("Beenden")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self._connect,
                "cancel": self.close,
                "green": self._connect,
                "red": self._disconnect,
                "yellow": self._open_settings,
                "blue": self.close,
            },
            -1,
        )

        self._timer = eTimer()
        self._timer.callback.append(self._update_status)
        self._timer.start(3000, False)
        self._ip_timer = eTimer()
        self._ip_timer.callback.append(self._fetch_ip)
        self._update_status()

    def _update_status(self):
        connected = manager.is_connected()
        if connected != self._prev_connected:
            if connected:
                self._ip_timer.start(5000, True)
            else:
                self._ip_timer.stop()
                self["ip_lbl"].setText("")
            self._prev_connected = connected
        if connected:
            self["status_lbl"].setText("Verbunden")
            srv = manager.get_current_server()
            self["server_lbl"].setText(srv if srv else "")
            self["key_red"].setText("Trennen")
            self["key_green"].setText("")
        else:
            self["status_lbl"].setText("Getrennt")
            self["server_lbl"].setText("")
            self["key_red"].setText("")
            self["key_green"].setText("Verbinden")
        self["country_lbl"].setText(
            ("Land: %s  |  Protokoll: %s" % (
                manager.get_country_name(),
                manager.get_protocol().upper(),
            )).encode("utf-8")
        )

    def _fetch_ip(self):
        if manager.is_connected():
            self._ip_container.execute(
                "wget -q -O /tmp/nordvpn_extip.txt http://ip4.me/api/"
            )

    def _on_ip_done(self, retval):
        if retval != 0:
            return
        try:
            data = open("/tmp/nordvpn_extip.txt").read().strip()
            ip = data.split(",")[1]
            self["ip_lbl"].setText(ip)
        except Exception:
            pass

    def _on_output(self, data):
        self._log_buf += data
        lines = self._log_buf.strip().splitlines()
        self["log_lbl"].setText("\n".join(lines[-6:]))

    def _on_connect_done(self, retval):
        self._update_status()
        if retval != 0:
            self.session.open(
                MessageBox,
                "Fehler beim Verbinden:\n" + self._log_buf[-300:],
                MessageBox.TYPE_ERROR,
                timeout=8,
            )

    def _on_disconnect_done(self, retval):
        self._update_status()

    def _connect(self):
        if not manager.has_auth():
            self.session.open(
                MessageBox,
                "Bitte zuerst die Service Credentials in den Einstellungen eintragen.",
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return
        if self._con_container.running():
            return
        self._log_buf = ""
        self["log_lbl"].setText("Verbinde...")
        self["status_lbl"].setText("Verbinde...")
        self["key_red"].setText("")
        self["key_green"].setText("")
        self._con_container.execute(manager.get_connect_cmd())

    def _disconnect(self):
        if self._dc_container.running():
            return
        self._log_buf = ""
        self["log_lbl"].setText("")
        self["status_lbl"].setText("Trenne...")
        self["key_red"].setText("")
        self["key_green"].setText("")
        self._dc_container.execute(manager.get_disconnect_cmd())

    def _open_settings(self):
        self.session.openWithCallback(lambda *a: self._update_status(), NordVPNSettings)

    def close(self):
        self._timer.stop()
        Screen.close(self)


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def main(session, **kwargs):
    session.open(NordVPNMain)


_status_timer = None
_last_vpn_status = None


def _check_vpn_status():
    global _last_vpn_status
    current = manager.is_connected()
    if _last_vpn_status is not None and current != _last_vpn_status:
        if current:
            srv = manager.get_current_server()
            msg = ("NordVPN verbunden" + (" – " + srv if srv else "")).encode("utf-8")
            AddPopup(msg, MessageBox.TYPE_INFO, timeout=5, id="nordvpn_notify")
        else:
            AddPopup("NordVPN getrennt!", MessageBox.TYPE_WARNING, timeout=8, id="nordvpn_notify")
    _last_vpn_status = current


def autostart(reason, **kwargs):
    global _status_timer
    if reason != 0:
        return
    import subprocess
    watchdog_pid = "/var/run/nordvpn-watchdog.pid"
    if os.path.isfile(watchdog_pid):
        try:
            pid = open(watchdog_pid).read().strip()
            if pid and os.path.isdir("/proc/%s" % pid):
                os.kill(int(pid), 15)
        except Exception:
            pass
    subprocess.Popen(["python", "/usr/sbin/nordvpn-watchdog"])
    if manager.get_autostart():
        subprocess.Popen(
            ["python", "/usr/sbin/nordvpn-connect",
             str(manager.get_country_id()),
             manager.get_protocol()],
        )
    _status_timer = eTimer()
    _status_timer.callback.append(_check_vpn_status)
    _status_timer.start(5000, False)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="NordVPN",
            description="NordVPN Client für Enigma2",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main,
        ),
        PluginDescriptor(
            name="NordVPN",
            where=PluginDescriptor.WHERE_AUTOSTART,
            fnc=autostart,
        ),
    ]
