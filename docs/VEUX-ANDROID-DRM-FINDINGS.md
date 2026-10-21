# VEUX Android DRM findings

Collected from Android on slot B with Magisk `su`, using the debugfs-enabled
5.4.292 Paimon kernel (`1438fcba`). The active display state was read from
`/sys/kernel/debug/dri/0/state` after the Android display stack had started.

## Active display state

- CRTC `crtc-0` / `crtc76` is enabled and active on connector `DSI-1`.
- Mode: 1080x2400 at 120 Hz.
- Primary plane `plane-1` / `plane66`, framebuffer 34: FourCC `XB24`
  (`DRM_FORMAT_XBGR8888`, `0x34324258`), modifier `0x500000000000001`.
- The allocated surface is 1088x2400, pitch 4352 bytes, offset 0, object size
  10,522,624 bytes. It is an imported GEM object and the driver reports
  `start=0x00000000`.
- Two additional active planes use `AB24`, 1088x112 surfaces, pitch 4352,
  offset 0, and the same modifier. They are overlays at the top and bottom of
  the display.

## What this establishes

This is direct evidence of Android's active DRM composition format and surface
geometry. It corrects the earlier recovery-only record, which had mode and
pitch but could not identify a format. The imported GEM object's `start=0`
does not reveal its physical address, and the nonzero modifier means the
surface must not be treated as a linear CPU framebuffer. These results do not
establish that the bootloader splash reservation at `0x85200000` is the active
scanout buffer.

Keep XNU framebuffer writes disabled. This observation also does not establish
a complete Android boot: `sys.boot_completed` was empty when the DRM state was
captured, although the composer and active CRTC were running. No partition was
written during this collection.

The raw capture is retained outside the repository at
`../veux-debugfs-kernel/magisk-patch/android-drm-state.txt`.
