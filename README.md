# NordVPN Plugin für Enigma2 (VU+ VTI)

OpenVPN-basierter NordVPN-Client für Enigma2-Receiver mit VTI-Image.

Entwickelt und getestet auf einem **VU+ Uno 4K SE** mit VTI 15.0.04, Python 2.7.9 und OpenVPN 2.3.6.

---

## Funktionen

- Verbindung zum besten verfügbaren NordVPN-Server im gewählten Land
- Automatische Serverwahl über die offizielle NordVPN-API
- Unterstützung für **UDP** und **TCP**
- **DNS-Leak-Schutz** – NordVPN-DNS wird beim Verbinden gesetzt und beim Trennen wiederhergestellt
- **IPv6-Leak-Schutz** – IPv6 wird für die Dauer der VPN-Verbindung deaktiviert
- **Watchdog-Daemon** – erkennt abgestürzte Verbindungen und reconnectet automatisch
- **OSD-Benachrichtigungen** bei Verbindungsauf- und -abbau, auch wenn das Plugin geschlossen ist
- **Autostart** beim Hochfahren der Box (optional)
- **Zuletzt gewählte Länder** werden oben in der Länderliste angezeigt

---

## Voraussetzungen

- VU+ Receiver mit **VTI-Image**
- OpenVPN installiert: `opkg install openvpn`
- Ein NordVPN-Konto mit **Service Credentials**

> **Wichtig:** Es werden nicht die normalen Login-Daten benötigt, sondern die manuellen Service Credentials.  
> Diese findest du unter: [nordvpn.com](https://nordvpn.com) → Mein Konto → Services → NordVPN → **Set up manually**

---

## Installation

Die aktuelle Version als ZIP-Archiv von der [Releases-Seite](../../releases/latest) herunterladen, entpacken und per SSH auf die Box übertragen:

```sh
unzip enigma2-plugin-extensions-nordvpn_*.zip

cat enigma2-plugin-extensions-nordvpn_*_all.ipk | ssh root@<BOX-IP> "cat > /tmp/nordvpn.ipk"
ssh root@<BOX-IP> "opkg install /tmp/nordvpn.ipk"
```

Das Plugin installiert sich vollständig – Berechtigungen werden automatisch gesetzt, der Watchdog-Daemon wird beim nächsten Verbinden gestartet.

### Installierte Dateien

| Pfad | Beschreibung |
|------|--------------|
| `/usr/lib/enigma2/python/Plugins/Extensions/NordVPN/` | Plugin-Dateien |
| `/usr/sbin/nordvpn-connect` | Verbindungsaufbau |
| `/usr/sbin/nordvpn-disconnect` | Verbindungstrennung |
| `/usr/sbin/nordvpn-fetch-countries` | Länderliste von der NordVPN-API laden |
| `/usr/sbin/nordvpn-watchdog` | Hintergrunddaemon |

---

## Einrichtung

Das Plugin öffnen: **Menü → Plugins → NordVPN**

Dann **Gelb → Einstellungen**:

### 1. Zugangsdaten hinterlegen

Einstellungen → **Zugangsdaten** → OK

Service Username und Service Passwort eingeben (nicht die normalen Login-Daten – siehe oben).  
Die Credentials werden verschlüsselt auf der Box gespeichert und sind nicht im Plugin selbst enthalten.

### 2. Land auswählen

Einstellungen → **Land** → OK

Die Länderliste wird live von der NordVPN-API geladen. Zuletzt gewählte Länder erscheinen oben.  
Beim Verbinden wird automatisch der beste verfügbare Server im gewählten Land ausgewählt.

### 3. Protokoll wählen

Einstellungen → **Protokoll** → OK oder Links/Rechts

- **UDP** – Standard, schneller
- **TCP** – stabiler hinter restriktiven Firewalls

### 4. Autostart

Einstellungen → **Autostart** → OK oder Links/Rechts

Wenn aktiviert, verbindet das Plugin automatisch beim Starten der Box.

---

## Bedienung

| Taste | Funktion |
|-------|----------|
| Grün | Verbinden |
| Rot | Trennen |
| Gelb | Einstellungen |
| Blau | Plugin schließen |

Der Verbindungsstatus, der aktuelle Server und die externe IP-Adresse werden im Hauptfenster angezeigt und regelmäßig aktualisiert.

---

## Technische Details

### DNS-Leak-Schutz

Beim Verbinden werden die NordVPN-eigenen DNS-Server gesetzt (`103.86.96.100`, `103.86.99.100`) und die ursprüngliche Konfiguration gesichert. Beim Trennen wird sie automatisch wiederhergestellt.

### IPv6-Leak-Schutz

IPv6 wird für die Dauer der VPN-Verbindung systemweit deaktiviert und beim Trennen wiederhergestellt. So kann kein Traffic an der VPN-Verbindung vorbeifließen.

### Watchdog

Der Watchdog-Daemon läuft im Hintergrund und prüft alle 60 Sekunden, ob der OpenVPN-Prozess noch aktiv ist. Ist er abgestürzt, wird automatisch eine neue Verbindung aufgebaut.

Beim manuellen Trennen über das Plugin wird der Watchdog beendet – es erfolgt keine automatische Wiederverbindung.

---

## Deinstallation

```sh
# IPK auf die Box kopieren (falls nicht mehr vorhanden, aus dem Release-ZIP)
cat enigma2-plugin-extensions-nordvpn_*_all.ipk | ssh root@<BOX-IP> "cat > /tmp/nordvpn.ipk"

# Paket registrieren und vollständig entfernen
ssh root@<BOX-IP> "opkg install --force-reinstall /tmp/nordvpn.ipk && opkg remove enigma2-plugin-extensions-nordvpn"
```

Das Deinstallations-Skript räumt vollständig auf: Watchdog und OpenVPN werden beendet, alle Konfigurationsdateien und Logdateien werden gelöscht, die **Credentials werden sicher entfernt**.

---

## Für Entwickler

### IPK neu bauen

```sh
python3 tools/build_ipk.py
```

Alle Quelldateien müssen im Projektordner vorhanden sein. Das fertige IPK wird im Projekt-Root abgelegt.

### Hinweise zur Kompatibilität

Das Plugin setzt Python 2.7 und die Enigma2-Python-API (VTI-Image) voraus. Es wurde ausschließlich auf VTI 15 getestet. Andere Enigma2-Images oder Python-3-Umgebungen werden nicht unterstützt.
