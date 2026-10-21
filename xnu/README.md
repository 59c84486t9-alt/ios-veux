# XNU for VEUX

Built on GitHub's macOS arm64 runners by `.github/workflows/xnu.yml`, using
[blacktop/darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build) (MIT) at a pinned commit.

- `MACOS_VERSION=13.5` -> xnu-8796 (same generation as iOS 16.6/16.7).
- `patches/*.patch` are copied into the build script's patch dir and applied to the xnu tree with `git apply`.
- Run the `xnu` workflow with `MACHINE_CONFIG=VEUX`; output is uploaded as the `xnu-kernel` workflow artifact.
- The VEUX machine config is a compile profile only. It does not yet provide the VEUX-specific platform, interrupt, storage, touch, power, USB, or display drivers needed for a bootable kernel. Framebuffer writes remain disabled until the physical scanout address and linear memory layout are established.

Fetch the latest build: `gh run download -R 59c84486t9-alt/ios-veux -n xnu-kernel -D xnu/out`
