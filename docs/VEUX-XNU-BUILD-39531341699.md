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

## Follow-up run 39532087795

[xnu run 39532087795](https://github.com/59c84486t9-alt/ios-veux/actions/runs/39532087795)
used the same settings and the new config. The unresolved-symbol link failure
was cleared. Compilation then stopped at
`bsd/sweet_hfs/sweet_hfs_iokit.c:21: fatal error: 'hfs.h' file not found`.
The pinned HFS, libpthread, and BearSSL staging scripts only ran when
`MACHINE_CONFIG=SWEET`, even though the VEUX compile profile also uses these
shared open-source sources. Their guards are being extended to VEUX.

The `xnu-buildtree` artifact for this run is saved locally at
`xnu/run-39532087795/buildtree.tgz` for replay; it is not committed.

## Follow-up run 39532741922

[xnu run 39532741922](https://github.com/59c84486t9-alt/ios-veux/actions/runs/39532741922)
successfully staged HFS, libpthread, and BearSSL and compiled the expanded HFS
sources. Compilation then failed because the HFS compatibility include flags in
`bsd/conf/Makefile.template` were nested inside the SWEET-only condition from
`0019-sweet-builtin-pthread.patch`. Updated that condition to include VEUX so
the compatibility header is applied to the HFS objects too. The log's main
errors were HFS compatibility declarations/macros missing without that header.

The `xnu-buildtree` artifact for this run is saved locally at
`xnu/run-39532741922/buildtree.tgz` for replay; it is not committed.

## Follow-up run 39533529250

[xnu run 39533529250](https://github.com/59c84486t9-alt/ios-veux/actions/runs/39533529250)
applied the HFS compatibility header and compiled all sources. The final link
was down to two missing symbols: `ml_enable_monitor` and `sweet_sample_task`.
Both definitions were guarded as SWEET-only even though the VEUX config calls
the no-monitor stub and includes the shared debug sampler. The XNU patches now
extend those guards to VEUX (`0008` and new `0084`).

The `xnu-buildtree` artifact for this run is saved locally at
`xnu/run-39533529250/buildtree.tgz` for replay; it is not committed.

## Follow-up run 39534235727

[xnu run 39534235727](https://github.com/59c84486t9-alt/ios-veux/actions/runs/39534235727)
applied the `ml_enable_monitor` extension but skipped `0084` because its hunk
did not have enough context to match `osfmk/kern/exception.c`. The final link
therefore had only `_sweet_sample_task` unresolved. Added the following include
line as patch context and verified `git apply --check` against the downloaded
source. The buildtree is saved locally at
`xnu/run-39534235727/buildtree.tgz` for replay; it is not committed.
