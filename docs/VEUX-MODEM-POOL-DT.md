# VEUX reserved-memory pool selection

Read-only collection from root recovery on VEUX, slot A, 2026-10-29. The live
DT reports `/reserved-memory/#address-cells = <2>` and `#size-cells = <2>`.
`reg` values below are the decoded big-endian DT cells; `size prop` records a
dynamic reserved-memory request that has no fixed `reg` in the live DT.

## Selected region

Use `removed_region@c0000000`, `0xc0000000 + 0x05100000` (81 MiB), with
`no-map`. It has no `memory-region` consumer in the live tree and is absent
from the Linux `/proc/iomem` System RAM entries. Its fixed address makes it
stable for the XNU allocator. It is disjoint from the observed recovery kernel
image (`0xa0080000` through `0xa2726fff`) and the live DT initrd interval
`[0x00500fa4, 0xbfe06fa5)`.

The other large no-map candidate, `memshare_region`, has no fixed `reg`; Linux
allocates it dynamically. The archived recovery boot log records it at
`0xf5c00000`, size 8 MiB. The live tree assigns it to
`qcom,memshare/qcom,client_3` (5 MiB, `allocate-on-request`), so the XNU pool
leaves that allocator-owned region alone. Other fixed no-map regions of at
least 4 MiB are assigned to ADSP, CDSP, video, or the hypervisor; the table
records those exclusions.

## Full live `/reserved-memory/` inventory

| DT node | `reg` base + size | `no-map` | `compatible` | Decision / reason |
|---|---:|:---:|---|---|
| `adsp@86700000` | `0x86700000 + 0x02c00000` | yes | — | Excluded: ADSP firmware carve-out. |
| `adsp_region` | no fixed `reg`; `size=0x00800000` | yes | `removed-dma-pool` | Excluded: dynamic DSP pool; no stable base to compile into XNU. |
| `cdsp@88700000` | `0x89300000 + 0x01e00000` | yes | — | Excluded: CDSP firmware carve-out. |
| `cdsp_secure_heap_mem@80c00000` | `0x80c00000 + 0x01e00000` | yes | — | Excluded: secure CDSP heap. |
| `dfps_data_region@85e00000` | `0x85e00000 + 0x00100000` | no | — | Excluded: below 4 MiB and Linux-mapped. |
| `fw_mem@80b00000` | `0x80b00000 + 0x00100000` | yes | — | Excluded: below 4 MiB firmware carve-out. |
| `gpu_micro_code@8aa1a000` | `0x8b61a000 + 0x00002000` | yes | — | Excluded: below 4 MiB GPU firmware. |
| `hyp@80000000` | `0x80000000 + 0x00600000` | yes | — | Excluded: hypervisor carve-out. |
| `ipa_fw@8aa00000` | `0x8b600000 + 0x00010000` | yes | — | Excluded: below 4 MiB IPA firmware. |
| `ipa_gsi@8aa10000` | `0x8b610000 + 0x0000a000` | yes | — | Excluded: below 4 MiB IPA GSI memory. |
| `linux,cma` | no fixed `reg`; `size=0x02000000` | no | `shared-dma-pool` | Excluded: reusable Linux CMA, not no-map. |
| `mem_dump_region` | no fixed `reg`; `size=0x00800000` | no | `shared-dma-pool` | Excluded: reusable Linux shared-DMA pool. |
| `memshare_region` | no fixed `reg`; `size=0x00800000` | yes | `shared-dma-pool` | Excluded: dynamic pool assigned to qcom memshare client 3; archived recovery log reports base `0xf5c00000`. |
| `mpss_wlan@8b800000` | `0x8b800000 + 0x10000000` | yes | — | Excluded: forbidden MPSS/WLAN region. |
| `qseecom_region` | no fixed `reg`; `size=0x01400000` | no | `shared-dma-pool` | Excluded: reusable QSEE pool, not no-map. |
| `qseecom_ta_region` | no fixed `reg`; `size=0x01000000` | no | `shared-dma-pool` | Excluded: reusable QSEE TA pool, not no-map. |
| `ramoops` | `0xd0000000 + 0x00200000` | no | `ramoops` | Excluded: forbidden ramoops/pmsg region. |
| `removed_region@c0000000` | `0xc0000000 + 0x05100000` | yes | — | **Selected:** fixed no-map region, no live `memory-region` consumer, outside Linux System RAM, and no overlap with the recovery kernel/initrd. |
| `reserved_xbl_uefi@80880000` | `0x80880000 + 0x00014000` | yes | — | Excluded: below 4 MiB bootloader carve-out. |
| `secure_display_region` | no fixed `reg`; `size=0x05c00000` | no | `shared-dma-pool` | Excluded: reusable secure-display pool, not no-map. |
| `smem@80900000` | `0x80900000 + 0x00200000` | yes | — | Excluded: forbidden SMEM region. |
| `splash_region@0x85200000` | `0x85200000 + 0x00c00000` | no | — | Excluded: forbidden framebuffer and Linux-mapped. |
| `user_contig_region` | no fixed `reg`; `size=0x01000000` | no | `shared-dma-pool` | Excluded: reusable Linux pool, not no-map. |
| `video@8a500000` | `0x8b100000 + 0x00500000` | yes | — | Excluded: video/CVP firmware carve-out. |
| `wlan@86500000` | `0x86500000 + 0x00200000` | yes | — | Excluded: forbidden WLAN MSA region. |
| `xbl_aop_mem@80700000` | `0x80700000 + 0x00100000` | yes | — | Excluded: below 4 MiB AOP firmware carve-out. |

The chosen interval is also compile-time checked against all five explicitly
forbidden regions, every fixed no-map/peripheral carve-out listed above, the
observed recovery kernel image, and the live recovery initrd. The initrd is
adjacent to the chosen region but ends below its base.
