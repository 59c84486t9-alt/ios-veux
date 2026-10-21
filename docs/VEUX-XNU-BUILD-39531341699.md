# VEUX XNU build attempt 39531341699

Workflow: [xnu run 39531341699](https://github.com/59c84486t9-alt/ios-veux/actions/runs/39531341699)

- Settings: `macos_version=13.5`, `kernel_config=DEVELOPMENT`,
  `machine_config=VEUX`; runner used Xcode 15.0.1.
- Patch application and the bootstrap build completed. XNU C/assembly compilation
  reached the final link, which failed with 264 unresolved symbol references.
- Missing groups included generic arm64 pmap (`pmap_*`), exception/copy routines,
  MMU and CPU entry points (`_start`, `_set_mmu_ttb`, `_start_cpu`), and routines
  supplied by the open-source arm64 assembly config (`CleanPoU_Dcache`,
  `InvalidatePoU_Icache`, and related symbols). The `xnu-kernel` artifact has no
  kernel image; the `xnu-buildtree` artifact is available for local replay.
- Diagnosis: the VEUX XNU tree had a VEUX machine header and build flags but no
  `config/MASTER.arm64.veux`. The kernel config therefore did not enable the
  open-source `nos_arm_pmap` and `nos_arm_asm` sources that this port needs. The
  SWEET port provides those settings in `MASTER.arm64.sweet`.
- Patch `0083-veux-open-source-arm64-config.patch` adds the matching
  `MASTER.arm64.veux` config for VEUX. This targets the missing source selection;
  it does not assert that all remaining VEUX compile/link errors are resolved.

The earlier missing VEUX processor cache-line and GIC macro errors no longer
appear in this run. This is still build work only; no kernel was produced, booted,
or flashed.
