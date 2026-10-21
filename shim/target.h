#pragma once

/* Physical UFSHCI bases: VEUX comes from its board-matched DTB; SWEET is the
 * diagnostic shim's original device. DEVICE_VEUX is set by build.sh --veux.
 */
#if defined(DEVICE_VEUX)
#define UFS_BASE 0x04804000UL /* ufshc@4804000, VEUX live DTB */
#else
#define UFS_BASE 0x01d84000UL /* ufshc@1d84000, SWEET live DTB */
#endif
