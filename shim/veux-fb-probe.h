#pragma once
#include <stdint.h>
#include <stddef.h>
struct probe_display {
    uint64_t base, size;
    uint32_t width, height, stride, bgr;
};
struct probe_info {
    struct probe_display fb;
    uint32_t fb_count, fb_valid, ramoops_valid;
    struct probe_display splash;
    uint32_t splash_count, splash_valid;
};
/* Returns 0 for malformed FDT; a valid FDT may contain no usable display. */
int probe_parse(const void *blob, size_t length, struct probe_info *out);
void probe_pattern(volatile uint32_t *pixels, const struct probe_display *fb);

/* 1 = live simplefb, 2 = explicit splash assumption, 0 = no safe selection. */
int probe_select(struct probe_info *info);
