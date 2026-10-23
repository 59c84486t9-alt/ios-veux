#pragma once
#include <stdint.h>

/* Boot the SWEETXNU payload found in the ABL ramdisk; returns only on error. */
const char *loader_boot(uintptr_t dtb);

#ifdef DEVICE_VEUX
void loader_early_marker(const char *marker);
#endif
