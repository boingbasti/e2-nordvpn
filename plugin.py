# -*- coding: utf-8 -*-
import os
try:
    import xml.etree.ElementTree as _ET
    _meta = _ET.parse(os.path.join(os.path.dirname(__file__), "meta.xml"))
    VERSION = _meta.findtext("version") or "?"
except Exception:
    VERSION = "?"
import time
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigNothing, ConfigSelection, getConfigListEntry, NoSave
from enigma import eConsoleAppContainer, eTimer, gRGB

try:
    from enigma import getDesktop as _getDesktop
    IS_FHD = _getDesktop(0).size().width() > 1280
except Exception:
    IS_FHD = True

from Tools.Notifications import AddPopup
from Plugins.Extensions.NordVPN.manager import manager

import sys
PY3 = sys.version_info[0] >= 3

if PY3:
    unicode = str
    def to_unicode(s):
        if isinstance(s, bytes):
            return s.decode("utf-8", "ignore")
        return str(s)
    def to_native_str(s):
        if isinstance(s, bytes):
            return s.decode("utf-8", "ignore")
        return str(s)
else:
    def to_unicode(s):
        if isinstance(s, str):
            return s.decode("utf-8", "ignore")
        return unicode(s)
    def to_native_str(s):
        if isinstance(s, unicode):
            return s.encode("utf-8")
        return str(s)

# ---------------------------------------------------------------------------
# Country selection screen
# ---------------------------------------------------------------------------

class NordVPNCountryList(Screen):

    _SKIN_FHD = """
        <screen position="0,0" size="1920,1080" flags="wfNoBorder">
            <eLabel position="0,0"    size="1920,1080" backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="320,180" size="1280,748" backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="320,180" size="1280,80"  backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="320,260" size="1280,3"   backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="320,836" size="1280,2"   backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="320,838" size="1280,90"  backgroundColor="#1A000000" zPosition="-4"/>
            <widget name="title_lbl" position="340,188" size="900,64"
                    font="Regular;40" valign="center" foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="list"      position="340,268" size="1200,560"
                    font="Regular;34" itemHeight="54" scrollbarMode="showOnDemand"
                    foregroundColor="#e0e0e0" backgroundColor="#33000000"
                    transparent="1"/>
            <eLabel position="340,856" size="8,54" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"   position="356,838" size="280,90"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <widget name="key_hint"  position="660,838" size="900,90"
                    font="Regular;32" valign="center" foregroundColor="#888888" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    _SKIN_HD = """
        <screen position="0,0" size="1280,720" flags="wfNoBorder">
            <eLabel position="0,0"    size="1280,720"  backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="215,120" size="850,500"  backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="215,120" size="850,54"   backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="215,174" size="850,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="215,558" size="850,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="215,560" size="850,60"   backgroundColor="#1A000000" zPosition="-4"/>
            <widget name="title_lbl" position="228,124" size="600,46"
                    font="Regular;28" valign="center" foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="list"      position="228,180" size="814,372"
                    font="Regular;26" itemHeight="42" scrollbarMode="showOnDemand"
                    foregroundColor="#e0e0e0" backgroundColor="#33000000"
                    transparent="1"/>
            <eLabel position="228,575" size="5,30" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"   position="240,560" size="184,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <widget name="key_hint"  position="440,560" size="596,60"
                    font="Regular;21" valign="center" foregroundColor="#888888" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    skin = ""

    def __init__(self, session):
        self.skin = self._SKIN_FHD if IS_FHD else self._SKIN_HD
        Screen.__init__(self, session)
        self._countries = []

        self["title_lbl"] = Label(to_native_str(u"Land auswählen"))
        self["list"]     = MenuList([])
        self["key_red"]  = Label(to_native_str(u"Abbrechen"))
        self["key_hint"] = Label(to_native_str(u"OK = Auswählen"))
        self["actions"]  = ActionMap(
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
                [(to_native_str(c["name"]), c["id"]) for c in data],
                key=lambda x: x[0],
            )
            recent = manager.get_recent_countries()
            self._countries = []
            display = []
            if recent:
                display.append(to_native_str(u"  -- Zuletzt gewählt --"))
                self._countries.append(None)
                for cid, cname in recent:
                    name = to_native_str(cname)
                    self._countries.append((name, cid))
                    display.append("  " + name)
                display.append(to_native_str(u"  -- Alle Länder --"))
                self._countries.append(None)
            for item in all_countries:
                self._countries.append(item)
                display.append(item[0])
            self["list"].setList(display)
        except Exception as e:
            self.session.open(
                MessageBox,
                to_native_str(u"Länderliste konnte nicht geladen werden:\n%s") % to_unicode(str(e)),
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
# Credentials entry screen
# ---------------------------------------------------------------------------

class NordVPNCredentials(Screen):

    _SKIN_FHD = """
        <screen position="0,0" size="1920,1080" flags="wfNoBorder">
            <eLabel position="0,0"    size="1920,1080" backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="510,320" size="900,468"  backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="510,320" size="900,80"   backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="510,400" size="900,3"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="510,700" size="900,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="510,702" size="900,86"   backgroundColor="#1A000000" zPosition="-4"/>
            <widget name="title_lbl" position="530,328" size="860,64"
                    font="Regular;40" halign="center" valign="center"
                    foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="info"      position="530,412" size="860,278"
                    font="Regular;28" halign="center" valign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <eLabel position="530,727" size="8,54" backgroundColor="#00BB00" zPosition="1"/>
            <widget name="key_green" position="546,702" size="370,86"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="940,727" size="8,54" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"   position="956,702" size="426,86"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    _SKIN_HD = """
        <screen position="0,0" size="1280,720" flags="wfNoBorder">
            <eLabel position="0,0"    size="1280,720"  backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="340,213" size="600,317"  backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="340,213" size="600,54"   backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="340,267" size="600,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="340,468" size="600,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="340,470" size="600,60"   backgroundColor="#1A000000" zPosition="-4"/>
            <widget name="title_lbl" position="354,217" size="572,50"
                    font="Regular;28" halign="center" valign="center"
                    foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="info"      position="354,274" size="572,188"
                    font="Regular;20" halign="center" valign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <eLabel position="354,485" size="5,30" backgroundColor="#00BB00" zPosition="1"/>
            <widget name="key_green" position="366,470" size="248,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="628,485" size="5,30" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"   position="640,470" size="286,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    skin = ""

    def __init__(self, session):
        self.skin = self._SKIN_FHD if IS_FHD else self._SKIN_HD
        Screen.__init__(self, session)
        self["title_lbl"] = Label("NordVPN Zugangsdaten")
        self["info"] = Label(
            "Service Credentials eingeben\n"
            "(NICHT Login-Passwort / Access Token!)\n\n"
            "nordvpn.com - Mein Konto - NordVPN - Manuelle Einrichtung - Service-Anmeldedaten"
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
            self.session.openWithCallback(
                lambda *a: self.close(True),
                MessageBox, "Zugangsdaten gespeichert.",
                MessageBox.TYPE_INFO, timeout=3,
            )
        else:
            self.close(True)


# ---------------------------------------------------------------------------
# Settings screen
# ---------------------------------------------------------------------------

class NordVPNSettings(Screen):

    _SKIN_FHD = """
        <screen position="0,0" size="1920,1080" flags="wfNoBorder">
            <eLabel position="0,0"    size="1920,1080" backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="320,180" size="1280,748" backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="320,180" size="1280,80"  backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="320,260" size="1280,3"   backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="320,836" size="1280,2"   backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="320,838" size="1280,90"  backgroundColor="#1A000000" zPosition="-4"/>
            <widget name="title_lbl" position="340,188" size="900,64"
                    font="Regular;40" valign="center" foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="list"     position="340,268" size="1200,560"
                    font="Regular;32" itemHeight="62" scrollbarMode="showOnDemand"
                    foregroundColor="#e0e0e0" backgroundColor="#33000000"
                    transparent="1"/>
            <eLabel position="340,856" size="8,54" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"  position="356,838" size="280,90"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <widget name="key_hint" position="660,838" size="900,90"
                    font="Regular;32" valign="center" foregroundColor="#888888" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    _SKIN_HD = """
        <screen position="0,0" size="1280,720" flags="wfNoBorder">
            <eLabel position="0,0"    size="1280,720"  backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="215,120" size="850,500"  backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="215,120" size="850,54"   backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="215,174" size="850,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="215,558" size="850,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="215,560" size="850,60"   backgroundColor="#1A000000" zPosition="-4"/>
            <widget name="title_lbl" position="228,124" size="600,46"
                    font="Regular;28" valign="center" foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="list"     position="228,180" size="814,372"
                    font="Regular;24" itemHeight="46" scrollbarMode="showOnDemand"
                    foregroundColor="#e0e0e0" backgroundColor="#33000000"
                    transparent="1"/>
            <eLabel position="228,575" size="5,30" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"  position="240,560" size="184,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <widget name="key_hint" position="440,560" size="596,60"
                    font="Regular;21" valign="center" foregroundColor="#888888" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    skin = ""

    _IDX_CREDS   = 0
    _IDX_COUNTRY = 1
    _IDX_PROTO   = 2
    _IDX_AUTO    = 3
    _IDX_WEBIF   = 4
    _IDX_STYPE   = 5
    _IDX_SFIX    = 6
    _IDX_DNS     = 7

    def __init__(self, session):
        self.skin = self._SKIN_FHD if IS_FHD else self._SKIN_HD
        Screen.__init__(self, session)
        self["title_lbl"] = Label(to_native_str(u"Einstellungen"))
        self["list"]     = MenuList([])
        self["key_red"]  = Label(to_native_str(u"Zurück"))
        self["key_hint"] = Label(to_native_str(u"OK = Ändern"))
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
        self._webif_was_running = False
        self._webif_timer = eTimer()
        self._webif_timer.callback.append(self._check_webif)
        self._webif_timer.start(2000, False)
        self._refresh()

    def _entries(self):
        creds = to_native_str(u"*** gesetzt ***" if manager.has_auth() else u"(nicht gesetzt)")
        proto = to_native_str(manager.get_protocol().upper())
        auto  = to_native_str(u"Ein" if manager.get_autostart() else u"Aus")
        webif = to_native_str(u"Läuft  (Port %d)" % 8765) if manager.is_webif_running() else to_native_str(u"Starten")
        stype = to_native_str(u"P2P" if manager.get_server_type() == "p2p" else u"Standard")
        sfix  = to_native_str(u"Ein" if manager.get_streaming_fix() else u"Aus")
        dns_names = {"nordvpn": u"NordVPN (Standard)", "google": u"Google (8.8.8.8)", "cloudflare": u"Cloudflare (1.1.1.1)"}
        dns_val = to_native_str(dns_names.get(manager.get_dns_type(), u"NordVPN (Standard)"))
        return [
            to_native_str(u"Zugangsdaten:   ") + creds,
            to_native_str(u"Land:           ") + to_native_str(manager.get_country_name()),
            to_native_str(u"Protokoll:      ") + proto,
            to_native_str(u"Autostart:      ") + auto,
            to_native_str(u"Zugangsdaten per WebIF: ") + webif,
            to_native_str(u"Server-Typ:     ") + stype,
            to_native_str(u"Mediathek-Fix:  ") + sfix,
            to_native_str(u"DNS-Server:     ") + dns_val,
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
        elif idx == self._IDX_WEBIF:
            self._webif_action()
        elif idx == self._IDX_STYPE:
            self._toggle_stype()
        elif idx == self._IDX_SFIX:
            self._toggle_sfix()
        elif idx == self._IDX_DNS:
            self._toggle_dns()

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

    def _toggle_stype(self):
        manager.set_server_type("p2p" if manager.get_server_type() == "standard" else "standard")
        self._refresh()

    def _toggle_sfix(self):
        manager.set_streaming_fix(not manager.get_streaming_fix())
        self._refresh()

    def _toggle_dns(self):
        dns_list = ["nordvpn", "google", "cloudflare"]
        current = manager.get_dns_type()
        try:
            next_idx = (dns_list.index(current) + 1) % len(dns_list)
        except ValueError:
            next_idx = 0
        manager.set_dns_type(dns_list[next_idx])
        self._refresh()

    def _check_webif(self):
        running = manager.is_webif_running()
        if running != self._webif_was_running:
            self._webif_was_running = running
            self._refresh()

    def close(self):
        self._webif_timer.stop()
        Screen.close(self)

    def _webif_action(self):
        if manager.is_webif_running():
            manager.stop_webif()
            self._refresh()
        else:
            manager.start_webif()
            url = manager.get_webif_url()
            self.session.openWithCallback(
                lambda *a: self._refresh(),
                MessageBox,
                "WebIF gestartet:\n%s\n\nIm Browser \xc3\xb6ffnen und Zugangsdaten eingeben.\nStoppt automatisch nach 5 Minuten." % url,
                MessageBox.TYPE_INFO,
                timeout=15,
            )

    def _keyLeft(self):
        idx = self["list"].getSelectedIndex()
        if idx == self._IDX_PROTO:
            self._toggle_proto()
        elif idx == self._IDX_AUTO:
            self._toggle_auto()
        elif idx == self._IDX_STYPE:
            self._toggle_stype()
        elif idx == self._IDX_SFIX:
            self._toggle_sfix()
        elif idx == self._IDX_DNS:
            self._toggle_dns()

    def _keyRight(self):
        self._keyLeft()


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------

def _fmt_duration(secs):
    secs = int(secs)
    d = secs // 86400
    h = (secs % 86400) // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if d > 0:
        return "%dd %d:%02d:%02d" % (d, h, m, s)
    if h > 0:
        return "%d:%02d:%02d" % (h, m, s)
    return "%02d:%02d" % (m, s)


def _fmt_bytes(n):
    if n < 0:
        n = 0
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024.0)
    if n < 1024 * 1024 * 1024:
        return "%.1f MB" % (n / (1024.0 * 1024))
    return "%.2f GB" % (n / (1024.0 * 1024 * 1024))


class NordVPNMain(Screen):

    _SKIN_FHD = """
        <screen position="0,0" size="1920,1080" flags="wfNoBorder">
            <eLabel position="0,0"    size="1920,1080" backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="320,180" size="1280,748" backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="320,180" size="1280,80"  backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="320,260" size="1280,3"   backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="320,836" size="1280,2"   backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="320,838" size="1280,90"  backgroundColor="#1A000000" zPosition="-4"/>
            <eLabel position="330,524" size="1260,310" backgroundColor="#20000000" zPosition="-2"/>
            <widget name="title_lbl"   position="340,188" size="900,64"
                    font="Regular;40" valign="center" foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="status_lbl"  position="340,268" size="1200,68"
                    font="Regular;60" halign="center" valign="center"
                    foregroundColor="#e0e0e0" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="server_lbl"  position="340,342" size="1200,36"
                    font="Regular;32" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="ip_lbl"      position="340,382" size="1200,32"
                    font="Regular;28" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="country_lbl" position="340,418" size="1200,32"
                    font="Regular;28" halign="center"
                    foregroundColor="#4ecdc4" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="city_lbl"    position="340,454" size="1200,32"
                    font="Regular;28" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="transfer_lbl" position="340,490" size="1200,32"
                    font="Regular;28" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="log_lbl"     position="340,528" size="1240,300"
                    font="Regular;24" foregroundColor="#888888" backgroundColor="#20000000"
                    transparent="1"/>
            <eLabel position="340,856" size="8,54" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"     position="356,838" size="272,90"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="660,856" size="8,54" backgroundColor="#00BB00" zPosition="1"/>
            <widget name="key_green"   position="676,838" size="272,90"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="980,856" size="8,54" backgroundColor="#FFD700" zPosition="1"/>
            <widget name="key_yellow"  position="996,838" size="272,90"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="1300,856" size="8,54" backgroundColor="#3366FF" zPosition="1"/>
            <widget name="key_blue"    position="1316,838" size="272,90"
                    font="Regular;32" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    _SKIN_HD = """
        <screen position="0,0" size="1280,720" flags="wfNoBorder">
            <eLabel position="0,0"    size="1280,720"  backgroundColor="#66000000" zPosition="-6"/>
            <eLabel position="215,120" size="850,500"  backgroundColor="#33000000" zPosition="-5"/>
            <eLabel position="215,120" size="850,54"   backgroundColor="#33000000" zPosition="-4"/>
            <eLabel position="215,174" size="850,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="215,558" size="850,2"    backgroundColor="#004ecdc4" zPosition="-3"/>
            <eLabel position="215,560" size="850,60"   backgroundColor="#1A000000" zPosition="-4"/>
            <eLabel position="222,352" size="836,202"  backgroundColor="#20000000" zPosition="-2"/>
            <widget name="title_lbl"   position="228,126" size="600,42"
                    font="Regular;28" valign="center" foregroundColor="#ffffff" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="status_lbl"  position="228,180" size="806,46"
                    font="Regular;42" halign="center" valign="center"
                    foregroundColor="#e0e0e0" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="server_lbl"  position="228,228" size="806,24"
                    font="Regular;22" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="ip_lbl"      position="228,254" size="806,22"
                    font="Regular;20" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="country_lbl" position="228,278" size="806,22"
                    font="Regular;20" halign="center"
                    foregroundColor="#4ecdc4" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="city_lbl"    position="228,302" size="806,22"
                    font="Regular;20" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="transfer_lbl" position="228,326" size="806,22"
                    font="Regular;20" halign="center"
                    foregroundColor="#888888" backgroundColor="#33000000"
                    transparent="1"/>
            <widget name="log_lbl"     position="228,356" size="820,192"
                    font="Regular;16" foregroundColor="#888888" backgroundColor="#20000000"
                    transparent="1"/>
            <eLabel position="228,575" size="5,30" backgroundColor="#EE0000" zPosition="1"/>
            <widget name="key_red"     position="240,560" size="178,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="440,575" size="5,30" backgroundColor="#00BB00" zPosition="1"/>
            <widget name="key_green"   position="452,560" size="174,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="648,575" size="5,30" backgroundColor="#FFD700" zPosition="1"/>
            <widget name="key_yellow"  position="660,560" size="176,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
            <eLabel position="848,575" size="5,30" backgroundColor="#3366FF" zPosition="1"/>
            <widget name="key_blue"    position="860,560" size="198,60"
                    font="Regular;21" valign="center" foregroundColor="#cccccc" backgroundColor="#1A000000"
                    transparent="1"/>
        </screen>
    """
    skin = ""

    def __init__(self, session):
        global _plugin_open
        _plugin_open = True
        self.skin = self._SKIN_FHD if IS_FHD else self._SKIN_HD
        Screen.__init__(self, session)
        self._con_container = eConsoleAppContainer()
        self._con_container.dataAvail.append(self._on_output)
        self._con_container.appClosed.append(self._on_connect_done)
        self._dc_container = eConsoleAppContainer()
        self._dc_container.dataAvail.append(self._on_output)
        self._dc_container.appClosed.append(self._on_disconnect_done)
        self._ip_container = eConsoleAppContainer()
        self._ip_container.appClosed.append(self._on_ip_done)
        self._city_container = eConsoleAppContainer()
        self._city_container.dataAvail.append(self._on_city_data)
        self._city_container.appClosed.append(self._on_city_done)
        self._city_buf = ""
        self._session_rx_base = 0
        self._session_tx_base = 0
        self._connect_time = None
        self._log_buf = ""
        self._prev_connected = None
        self._connecting = False
        self._skip_servers = []

        self["title_lbl"]    = Label("NordVPN v%s" % VERSION)
        self["status_lbl"]   = Label("")
        self["server_lbl"]   = Label("")
        self["ip_lbl"]       = Label("")
        self["country_lbl"]  = Label("")
        self["city_lbl"]     = Label("")
        self["transfer_lbl"] = Label("")
        self["log_lbl"]      = Label("")
        self["key_red"]     = Label("")
        self["key_green"]   = Label("")
        self["key_yellow"]  = Label("Einstellungen")
        self["key_blue"]    = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok":     self._connect,
                "cancel": self.close,
                "green":  self._connect,
                "red":    self._disconnect,
                "yellow": self._open_settings,
                "blue":   self._next_server,
            },
            -1,
        )

        self._timer = eTimer()
        self._timer.callback.append(self._update_status)
        self._timer.start(3000, False)
        self._ip_timer = eTimer()
        self._ip_timer.callback.append(self._fetch_ip)
        self._city_timer = eTimer()
        self._city_timer.callback.append(self._fetch_city)
        self._update_status()

    def _set_status_color(self, connected):
        try:
            if connected:
                self["status_lbl"].instance.setForegroundColor(gRGB(0x4e, 0xcd, 0xc4))
            else:
                self["status_lbl"].instance.setForegroundColor(gRGB(0x88, 0x88, 0x88))
        except Exception:
            pass

    def _update_status(self):
        connected = manager.is_connected()
        if connected != self._prev_connected:
            if connected:
                if self._prev_connected is None:
                    self._restore_session()
                else:
                    self._connect_time = time.time()
                    rx, tx = self._read_tun_bytes()
                    self._session_rx_base = rx if rx is not None else 0
                    self._session_tx_base = tx if tx is not None else 0
                    self._save_session()
                if not self._connecting:
                    self._ip_timer.start(3000, True)
                    self._city_timer.start(4000, True)
                    self["log_lbl"].setText("")
            else:
                self._ip_timer.stop()
                self._connect_time = None
                try:
                    os.remove("/tmp/nordvpn_session")
                except Exception:
                    pass
                self["ip_lbl"].setText("")
                self["city_lbl"].setText("")
                self["transfer_lbl"].setText("")
            self._prev_connected = connected
        if connected:
            self["status_lbl"].setText(to_native_str(u"Verbunden"))
            self._set_status_color(True)
            srv = manager.get_current_server()
            self["server_lbl"].setText(to_native_str(srv) if srv else "")
            self["key_red"].setText(to_native_str(u"Trennen"))
            self["key_green"].setText("")
            self["key_blue"].setText(to_native_str(u"Nächster Server"))
            rx, tx = self._read_tun_bytes()
            dur = _fmt_duration(time.time() - self._connect_time) if self._connect_time else ""
            if rx is not None:
                dl = rx - self._session_rx_base
                ul = tx - self._session_tx_base
                self["transfer_lbl"].setText(
                    to_native_str(u"DL: %s   UL: %s   |   Verbunden seit: %s" % (_fmt_bytes(dl), _fmt_bytes(ul), dur))
                )
            elif dur:
                self["transfer_lbl"].setText(to_native_str(u"Verbunden seit: %s" % dur))
        else:
            self["status_lbl"].setText(to_native_str(u"Getrennt"))
            self._set_status_color(False)
            self["server_lbl"].setText("")
            self["key_red"].setText("")
            self["key_green"].setText(to_native_str(u"Verbinden"))
            self["key_blue"].setText("")
        self["country_lbl"].setText(
            to_native_str(u"Land: %s  |  Protokoll: %s" % (
                to_unicode(manager.get_country_name()),
                to_unicode(manager.get_protocol().upper()),
            ))
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

    def _fetch_city(self):
        if manager.is_connected():
            self._city_buf = ""
            self._city_container.execute(
                "wget -q -T 5 -O - 'http://ip-api.com/line/?fields=city'"
            )

    def _on_city_data(self, data):
        self._city_buf += data

    def _on_city_done(self, retval):
        city = self._city_buf.strip()
        if retval == 0 and city:
            self["city_lbl"].setText(city)

    def _read_tun_bytes(self):
        try:
            with open("/proc/net/dev") as f:
                for line in f:
                    if "tun0" in line:
                        parts = line.split()
                        return int(parts[1]), int(parts[9])
        except Exception:
            pass
        return None, None

    def _save_session(self):
        try:
            with open("/tmp/nordvpn_session", "w") as f:
                f.write("%s %d %d" % (
                    self._connect_time,
                    self._session_rx_base,
                    self._session_tx_base,
                ))
        except Exception:
            pass

    def _restore_session(self):
        try:
            with open("/tmp/nordvpn_session") as f:
                parts = f.read().split()
            self._connect_time = float(parts[0])
            self._session_rx_base = int(parts[1])
            self._session_tx_base = int(parts[2])
            return
        except Exception:
            pass
        self._connect_time = time.time()
        rx, tx = self._read_tun_bytes()
        self._session_rx_base = rx if rx is not None else 0
        self._session_tx_base = tx if tx is not None else 0

    def close(self):
        global _plugin_open, _last_vpn_status
        _plugin_open = False
        _last_vpn_status = manager.is_connected()
        self._timer.stop()
        self._city_timer.stop()
        Screen.close(self)

    def _on_output(self, data):
        lines = (self._log_buf + data).strip().splitlines()
        self._log_buf = "\n".join(lines[-9:]) + "\n"
        self["log_lbl"].setText(self._log_buf.strip())

    def _on_connect_done(self, retval):
        self._connecting = False
        if retval != 0:
            self._update_status()
            self.session.open(
                MessageBox,
                "Fehler beim Verbinden:\n" + self._log_buf[-300:],
                MessageBox.TYPE_ERROR,
                timeout=8,
            )
        else:
            self._prev_connected = False
            self._update_status()

    def _on_disconnect_done(self, retval):
        self._update_status()

    def _connect(self):
        if manager.is_connected():
            return
        if not manager.has_auth():
            self.session.open(
                MessageBox,
                "Bitte zuerst die Service Credentials in den Einstellungen eintragen.",
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return
        if self._con_container.running():
            self.session.open(
                MessageBox,
                "Verbindungsaufbau l\xc3\xa4uft bereits.",
                MessageBox.TYPE_INFO,
                timeout=3,
            )
            return
        self._connecting = True
        self._skip_servers = []
        self._log_buf = ""
        self["log_lbl"].setText("Verbinde...")
        self["status_lbl"].setText("Verbinde...")
        try:
            self["status_lbl"].instance.setForegroundColor(gRGB(0xff, 0xff, 0xff))
        except Exception:
            pass
        self["key_red"].setText("")
        self["key_green"].setText("")
        self._con_container.execute(manager.get_connect_cmd())

    def _next_server(self):
        if not manager.is_connected():
            return
        if self._con_container.running():
            return
        current = manager.get_current_server()
        if current and current not in self._skip_servers:
            self._skip_servers.append(current)
        self._connecting = True
        self._log_buf = ""
        self["log_lbl"].setText("Verbinde mit n\xc3\xa4chstem Server...")
        self["status_lbl"].setText("Verbinde...")
        try:
            self["status_lbl"].instance.setForegroundColor(gRGB(0xff, 0xff, 0xff))
        except Exception:
            pass
        self["key_red"].setText("")
        self["key_green"].setText("")
        self["key_blue"].setText("")
        self._con_container.execute(manager.get_connect_cmd_skip(self._skip_servers))

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



# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def main(session, **kwargs):
    session.open(NordVPNMain)


_status_timer = None
_last_vpn_status = None
_plugin_open = False


def _check_vpn_status():
    global _last_vpn_status
    current = manager.is_connected()
    if _last_vpn_status is not None and current != _last_vpn_status:
        if current and not _plugin_open:
            srv = manager.get_current_server()
            msg = to_unicode(u"NordVPN verbunden")
            if srv:
                msg += to_unicode(u" – ") + to_unicode(srv)
            AddPopup(to_native_str(msg), MessageBox.TYPE_INFO, timeout=5, id="nordvpn_notify")
        elif not _plugin_open:
            AddPopup(to_native_str(u"NordVPN getrennt! Reconnect in bis zu 60 Sek..."), MessageBox.TYPE_WARNING, timeout=8, id="nordvpn_notify")
    _last_vpn_status = current


def autostart(reason, **kwargs):
    global _status_timer
    if reason != 0:
        return

    # DNS rescue if box crashed while VPN was connected
    RESOLV_CONF   = "/etc/resolv.conf"
    RESOLV_BACKUP = "/etc/resolv.conf.nordvpn.bak"
    if not manager.is_connected() and os.path.isfile(RESOLV_BACKUP):
        try:
            import shutil
            shutil.move(RESOLV_BACKUP, RESOLV_CONF)
        except Exception:
            pass

    import subprocess
    try:
        for _entry in os.listdir("/proc"):
            if not _entry.isdigit():
                continue
            try:
                with open("/proc/%s/cmdline" % _entry) as _f:
                    _cmdline = _f.read()
            except Exception:
                continue
            if "nordvpn-watchdog" in _cmdline:
                try:
                    os.kill(int(_entry), 15)
                except Exception:
                    pass
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
            description="NordVPN Client f\xc3\xbcr Enigma2",
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
