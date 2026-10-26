# Launchd entitlement loss and root-image repair — 2026-10-25

The photographed boot of CI 40231594906 repeatedly returned EPERM while
launchd spawned xpcproxy, before exec_activate_image. This is an observed
failure; the precise runtime return site was not captured.

The saved keybag-noop root image contains an ad-hoc-signed launchd with no
XML or DER entitlement slots. Its CodeDirectory has only two special slots.
The historical keybag workaround edited launchd's embedded configuration and
re-signed it. Entitlement loss is a concrete image defect: the persona spawn
validation in XNU requires com.apple.private.persona-mgmt and returns EPERM
without it, before reaching the DRIVER diagnostic exception.

An older launchd signature remains in the sparse image's leftover data. Its
CodeDirectory identifier is com.apple.xpc.launchd, and its special-slot-5
SHA-256 matches the complete XML entitlement blob:
`aa19776d632829897f6f45eaac7639f5983bf22386757ff35aea02885d54e854`.
The recovered dictionary has 22 keys, including persona-mgmt=true. This
verifies the recovered entitlement blob against that CodeDirectory; it does
not make the leftover whole executable a valid signed baseline.

Restored the recovered dictionary to the current keybag-noop launchd. Reused
its existing 19,264-byte signature reservation, rebuilt the signature from
codesign's generated XML/DER signature, and recomputed CodeDirectory page
hashes against the unchanged executable prefix. Final signature is 4,212
bytes. All 516,336 pre-signature bytes, including the keybag workaround and
Mach-O headers, are identical. File size remains 535,600 bytes, so the HFS
catalog, extents and allocation map require no edits.

Created a separate APFS clone of the known saved sparse image, patched only
launchd's existing raw signature storage, then re-extracted the file from
the resulting HFS image. `codesign --verify --strict --verbose=2` succeeds
for that extracted binary. The original saved image is unchanged.

- Candidate: `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop-entitlements.simg`
- Candidate SHA-256: `d7777c229e7dc012a3e86a5d9f54ab4fc4bf74e443526fe2f11562f0d2b2d691`
- Original image SHA-256: `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`
- Original launchd SHA-256: `270b5a5f63d39256e7ee5e05053a569fc608802f4209e7affa07f48e4f082f7e`
- Repaired launchd SHA-256: `0f2d901341296f7154149122e33aa9c8c31f9b2a3359b78374dc89ef0c117f1f`
- Host-only evidence, binaries and reconstruction scripts:
  `research/veux-logs/launchd-entitlements-repair/` (ignored by Git).

Fastboot currently reports product veux, slot B. No phone partitions were
written and no reboot was issued during this repair. The existing boot_b
kernel (40231594906) can test the root fix; no new kernel build is required.
A fresh RW test requires restoring the repaired full root image to userdata.
Await per-destructive-step confirmation before that write, then reboot slot B
once Fastboot returns. Check whether xpcproxy setup EPERM disappears and
capture any next policy/activation failure. Runtime success is still untested.
