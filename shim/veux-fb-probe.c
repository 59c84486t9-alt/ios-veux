/* Standalone probe: only trust a complete simple-framebuffer in ABL's FDT.
 * Splash reservations and later Android DRM metadata are not scanout modes.
 */
#include "veux-fb-probe.h"

static uint32_t be32(const unsigned char *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}
static int eq(const char *a, const char *b)
{
    while (*a && *a == *b) { a++; b++; }
    return *a == *b;
}
static int terminated(const unsigned char *p, size_t n)
{
    for (size_t i = 0; i < n; i++) if (!p[i]) return (int)i + 1;
    return 0;
}
static int compatible(const unsigned char *p, size_t n, const char *wanted)
{
    while (n) {
        int len = terminated(p, n);
        if (!len) return 0;
        if (eq((const char *)p, wanted)) return 1;
        p += len; n -= len;
    }
    return 0;
}
struct node {
    uint32_t ac, sc, parent_ac, parent_sc;
    uint32_t chosen, reserved, direct, enabled, simple, ramoops, bgr, format;
    uint32_t width, height, stride, reglen, ranges_empty;
    const unsigned char *reg;
};
static uint64_t cells(const unsigned char *p, uint32_t n)
{
    return n == 2 ? (uint64_t)be32(p) << 32 | be32(p + 4) : be32(p);
}
int probe_parse(const void *blob, size_t length, struct probe_info *out)
{
    const unsigned char *b = blob;
    *out = (struct probe_info){0};
    if (length < 40 || be32(b) != 0xd00dfeed) return 0;
    uint32_t total = be32(b + 4), pos = be32(b + 8), strings = be32(b + 12);
    uint32_t string_size = be32(b + 32), struct_size = be32(b + 36);
    if (total > length || total > 0x200000 || total < 40 || pos < 40 || (pos & 3) ||
        strings < 40 || pos > total || struct_size > total - pos ||
        strings > total || string_size > total - strings || be32(b + 20) < 17)
        return 0;
    uint32_t end = pos + struct_size;
    if (pos < strings + string_size && strings < end) return 0;
    struct node stack[32];
    int depth = 0, root_seen = 0;
    while (pos <= end && end - pos >= 4) {
        uint32_t token = be32(b + pos); pos += 4;
        if (token == 1) {
            if (depth == 32 || (!depth && root_seen)) return 0;
            int len = terminated(b + pos, end - pos);
            if (!len) return 0;
            struct node n = {0};
            n.ac = 2; n.sc = 1; n.enabled = 1;
            if (!depth) { root_seen = 1; if (len != 1) return 0; }
            else {
                struct node *parent = &stack[depth - 1];
                n.parent_ac = parent->ac; n.parent_sc = parent->sc;
                n.enabled = parent->enabled;
                n.chosen = depth == 1 && eq((const char *)b + pos, "chosen");
                n.reserved = depth == 1 && eq((const char *)b + pos, "reserved-memory");
                n.direct = depth == 1 || (depth == 2 &&
                    (parent->chosen || (parent->reserved && parent->ranges_empty)));
            }
            stack[depth++] = n;
            pos = (pos + (uint32_t)len + 3) & ~3u;
        } else if (token == 3) {
            if (!depth || end - pos < 8) return 0;
            uint32_t len = be32(b + pos), noff = be32(b + pos + 4); pos += 8;
            if (len > end - pos || noff >= string_size ||
                !terminated(b + strings + noff, string_size - noff)) return 0;
            const char *name = (const char *)b + strings + noff;
            const unsigned char *v = b + pos;
            struct node *n = &stack[depth - 1];
            if (eq(name, "#address-cells") && len == 4) n->ac = be32(v);
            else if (eq(name, "#size-cells") && len == 4) n->sc = be32(v);
            else if (eq(name, "ranges")) n->ranges_empty = len == 0;
            else if (eq(name, "compatible")) {
                n->simple = compatible(v, len, "simple-framebuffer");
                n->ramoops = compatible(v, len, "ramoops");
            } else if (eq(name, "status")) {
                n->enabled = n->enabled && terminated(v, len) &&
                    (eq((const char *)v, "okay") || eq((const char *)v, "ok"));
            } else if (eq(name, "reg")) { n->reg = v; n->reglen = len; }
            else if (eq(name, "width") && len == 4) n->width = be32(v);
            else if (eq(name, "height") && len == 4) n->height = be32(v);
            else if (eq(name, "stride") && len == 4) n->stride = be32(v);
            else if (eq(name, "format") && terminated(v, len)) {
                n->bgr = eq((const char *)v, "a8b8g8r8") || eq((const char *)v, "x8b8g8r8");
                n->format = n->bgr || eq((const char *)v, "a8r8g8b8") || eq((const char *)v, "x8r8g8b8");
            }
            pos = (pos + len + 3) & ~3u;
        } else if (token == 2) {
            if (!depth) return 0;
            struct node *n = &stack[--depth];
            if (n->enabled && n->simple) out->fb_count++;
            if (!n->enabled || !n->direct || !n->reg ||
                n->parent_ac < 1 || n->parent_ac > 2 ||
                n->parent_sc < 1 || n->parent_sc > 2 ||
                n->reglen != 4 * (n->parent_ac + n->parent_sc)) continue;
            uint64_t base = cells(n->reg, n->parent_ac);
            uint64_t size = cells(n->reg + 4 * n->parent_ac, n->parent_sc);
            /* Existing recovery's verified runtime split: 1 MiB records +
             * 1 MiB pmsg. DT's 2 MiB pmsg-size differs from that override.
             * Validate the reservation, never infer the runtime split from it. */
            if (n->ramoops && base == 0xd0000000 && size == 0x200000)
                out->ramoops_valid = 1;
            if (n->simple) {
                out->fb = (struct probe_display){base, size, n->width, n->height, n->stride, n->bgr};
                /* Limit this board probe to the DT-verified splash reservation;
                 * geometry and address still must come from the live node. */
                out->fb_valid = n->format && base >= 0x85200000 && base < 0x85e00000 &&
                    size <= 0x85e00000 - base && !(base & 3) && !(n->stride & 3) &&
                    n->width && n->width <= 4096 && n->height && n->height <= 4096 &&
                    (uint64_t)n->width * 4 <= n->stride &&
                    (uint64_t)n->stride * n->height <= size;
            }
        } else if (token == 9) {
            if (depth || !root_seen) return 0;
            if (out->fb_count != 1) out->fb_valid = 0;
            return 1;
        } else if (token != 4) return 0;
    }
    return 0;
}
void probe_pattern(volatile uint32_t *pixels, const struct probe_display *f)
{
    for (uint32_t y = 0; y < f->height; y++) {
        volatile uint32_t *row = pixels + (uint64_t)y * (f->stride / 4);
        for (uint32_t x = 0; x < f->width; x++) {
            uint32_t color = x < f->width / 3 ? 0xffff0000u :
                x < 2 * f->width / 3 ? 0xff00ff00u : 0xff0000ffu;
            if (f->bgr) color = (color & 0xff00ff00u) | ((color & 255) << 16) | ((color >> 16) & 255);
            /* White corner square + black border expose orientation/stride. */
            if (x < 32 && y < 32) color = 0xffffffffu;
            if (x == 0 || y == 0 || x + 1 == f->width || y + 1 == f->height) color = 0xff000000u;
            row[x] = color;
        }
    }
}
#ifndef PROBE_HOST
static void barrier(void) { __asm__ volatile("dsb sy" ::: "memory"); }
static void log_char(char c)
{
    volatile uint32_t *h = (volatile uint32_t *)0xd0100000UL;
    volatile unsigned char *data = (volatile unsigned char *)(0xd0100000UL + 12);
    const uint32_t capacity = 0x100000 - 12;
    uint32_t start = h[1], size = h[2];
    if (h[0] != 0x43474244 || start >= capacity || size > capacity || start > size) {
        h[0] = 0x43474244; h[1] = h[2] = 0; start = size = 0; barrier();
    }
    data[start] = (unsigned char)c; barrier();
    h[1] = (start + 1) % capacity;
    h[2] = size < capacity ? size + 1 : capacity; barrier();
}
static void log_text(const char *s) { while (*s) log_char(*s++); }
static void log_hex(const char *label, uint64_t v)
{
    log_text(label);
    for (int i = 60; i >= 0; i -= 4) log_char("0123456789abcdef"[(v >> i) & 15]);
    log_char('\n');
}
void probe_main(uintptr_t fdt)
{
    struct probe_info info;
    if (!fdt || (fdt & 7)) return;
    if (!probe_parse((const void *)fdt, be32((const unsigned char *)fdt + 4), &info)) return;
    if (info.ramoops_valid) {
        log_text("\nVEUX FDT PROBE v2 stage=1 parsed live FDT\n");
        log_hex("fdt=", fdt);
        log_hex("framebuffers=", info.fb_count);
        log_hex("base=", info.fb.base); log_hex("size=", info.fb.size);
        log_hex("width=", info.fb.width); log_hex("height=", info.fb.height);
        log_hex("stride=", info.fb.stride); log_hex("bgr=", info.fb.bgr);
    }
    if (!info.fb_valid) {
        if (info.ramoops_valid) log_text("stage=2 SKIP missing/unsupported/ambiguous live simplefb\n");
        return;
    }
    if (info.ramoops_valid) log_text("stage=2 validated simplefb; starting RGB fill\n");
    probe_pattern((volatile uint32_t *)(uintptr_t)info.fb.base, &info.fb);
    barrier();
    if (info.ramoops_valid) log_text("stage=3 RGB fill complete; holding indefinitely\n");
}
#endif
