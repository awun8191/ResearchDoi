---
name: network-connectivity-rescue
description: Diagnose and fix cases where Ethernet only works with a VPN, DNS fails without VPN, ping shows "network prohibited", or connectivity breaks after VPN toggles. Use this skill whenever users mention Ethernet no internet, VPN-required browsing, DNS timeout, ProtonVPN kill switch behavior, NetworkManager/systemd-networkd conflicts, or Wi-Fi hotspot sharing issues.
---

# Network Connectivity Rescue

Restore stable non-VPN connectivity with a fast, evidence-first workflow, including advanced Wi-Fi hotspot troubleshooting.

## When this skill should trigger

Use this skill when users report issues like:

- "Ethernet works only when VPN is on"
- "DNS fails unless VPN is enabled"
- "ping shows network prohibited / destination prohibited"
- "internet is slow or unstable after enabling/disabling VPN"
- "wired network connected but websites do not load"
- "hotspot is not showing up on phone"
- "hotspot connected but no internet"

## Operating principles

1. Diagnose before changing configuration.
2. Prefer reversible, low-risk changes.
3. Isolate interface paths (Ethernet vs Wi-Fi) before concluding root cause.
4. Treat VPN kill-switch residue, dual network managers, and Docker iptables as first-class suspects.
5. If plain DNS is blocked on this network, prefer DNS-over-TLS over a full VPN.

## Standard troubleshooting flow

### 1. Capture baseline

Collect:

- `nmcli connection show --active`
- `nmcli -t -f DEVICE,STATE,CONNECTION dev status`
- `ip route` and `ip rule show`
- `resolvectl status`
- `ping -4 -c3 1.1.1.1`
- DNS + HTTPS tests (`getent ahostsv4 github.com`, `curl -4I https://github.com`)

### 2. Isolate Ethernet path

- Temporarily disconnect Wi-Fi only for verification.
- Re-test DNS and HTTPS on Ethernet.
- If IP connectivity works but hostname resolution fails, branch to DNS remediation.

### 3. Check for VPN residue

Look for active VPN/tunnel/leak interfaces and connections (WireGuard, Proton, dummy kill-switch links).  
If present, bring them down before non-VPN validation or hotspot creation. VPN kill-switches strictly drop forwarded traffic.

### 4. Detect network manager conflict

If both NetworkManager and systemd-networkd manage the same interface (e.g., duplicate IPs, "externally" managed state), treat this as a root-cause candidate.

- Desktop/Laptop default: keep NetworkManager as authority.
- Disable/stop systemd-networkd (`systemctl disable --now systemd-networkd`).
- Move any conflicting `.network` files out of `/etc/systemd/network/`.
- Ensure device is managed by NetworkManager.

### 5. Wi-Fi Hotspot Troubleshooting (Advanced)

If a user is trying to host a Wi-Fi hotspot but devices cannot see it or have no internet:

1. **Missing DHCP Server:** NetworkManager requires `dnsmasq` to assign IPs to hotspot clients. Check if installed (`pacman -Qs dnsmasq`). If missing, hotspot activation will fail with "IP configuration could not be reserved".
2. **Docker Firewall Block:** Docker sets the `FORWARD` policy to `DROP`. Even if `ipv4.method shared` is set, Docker blocks the traffic. Fix by adding rules to `DOCKER-USER`:
   - `sudo iptables -I DOCKER-USER -i wlan0 -j ACCEPT`
   - `sudo iptables -I DOCKER-USER -o wlan0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT`
3. **WPA3 (SAE) Invisibility:** NetworkManager defaults to WPA3/WPA2 mixed mode. Many phones silently ignore WPA3 beacons and hide the SSID. Fix by forcing WPA2-PSK and **renaming the SSID** to bypass the phone's cache:
   - `nmcli connection modify Hotspot 802-11-wireless-security.key-mgmt wpa-psk 802-11-wireless-security.proto rsn 802-11-wireless-security.pairwise ccmp 802-11-wireless-security.group ccmp 802-11-wireless-security.pmf 1`
   - `nmcli connection modify Hotspot 802-11-wireless.ssid "NewName"`
4. **Channel Auto-Negotiation Failure:** Some cards (like Realtek) fail to broadcast when the channel is `0` (auto). Force a specific channel (e.g., `802-11-wireless.channel 6`).
5. **Realtek (rtw88) Firmware Crashes:** "failed to get tx report from firmware". Stabilize by disabling ASPM and deep sleep:
   - `echo "options rtw88_pci disable_aspm=y" | sudo tee /etc/modprobe.d/rtw88.conf`
   - `echo "options rtw88_core disable_lps_deep=y" | sudo tee -a /etc/modprobe.d/rtw88.conf`
   - *Requires reboot or module reload.*

### 6. DNS remediation ladder (no VPN)

1. Set stable resolver in NetworkManager profile:
   - `ipv4.ignore-auto-dns yes`
   - `ipv4.dns "1.1.1.1 1.0.0.1"`
2. If DNS still fails but IP traffic works, enable DoT on the profile:
   - `connection.dns-over-tls yes`
   - `ipv4.dns "1.1.1.1#cloudflare-dns.com 1.0.0.1#cloudflare-dns.com"`
3. Restart the Ethernet connection and verify again.
4. If IPv6 path causes instability on this network, optionally set `ipv6.method ignore`.

### 7. Verify outcome

Confirm all of:

- No active VPN route is required
- Hostname DNS resolution works
- HTTPS to major domains works
- Ping by hostname works (not only by IP)
- (For Hotspot) Clients can connect, receive an IP in the `10.42.0.x` range, and route to the internet.

## Output format for user handoff

Always return:

1. **Root cause found** (or most likely cause if partial)
2. **Changes applied** (exact profile/service/iptables updates)
3. **Current working state** (non-VPN DNS + HTTPS status, or Hotspot visibility)
4. **Rollback commands** (quick path to revert)

## Privilege handling

If root actions are required and sudo is not available/locked out (e.g., `pam_faillock`):

1. Provide the user exact commands to run (copy/paste safe in one line to avoid shell parsing errors).
2. Explain the lockout if applicable (e.g., 10-minute wait).
3. Wait for confirmation.
4. Resume validation immediately after user runs them.