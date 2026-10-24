/*
 * treasure_hook.c - adds the missing server half of the Treasures (Lucky Key)
 *                   system to the Perfect World 1.7.3 game server (gs).
 *
 * WHY
 *   In the 1.7.3 gs the Treasures window's commands arrive in
 *   gplayer_imp::Lottery_Notice1(type, param). Only type 2 (take an item out of
 *   the Treasure Warehouse) is implemented. Type 3 (seek), 1 (open chest n) and
 *   0 (window opened) only print "Lottery_Notice1 roleid=.. t p" and return, so
 *   the client never receives a chest board. (Verified 2026-10-17 by disassembly.)
 *
 * HOW
 *   The library is loaded into gs with LD_PRELOAD. At start-up, before gs's
 *   main() runs, it reads gs's own symbol table from /proc/self/exe and redirects
 *   calls to one gs function to a hook here. gs's own code is not changed:
 *     hook.mode = notice1 (default): every vtable slot, and every direct call or
 *       jump inside functions named *CommandHandler*, that leads to
 *       gplayer_imp::Lottery_Notice1 goes to hook_notice1().
 *     hook.mode = command (plan B, if the compiler inlined or split
 *       Lottery_Notice1): the vtable slots and direct calls of
 *       gplayer_controller::CommandHandler go to hook_cmd(), which picks out the
 *       Treasures client command (cmd.id) and passes every other command on.
 *   The hook answers seek / open / window itself by calling gs's OWN functions
 *   (item check, take, give, packet senders) found by symbol name. Which
 *   functions and which arguments is set in treasure_hook.conf, so new findings
 *   need a config edit, not a rebuild. Everything else goes to gs's original code.
 *
 * CHEST BOARD (what makes the client show the 10 chests)
 *   Modelled on the public DeadRaky 2022 rewrite (cgame/gs/player_lottery.cpp in
 *   the 1.7.4/1.7.6 sources) and its S2C packet get_treasure_info, opcode 434 in
 *   the 1.7.6 source (verified 2026-10-19 from s2c_source.h / s2c_header.h):
 *     u16 cmd, u8 manager, u32 score, u32 free_count, u32 lot_count, u32 box_count,
 *     LOT[lot_count] {u32 id, u32 count, u8 lot}               prizes not yet won
 *     BOX[box_count] {u32 id, u32 box, u32 count, u8 lot}      opened chests, in order
 *   (in that source the BOX array line is commented out; here it is configurable).
 *   A seek draws 10 prizes ("lots", index 0-9) and hides each one in a random
 *   chest position ("box", 0-9). manager = 1 after a seek, 2 after an open.
 *
 * MODES (treasure_hook.conf, re-read automatically when the file changes)
 *   log    log every Treasures command, then let gs handle it as before
 *   probe  allowed roles only: send a test board, move no items
 *   live   full Treasures logic for allowed roles (allow_roles = all for everyone)
 *
 * SAFETY RULES BUILT IN
 *   - only global functions without '.' in the name are called or hooked
 *     (GCC's local copies like ".part.0" may use a different calling convention)
 *   - a call is refused when a pointer argument is 0 (offset not set, call not run)
 *   - pointers read through config offsets are read with process_vm_readv, so a
 *     wrong offset gives "no role id" instead of a crash
 *   - the per-character state is saved BEFORE items move, and put back if the
 *     item step fails
 *
 * BUILD on the server VM (gs is a 32-bit program): see Makefile and README.md.
 * The same source also builds 64-bit; that is used for the tests on Claude's
 * side (test/run_tests.sh) and would suit a 64-bit server.
 *
 * STATUS: theoretical. Symbols, offsets and argument lists in the config must
 * be filled in from tools/recon_gs.sh output and tried in a test VM first.
 */
#define _DEFAULT_SOURCE /* not _GNU_SOURCE: keeps glibc 2.38+ from swapping in newer
                           strtol/sscanf symbols, so the .so also runs on older glibc */
#include <ctype.h>
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <link.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>

#if defined(__i386__)
#define TH_ELFCLASS ELFCLASS32
#elif defined(__x86_64__)
#define TH_ELFCLASS ELFCLASS64
#else
#error "x86 only (32-bit for the PW 1.7.3 gs)"
#endif

#ifndef MAP_FIXED_NOREPLACE
#define MAP_FIXED_NOREPLACE 0x100000
#endif

typedef uint32_t u32;
typedef int32_t s32;
typedef uint8_t u8;
typedef uintptr_t uptr;

#define ENTRY __attribute__((force_align_arg_pointer))
#define ST_TYPE(i) ((i) & 0xf)
#define ST_BIND(i) ((i) >> 4)

/* dl_iterate_phdr is only declared with _GNU_SOURCE; declare the part we use. */
#ifdef __USE_GNU
typedef struct dl_phdr_info th_phdr_info_t;
#else
typedef struct {
    ElfW(Addr) dlpi_addr;
    const char *dlpi_name;
    const ElfW(Phdr) *dlpi_phdr;
    ElfW(Half) dlpi_phnum;
} th_phdr_info_t;
extern int dl_iterate_phdr(int (*cb)(th_phdr_info_t *, size_t, void *), void *data);
#endif

/* ------------------------------------------------------------------ */
/* paths, locks, logging                                               */
/* ------------------------------------------------------------------ */
static char g_confpath[512] = "/opt/treasure_hook/treasure_hook.conf";
static char g_logpath[512] = "/opt/treasure_hook/hook.log";
static pthread_mutex_t g_logmx = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t g_reloadmx = PTHREAD_MUTEX_INITIALIZER;
static __thread int g_in_hook; /* re-entry guard: a gs call made by us never loops back */

/* gs forks one child per map: make sure no lock is held across a fork */
static void atfork_prepare(void)
{
    pthread_mutex_lock(&g_reloadmx);
    pthread_mutex_lock(&g_logmx);
}
static void atfork_release(void)
{
    pthread_mutex_unlock(&g_logmx);
    pthread_mutex_unlock(&g_reloadmx);
}

static void tlog(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void tlog(const char *fmt, ...)
{
    char line[2048];
    int saved = errno;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    struct timeval tv;
    gettimeofday(&tv, NULL);
    struct tm tm;
    localtime_r(&tv.tv_sec, &tm);
    pthread_mutex_lock(&g_logmx);
    FILE *f = fopen(g_logpath, "ae"); /* e = close-on-exec */
    if (f) {
        fprintf(f, "%04d-%02d-%02d %02d:%02d:%02d pid %d | %s\n", tm.tm_year + 1900,
                tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec, (int)getpid(), line);
        fclose(f);
    }
    pthread_mutex_unlock(&g_logmx);
    errno = saved;
}

static void tlog_hex(const char *what, const u8 *p, u32 n)
{
    char buf[3 * 256 + 1];
    u32 m = n > 256 ? 256 : n, i;
    for (i = 0; i < m; i++)
        snprintf(buf + 3 * i, 4, "%02x ", p[i]);
    buf[3 * m] = 0;
    tlog("%s (%u bytes): %s%s", what, n, buf, n > m ? "..." : "");
}

/* ------------------------------------------------------------------ */
/* small helpers                                                       */
/* ------------------------------------------------------------------ */
static char *trim(char *s)
{
    while (isspace((unsigned char)*s))
        s++;
    char *e = s + strlen(s);
    while (e > s && isspace((unsigned char)e[-1]))
        *--e = 0;
    return s;
}

static void copyz(char *dst, size_t n, const char *src) { snprintf(dst, n, "%s", src); }

static int parse_bool(const char *v)
{
    return !strcmp(v, "1") || !strcmp(v, "yes") || !strcmp(v, "true") || !strcmp(v, "on");
}

/* whole-string number: decimal, or hex with 0x; optional leading '-'. 0 = ok */
static int parse_long(const char *v, long *out)
{
    const char *p = v;
    int neg = 0;
    if (*p == '-') {
        neg = 1;
        p++;
    }
    if (!isdigit((unsigned char)*p))
        return -1;
    int base = (p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) ? 16 : 10;
    char *end;
    errno = 0;
    unsigned long long n = strtoull(p, &end, base);
    if (errno || end == p)
        return -1;
    while (isspace((unsigned char)*end))
        end++;
    if (*end)
        return -1;
    *out = neg ? -(long)n : (long)n;
    return 0;
}

static int preadall(int fd, void *buf, size_t n, off_t off)
{
    u8 *p = buf;
    while (n) {
        ssize_t r = pread(fd, p, n, off);
        if (r <= 0)
            return -1;
        p += r;
        n -= (size_t)r;
        off += r;
    }
    return 0;
}

/* read our own memory without crashing on a bad pointer (wrong offset in the config) */
static int safe_read(uptr addr, void *out, size_t n)
{
    struct iovec l = { out, n }, r = { (void *)addr, n };
    long rc = syscall(SYS_process_vm_readv, (long)getpid(), &l, 1UL, &r, 1UL, 0UL);
    return rc == (long)n ? 0 : -1;
}

/* ------------------------------------------------------------------ */
/* configuration                                                       */
/* ------------------------------------------------------------------ */
#define NCHEST 10
#define MAXLOOT 256
#define MAXROLES 64
#define MAXLIST 4

enum { MODE_LOG, MODE_PROBE, MODE_LIVE };
static const char *MODENAME[] = { "log", "probe", "live" };

enum { C_COUNT, C_REMOVE, C_OBTAIN, C_LOTADD, C_INFO, C_INV, C_MSG, C_RAW, C_SAFELOCK,
       C_AUX1, C_AUX2, C_AUX3, C_AUX4, NCALLS };
static const char *CALLNAME[NCALLS] = { "count", "remove", "obtain", "lotadd", "info",
    "inv", "msg", "raw", "safelock", "aux1", "aux2", "aux3", "aux4" };

enum { EV_SEEK, EV_OPEN, EV_REFRESH, NEVENTS };
static const char *EVNAME[NEVENTS] = { "seek", "open", "refresh" };

enum { A_NONE, A_REFRESH, A_OPEN, A_SEEK, A_SEEK_AURUM };
static const char *ACTNAME[] = { "pass", "window", "open", "seek", "aurum-seek" };

typedef struct {
    char sym[256];  /* mangled symbol name, or 0x<address> as printed by nm/objdump */
    char args[256]; /* comma-separated argument words, see tokval() */
    char ok[16];    /* how to read the return value: any|true|false|nonzero|zero */
    int pre[MAXLIST], npre; /* calls to run first (their results: ret.<name>) */
    uptr addr;      /* resolved address, 0 = not configured or not usable */
} callspec_t;

typedef struct { u32 id; double p; u32 count; } loot_t;

typedef struct {
    int mode;
    u32 allow[MAXROLES];
    int nallow, allow_all;
    long off_parent, off_runner, off_roleid, off_csidx, off_cssid, off_ctrl_imp;
    char hook_mode[16]; /* notice1 | command */
    char notice1_sym[256], cmd_sym[256], scan_funcs[256];
    int patch;
    long hook_ret;
    long cmd_id, cmd_type_off, cmd_param_off, cmd_ret;
    long cmd_log;      /* notice1 mode: also record this client command (197) in hook.log */
    int cmd_log_all;   /* 1 = record every type, 0 = only types gs does not accept (not 0-3) */
    long type_refresh, type_open, type_seek, type_seek_aurum, aurum_param;
    u32 key_item, keys_per_seek, aurum_cost, aurum_free, chest_base;
    u32 cost[NCHEST];
    loot_t loot[MAXLOOT];
    int nloot, loot_unique;
    double loot_sum;
    char deliver[16];   /* bag | lotadd */
    int seek_clear;     /* 1 = send an empty board before a new one (clears old opened-chest pictures) */
    char info_send[16]; /* native | raw | none */
    char lot_layout[256], box_layout[256], raw_info[512];
    u32 err_nokeys, err_noaurum, err_bagfull, err_safelock;
    char state_dir[256];
    u32 probe_manager, probe_free, probe_score, probe_fill;
    char probe_send[16]; /* info | inv | both | none */
    callspec_t call[NCALLS];
    int on[NEVENTS][MAXLIST], non[NEVENTS];
} cfg_t;

static void cfg_defaults(cfg_t *c)
{
    static const u32 dcost[NCHEST] = { 0, 5, 12, 30, 75, 188, 466, 1166, 2998, 4198 };
    memset(c, 0, sizeof *c);
    c->mode = MODE_LOG;
    c->hook_ret = 1; /* gs: Lottery_Notice1 returning false makes CommandHandler send error 3 ("invalid action") */
    c->off_parent = c->off_runner = c->off_roleid = c->off_csidx = c->off_cssid = -1;
    c->off_ctrl_imp = -1;
    copyz(c->hook_mode, sizeof c->hook_mode, "notice1");
    c->patch = 1;
    c->cmd_log = -1;
    c->cmd_id = -1;     /* command mode: the Treasures C2S id (197 in the 1.7.6 source) */
    c->cmd_type_off = 2; /* lottery_manager { u16 cmd; u32 manager; u8 param[] } */
    c->cmd_param_off = 6;
    c->type_refresh = 0; /* the 1.7.3 log lines: "0 0" window, "1 n" open, "3 0" seek */
    c->type_open = 1;
    c->type_seek = 3;
    c->type_seek_aurum = -1; /* unknown until the log shows what the Aurum button sends */
    c->aurum_param = -1;
    c->key_item = 56274; /* Lucky Key, LOTTORY_TICKET_COST_CONFIG record 2313 */
    c->keys_per_seek = 2;
    c->aurum_cost = 20;
    c->aurum_free = 2;
    memcpy(c->cost, dcost, sizeof dcost);
    c->loot_unique = 1;
    copyz(c->deliver, sizeof c->deliver, "bag");
    copyz(c->info_send, sizeof c->info_send, "native");
    copyz(c->lot_layout, sizeof c->lot_layout, "id:u32, count:u32, lot:u8");
    copyz(c->box_layout, sizeof c->box_layout, "id:u32, box:u32, count:u32, lot:u8");
    copyz(c->raw_info, sizeof c->raw_info,
          "u16:434, u8:manager, u32:score, u32:free, u32:nlots, u32:nboxes, lots, boxes");
    copyz(c->state_dir, sizeof c->state_dir, "/opt/treasure_hook/state");
    c->probe_manager = 1;
    c->probe_free = 1;
    copyz(c->probe_send, sizeof c->probe_send, "info");
    for (int i = 0; i < NCALLS; i++) /* item functions are bool: success = true */
        copyz(c->call[i].ok, sizeof c->call[i].ok,
              (i == C_COUNT || i == C_REMOVE || i == C_OBTAIN || i == C_LOTADD) ? "true" : "any");
}

static int call_index(const char *nm)
{
    for (int i = 0; i < NCALLS; i++)
        if (!strcmp(nm, CALLNAME[i]))
            return i;
    return -1;
}

static int parse_call_list(const char *v, int *out, int max, int ln)
{
    char tmp[256], *save = NULL, *t;
    int n = 0;
    copyz(tmp, sizeof tmp, v);
    for (t = strtok_r(tmp, ", \t", &save); t && n < max; t = strtok_r(NULL, ", \t", &save)) {
        int i = call_index(t);
        if (i < 0)
            tlog("conf line %d: unknown call name '%s'", ln, t);
        else
            out[n++] = i;
    }
    return n;
}

static int ok_valid(const char *s)
{
    return !strcmp(s, "any") || !strcmp(s, "true") || !strcmp(s, "false") ||
           !strcmp(s, "nonzero") || !strcmp(s, "zero");
}

static void parse_loot(cfg_t *c, char *v, int ln)
{
    char *f[3] = { 0 }, *save = NULL, *t;
    int n = 0;
    for (t = strtok_r(v, ",", &save); t && n < 3; t = strtok_r(NULL, ",", &save))
        f[n++] = trim(t);
    long id = 0, cnt = 1;
    char *end = NULL;
    double p = n >= 2 ? strtod(f[1], &end) : 0;
    if (n < 2 || parse_long(f[0], &id) || id <= 0 || !end || end == f[1] || *trim(end) ||
        !(p > 0) || (n == 3 && (parse_long(f[2], &cnt) || cnt <= 0))) {
        tlog("conf line %d: bad loot line (need: item id, chance, count)", ln);
        return;
    }
    if (c->nloot >= MAXLOOT) {
        tlog("conf line %d: more than %d loot lines, ignored", ln, MAXLOOT);
        return;
    }
    c->loot[c->nloot].id = (u32)id;
    c->loot[c->nloot].p = p;
    c->loot[c->nloot].count = (u32)cnt;
    c->nloot++;
}

static void parse_allow(cfg_t *c, char *v, int ln)
{
    char *save = NULL, *t;
    c->nallow = 0;
    c->allow_all = 0;
    for (t = strtok_r(v, ", \t", &save); t; t = strtok_r(NULL, ", \t", &save)) {
        long id;
        if (!strcmp(t, "all") || !strcmp(t, "*"))
            c->allow_all = 1;
        else if (parse_long(t, &id) || id <= 0)
            tlog("conf line %d: '%s' is not a role id", ln, t);
        else if (c->nallow < MAXROLES)
            c->allow[c->nallow++] = (u32)id;
    }
}

static void parse_cost(cfg_t *c, char *v, int ln)
{
    u32 tmp[NCHEST];
    char *save = NULL, *t;
    int n = 0, bad = 0;
    for (t = strtok_r(v, ", \t", &save); t; t = strtok_r(NULL, ", \t", &save)) {
        long x;
        if (n >= NCHEST || parse_long(t, &x) || x < 0)
            bad = 1;
        else
            tmp[n++] = (u32)x;
    }
    if (bad || n != NCHEST)
        tlog("conf line %d: cost needs %d whole numbers; kept the old costs", ln, NCHEST);
    else
        memcpy(c->cost, tmp, sizeof tmp);
}

static int cfg_load(const char *path, cfg_t *c)
{
    FILE *f = fopen(path, "re");
    if (!f)
        return -1;
    cfg_defaults(c);
    char line[1024];
    int ln = 0;
    while (fgets(line, sizeof line, f)) {
        ln++;
        size_t len = strlen(line);
        if (len == sizeof line - 1 && line[len - 1] != '\n' && !feof(f)) {
            int ch;
            while ((ch = fgetc(f)) != EOF && ch != '\n')
                ;
            tlog("conf line %d: longer than %d characters, ignored", ln, (int)sizeof line - 2);
            continue;
        }
        char *h = strchr(line, '#');
        if (h)
            *h = 0;
        char *eq = strchr(line, '=');
        if (!eq) {
            if (*trim(line))
                tlog("conf line %d: no '=' on this line, ignored", ln);
            continue;
        }
        *eq = 0;
        char *k = trim(line), *v = trim(eq + 1);
        if (!*k)
            continue;
#define IS(name) (!strcmp(k, name))
#define STR(field) copyz(c->field, sizeof c->field, v)
#define NUM(field)                                                                          \
    do {                                                                                    \
        long n_;                                                                            \
        if (parse_long(v, &n_))                                                             \
            tlog("conf line %d: %s needs a number; kept %ld", ln, k, (long)c->field);       \
        else                                                                                \
            c->field = n_;                                                                  \
    } while (0)
#define UNUM(field)                                                                         \
    do {                                                                                    \
        long n_;                                                                            \
        if (parse_long(v, &n_) || n_ < 0)                                                   \
            tlog("conf line %d: %s needs a whole number; kept %lu", ln, k,                  \
                 (unsigned long)c->field);                                                  \
        else                                                                                \
            c->field = (u32)n_;                                                             \
    } while (0)
        if (IS("mode")) {
            if (!strcmp(v, "live")) c->mode = MODE_LIVE;
            else if (!strcmp(v, "probe")) c->mode = MODE_PROBE;
            else if (!strcmp(v, "log")) c->mode = MODE_LOG;
            else tlog("conf line %d: mode must be log, probe or live; using log", ln);
        } else if (IS("allow_roles")) parse_allow(c, v, ln);
        else if (IS("off.parent")) NUM(off_parent);
        else if (IS("off.runner")) NUM(off_runner);
        else if (IS("off.roleid")) NUM(off_roleid);
        else if (IS("off.csidx")) NUM(off_csidx);
        else if (IS("off.cssid")) NUM(off_cssid);
        else if (IS("off.ctrl_imp")) NUM(off_ctrl_imp);
        else if (IS("hook.mode")) {
            if (!strcmp(v, "notice1") || !strcmp(v, "command")) STR(hook_mode);
            else tlog("conf line %d: hook.mode must be notice1 or command", ln);
        } else if (IS("hook.notice1")) STR(notice1_sym);
        else if (IS("hook.command")) STR(cmd_sym);
        else if (IS("hook.scan_funcs")) STR(scan_funcs);
        else if (IS("hook.patch")) c->patch = parse_bool(v);
        else if (IS("hook.ret")) NUM(hook_ret);
        else if (IS("cmd.id")) NUM(cmd_id);
        else if (IS("cmd.log") && (!strcmp(v, "any") || !strcmp(v, "all"))) c->cmd_log = -2;
        else if (IS("cmd.log")) NUM(cmd_log);
        else if (IS("cmd.log_all")) c->cmd_log_all = parse_bool(v);
        else if (IS("cmd.type_off")) NUM(cmd_type_off);
        else if (IS("cmd.param_off")) NUM(cmd_param_off);
        else if (IS("cmd.ret")) NUM(cmd_ret);
        else if (IS("type.refresh")) NUM(type_refresh);
        else if (IS("type.open")) NUM(type_open);
        else if (IS("type.seek")) NUM(type_seek);
        else if (IS("type.seek_aurum")) NUM(type_seek_aurum);
        else if (IS("aurum_param")) NUM(aurum_param);
        else if (IS("key_item")) UNUM(key_item);
        else if (IS("keys_per_seek")) UNUM(keys_per_seek);
        else if (IS("aurum_cost")) UNUM(aurum_cost);
        else if (IS("aurum_free")) UNUM(aurum_free);
        else if (IS("chest_base")) UNUM(chest_base);
        else if (IS("cost")) parse_cost(c, v, ln);
        else if (IS("loot")) parse_loot(c, v, ln);
        else if (IS("loot.unique")) c->loot_unique = parse_bool(v);
        else if (IS("seek.clear")) c->seek_clear = !strcmp(v, "empty") || !strcmp(v, "yes") || !strcmp(v, "1");
        else if (IS("deliver")) {
            if (!strcmp(v, "bag") || !strcmp(v, "lotadd")) STR(deliver);
            else tlog("conf line %d: deliver must be bag or lotadd", ln);
        } else if (IS("info.send")) {
            if (!strcmp(v, "native") || !strcmp(v, "raw") || !strcmp(v, "none")) STR(info_send);
            else tlog("conf line %d: info.send must be native, raw or none", ln);
        } else if (IS("lot.layout")) STR(lot_layout);
        else if (IS("box.layout")) STR(box_layout);
        else if (IS("raw.info")) STR(raw_info);
        else if (IS("err.nokeys")) UNUM(err_nokeys);
        else if (IS("err.noaurum")) UNUM(err_noaurum);
        else if (IS("err.bagfull")) UNUM(err_bagfull);
        else if (IS("err.safelock")) UNUM(err_safelock);
        else if (IS("state_dir")) {
            if (*v == '/') STR(state_dir);
            else tlog("conf line %d: state_dir must be a full path; kept %s", ln, c->state_dir);
        } else if (IS("probe.manager")) UNUM(probe_manager);
        else if (IS("probe.free")) UNUM(probe_free);
        else if (IS("probe.score")) UNUM(probe_score);
        else if (IS("probe.fill")) UNUM(probe_fill);
        else if (IS("probe.send")) STR(probe_send);
        else if (!strncmp(k, "on.", 3)) {
            int e;
            for (e = 0; e < NEVENTS; e++)
                if (!strcmp(k + 3, EVNAME[e]))
                    break;
            if (e == NEVENTS)
                tlog("conf line %d: unknown event '%s'", ln, k + 3);
            else
                c->non[e] = parse_call_list(v, c->on[e], MAXLIST, ln);
        } else if (!strncmp(k, "call.", 5) || !strncmp(k, "ok.", 3) || !strncmp(k, "pre.", 4)) {
            const char *nm = strchr(k, '.') + 1;
            int i = call_index(nm);
            if (i < 0) {
                tlog("conf line %d: unknown call '%s'", ln, nm);
                continue;
            }
            callspec_t *cs = &c->call[i];
            if (k[0] == 'o')
                copyz(cs->ok, sizeof cs->ok, v);
            else if (k[0] == 'p')
                cs->npre = parse_call_list(v, cs->pre, MAXLIST, ln);
            else {
                char *colon = strchr(v, ':');
                cs->args[0] = 0;
                if (colon) {
                    *colon = 0;
                    copyz(cs->args, sizeof cs->args, trim(colon + 1));
                }
                copyz(cs->sym, sizeof cs->sym, trim(v));
            }
        } else
            tlog("conf line %d: unknown key '%s' (ignored)", ln, k);
#undef IS
#undef STR
#undef NUM
#undef UNUM
    }
    fclose(f);
    c->loot_sum = 0;
    for (int i = 0; i < c->nloot; i++)
        c->loot_sum += c->loot[i].p;
    for (int i = 0; i < NCALLS; i++) {
        callspec_t *cs = &c->call[i];
        if (!ok_valid(cs->ok)) {
            tlog("ok.%s = %s is not one of any/true/false/nonzero/zero; the call will count as failed",
                 CALLNAME[i], cs->ok);
            copyz(cs->ok, sizeof cs->ok, "invalid");
        }
        if (!cs->sym[0] || strcmp(cs->ok, "any"))
            continue;
        if (i == C_COUNT || i == C_REMOVE || i == C_OBTAIN || i == C_LOTADD)
            tlog("WARNING ok.%s = any: every result counts as success", CALLNAME[i]);
        if (i == C_SAFELOCK)
            tlog("WARNING ok.safelock = any: the safety lock check has no effect");
    }
    return 0;
}

/* ------------------------------------------------------------------ */
/* gs symbol table, read from /proc/self/exe with pread (not mmap: the */
/* 1.7.3 gs file is ~614 MB and the process is 32-bit)                 */
/* ------------------------------------------------------------------ */
typedef struct {
    ElfW(Sym) *syms;
    size_t nsyms;
    char *str;
    size_t strsz;
    ElfW(Word) *shflags; /* sh_flags per section index */
    size_t nsh;
} symtab_t;

static uptr g_base; /* load address of gs (0 for a classic non-PIE program) */

static int phdr_cb(th_phdr_info_t *info, size_t sz, void *data)
{
    (void)sz;
    *(uptr *)data = (uptr)info->dlpi_addr; /* the first entry is the main program */
    return 1;
}

static void symtab_free(symtab_t *t)
{
    free(t->syms);
    free(t->str);
    free(t->shflags);
    memset(t, 0, sizeof *t);
}

static int symtab_load(symtab_t *t)
{
    memset(t, 0, sizeof *t);
    int fd = open("/proc/self/exe", O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -1;
    ElfW(Ehdr) eh;
    ElfW(Shdr) *sh = NULL;
    int rc = -1;
    if (preadall(fd, &eh, sizeof eh, 0) || memcmp(eh.e_ident, ELFMAG, SELFMAG) ||
        eh.e_ident[EI_CLASS] != TH_ELFCLASS || eh.e_shentsize != sizeof(ElfW(Shdr)) || !eh.e_shnum)
        goto out;
    sh = malloc((size_t)eh.e_shnum * sizeof *sh);
    if (!sh || preadall(fd, sh, (size_t)eh.e_shnum * sizeof *sh, (off_t)eh.e_shoff))
        goto out;
    int si = -1;
    for (int i = 0; i < eh.e_shnum; i++)
        if (sh[i].sh_type == SHT_SYMTAB) { si = i; break; }
    if (si < 0)
        for (int i = 0; i < eh.e_shnum; i++)
            if (sh[i].sh_type == SHT_DYNSYM) { si = i; break; }
    if (si < 0 || sh[si].sh_link >= eh.e_shnum)
        goto out;
    ElfW(Shdr) *ss = &sh[si], *st = &sh[ss->sh_link];
    t->nsyms = ss->sh_size / sizeof(ElfW(Sym));
    t->syms = malloc(ss->sh_size ? ss->sh_size : 1);
    t->str = malloc(st->sh_size + 1);
    t->shflags = malloc((size_t)eh.e_shnum * sizeof *t->shflags);
    if (!t->syms || !t->str || !t->shflags ||
        preadall(fd, t->syms, ss->sh_size, (off_t)ss->sh_offset) ||
        preadall(fd, t->str, st->sh_size, (off_t)st->sh_offset))
        goto out;
    t->str[st->sh_size] = 0;
    t->strsz = st->sh_size;
    t->nsh = eh.e_shnum;
    for (int i = 0; i < eh.e_shnum; i++)
        t->shflags[i] = (ElfW(Word))sh[i].sh_flags;
    rc = 0;
out:
    free(sh);
    close(fd);
    if (rc)
        symtab_free(t);
    return rc;
}

static const char *symname(const symtab_t *t, const ElfW(Sym) *s)
{
    return s->st_name < t->strsz ? t->str + s->st_name : "";
}

/* defined, non-zero, in a section that is loaded into memory */
static int sym_loaded(const symtab_t *t, const ElfW(Sym) *s)
{
    if (!s->st_name || !s->st_value || s->st_shndx == SHN_UNDEF || s->st_shndx >= SHN_LORESERVE)
        return 0;
    return s->st_shndx < t->nsh && (t->shflags[s->st_shndx] & SHF_ALLOC);
}

/* a function we may call or hook: global/weak, and not a compiler-made copy
 * (".part.0", ".isra.0", ".constprop.0", ".cold": those may take their
 * arguments in registers instead of on the stack) */
static int sym_callable(const symtab_t *t, const ElfW(Sym) *s)
{
    if (ST_TYPE(s->st_info) != STT_FUNC || !sym_loaded(t, s))
        return 0;
    int b = ST_BIND(s->st_info);
    return (b == STB_GLOBAL || b == STB_WEAK) && !strchr(symname(t, s), '.');
}

static int sym_find_func(const symtab_t *t, const char *name, uptr *addr, size_t *size)
{
    int seen = 0;
    for (size_t i = 0; i < t->nsyms; i++) {
        const ElfW(Sym) *s = &t->syms[i];
        if (strcmp(symname(t, s), name))
            continue;
        if (sym_callable(t, s)) {
            *addr = (uptr)s->st_value + g_base;
            if (size)
                *size = s->st_size;
            return 1;
        }
        seen = 1;
    }
    if (seen)
        tlog("%s exists but is not a global function; it may not be called or hooked", name);
    return 0;
}

/* resolved names are cached, so a config reload does not re-read the big gs file */
static struct { char name[256]; uptr addr; } g_symcache[NCALLS * 2];
static int g_nsymcache;

static int cache_get(const char *name, uptr *addr)
{
    for (int i = 0; i < g_nsymcache; i++)
        if (!strcmp(g_symcache[i].name, name)) {
            *addr = g_symcache[i].addr;
            return 1;
        }
    return 0;
}

static int page_prot(uptr addr);

/* t = an already loaded symbol table, or NULL (then it is loaded if needed) */
static void cfg_resolve(cfg_t *c, symtab_t *t)
{
    int missing = 0;
    for (int i = 0; i < NCALLS; i++) {
        callspec_t *cs = &c->call[i];
        cs->addr = 0;
        if (!cs->sym[0])
            continue;
        if (!strncmp(cs->sym, "0x", 2)) {
            uptr a = (uptr)strtoull(cs->sym, NULL, 16) + g_base;
            int prot = page_prot(a);
            if (prot < 0 || !(prot & PROT_EXEC))
                tlog("call.%s: %s is not in program code; refused", CALLNAME[i], cs->sym);
            else {
                cs->addr = a;
                tlog("call.%s: raw address %s used as given (not checked against symbols)",
                     CALLNAME[i], cs->sym);
            }
        } else if (!cache_get(cs->sym, &cs->addr))
            missing = 1;
    }
    if (!missing)
        return;
    symtab_t own;
    symtab_t *use = t;
    if (!use) {
        tlog("reading the gs symbol table for new call names");
        if (symtab_load(&own)) {
            tlog("cannot read the gs symbol table; new call names stay unresolved");
            return;
        }
        use = &own;
    }
    for (int i = 0; i < NCALLS; i++) {
        callspec_t *cs = &c->call[i];
        if (!cs->sym[0] || cs->addr || !strncmp(cs->sym, "0x", 2))
            continue;
        if (sym_find_func(use, cs->sym, &cs->addr, NULL)) {
            if (g_nsymcache == (int)(sizeof g_symcache / sizeof g_symcache[0]))
                g_nsymcache = 0;
            copyz(g_symcache[g_nsymcache].name, sizeof g_symcache[0].name, cs->sym);
            g_symcache[g_nsymcache++].addr = cs->addr;
        } else
            tlog("call.%s: function not found: %s", CALLNAME[i], cs->sym);
    }
    if (use == &own)
        symtab_free(&own);
}

/* ------------------------------------------------------------------ */
/* patching memory                                                      */
/* ------------------------------------------------------------------ */
static int page_prot(uptr addr)
{
    FILE *f = fopen("/proc/self/maps", "re");
    if (!f)
        return -1;
    char line[512];
    int prot = -1;
    while (fgets(line, sizeof line, f)) {
        unsigned long a, b;
        char perms[8];
        if (sscanf(line, "%lx-%lx %7s", &a, &b, perms) == 3 && addr >= a && addr < b) {
            prot = 0;
            if (perms[0] == 'r') prot |= PROT_READ;
            if (perms[1] == 'w') prot |= PROT_WRITE;
            if (perms[2] == 'x') prot |= PROT_EXEC;
            break;
        }
    }
    fclose(f);
    return prot;
}

static int poke(uptr addr, const void *val, size_t n)
{
    uptr ps = (uptr)sysconf(_SC_PAGESIZE);
    uptr p0 = addr & ~(ps - 1), p1 = (addr + n - 1) & ~(ps - 1);
    int prot0 = page_prot(p0), prot1 = page_prot(p1);
    if (prot0 < 0 || prot1 < 0)
        return -1;
    if (mprotect((void *)p0, (p1 - p0) + ps, PROT_READ | PROT_WRITE | PROT_EXEC))
        return -1;
    memcpy((void *)addr, val, n);
    __builtin___clear_cache((char *)addr, (char *)addr + n);
    mprotect((void *)p0, ps, prot0);
    if (p1 != p0)
        mprotect((void *)p1, ps, prot1);
    return 0;
}

#if defined(__x86_64__)
/* 64-bit only: a direct call (rel32) cannot reach a library 2+ GB away, so it is
 * pointed at a small "jmp [rip]" stub placed near gs instead. 32-bit gs never needs it. */
static int in_reach(uptr from_next, uptr to)
{
    long long d = (long long)to - (long long)from_next;
    return d > -0x7fff0000LL && d < 0x7fff0000LL;
}

static uptr tramp_near(uptr site, uptr dest)
{
    static uptr page, used;
    uptr ps = (uptr)sysconf(_SC_PAGESIZE);
    if (!page || used + 16 > ps || !in_reach(site + 5, page)) {
        page = 0;
        for (long k = 1; k < 120 && !page; k++)
            for (int sgn = -1; sgn <= 1 && !page; sgn += 2) {
                uptr hint = (site & ~(ps - 1)) + (uptr)(sgn * k * (16L << 20));
                void *p = mmap((void *)hint, ps, PROT_READ | PROT_WRITE,
                               MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
                if (p == MAP_FAILED)
                    continue;
                if (in_reach(site + 5, (uptr)p))
                    page = (uptr)p;
                else
                    munmap(p, ps);
            }
        used = 0;
        if (!page)
            return 0;
    }
    u8 stub[14] = { 0xFF, 0x25, 0, 0, 0, 0 }; /* jmp qword [rip+0] ; .quad dest */
    memcpy(stub + 6, &dest, 8);
    uptr at = page + used;
    mprotect((void *)page, ps, PROT_READ | PROT_WRITE);
    memcpy((void *)at, stub, sizeof stub);
    mprotect((void *)page, ps, PROT_READ | PROT_EXEC);
    __builtin___clear_cache((char *)at, (char *)at + sizeof stub);
    used += 16;
    return at;
}
#endif

/* ------------------------------------------------------------------ */
/* live config: re-read when the file changes. A new config is swapped */
/* in atomically and the old one is kept (never freed), so no lock is   */
/* needed while a command is being handled.                             */
/* ------------------------------------------------------------------ */
static cfg_t *g_cfg;
static struct timespec g_cfg_mtim;
static off_t g_cfg_size;
static ino_t g_cfg_ino;

static const cfg_t *cfg_now(void) { return __atomic_load_n(&g_cfg, __ATOMIC_ACQUIRE); }

static void maybe_reload(symtab_t *t)
{
    if (pthread_mutex_trylock(&g_reloadmx))
        return; /* another thread is reloading right now */
    struct stat st;
    if (stat(g_confpath, &st) == 0 &&
        !(g_cfg && st.st_mtim.tv_sec == g_cfg_mtim.tv_sec && st.st_mtim.tv_nsec == g_cfg_mtim.tv_nsec &&
          st.st_size == g_cfg_size && st.st_ino == g_cfg_ino)) {
        cfg_t *n = calloc(1, sizeof *n);
        if (n && cfg_load(g_confpath, n) == 0) {
            cfg_resolve(n, t);
            g_cfg_mtim = st.st_mtim;
            g_cfg_size = st.st_size;
            g_cfg_ino = st.st_ino;
            __atomic_store_n(&g_cfg, n, __ATOMIC_RELEASE);
            char calls[512] = "";
            for (int i = 0; i < NCALLS; i++)
                if (n->call[i].sym[0]) {
                    size_t l = strlen(calls);
                    snprintf(calls + l, sizeof calls - l, " %s=%s", CALLNAME[i],
                             n->call[i].addr ? "ok" : "MISSING");
                }
            tlog("config loaded: mode=%s loot=%d allow=%s%d deliver=%s info=%s calls:%s",
                 MODENAME[n->mode], n->nloot, n->allow_all ? "all+" : "", n->nallow, n->deliver,
                 n->info_send, calls[0] ? calls : " none");
        } else
            free(n);
    }
    pthread_mutex_unlock(&g_reloadmx);
}

/* ------------------------------------------------------------------ */
/* calling gs functions                                                 */
/* ------------------------------------------------------------------ */
typedef struct {
    uptr imp, runner, parent;
    u32 roleid;
    s32 csidx, cssid;
    s32 type, param;
    u32 id, count, slot, lot;   /* item being checked/taken/given; chest position; prize index */
    u32 manager, score, free_c; /* board values */
    u32 nlots, nboxes;
    u8 *lots, *boxes;
    u32 lots_bytes, boxes_bytes;
    u8 *buf;
    u32 len;
    u32 err;
    u32 out1, out2;   /* out-parameters: pass "&out1" to a call, read "out1" after */
    uptr ret[NCALLS]; /* return value of each call made for this command */
    u32 ran;          /* bit i set = call i ran for this command */
} ctx_t;

/* *bad: 1 = unknown word, 2 = pointer is 0, 3 = ret.X before call X ran */
static uptr tokval(const char *t, const ctx_t *x, int *bad)
{
    if (isdigit((unsigned char)t[0]) || t[0] == '-') {
        long n;
        if (parse_long(t, &n)) {
            *bad = 1;
            return 0;
        }
        return (uptr)n;
    }
    if (!strncmp(t, "ret.", 4)) {
        int i = call_index(t + 4);
        if (i < 0) {
            *bad = 1;
            return 0;
        }
        if (!(x->ran & (1u << i)))
            *bad = 3;
        else if (!x->ret[i])
            *bad = 2;
        return x->ret[i];
    }
#define T(name, val) if (!strcmp(t, name)) return (uptr)(val)
#define P(name, val) if (!strcmp(t, name)) { if (!(val)) *bad = 2; return (uptr)(val); }
    P("imp", x->imp);
    P("runner", x->runner);
    P("parent", x->parent);
    P("lots", x->lots);
    P("boxes", x->boxes);
    P("buf", x->buf);
    T("&out1", &x->out1);
    T("&out2", &x->out2);
    T("out1", x->out1);
    T("out2", x->out2);
    T("roleid", x->roleid);
    T("csidx", x->csidx);
    T("cssid", x->cssid);
    T("type", x->type);
    T("param", x->param);
    T("id", x->id);
    T("count", x->count);
    T("slot", x->slot);
    T("lot", x->lot);
    T("manager", x->manager);
    T("score", x->score);
    T("free", x->free_c);
    T("nlots", x->nlots);
    T("nboxes", x->nboxes);
    T("lotsbytes", x->lots_bytes);
    T("boxesbytes", x->boxes_bytes);
    T("len", x->len);
    T("err", x->err);
    T("true", 1);
    T("false", 0);
    T("null", 0);
#undef T
#undef P
    *bad = 1;
    return 0;
}

typedef uptr (*fn12_t)(uptr, uptr, uptr, uptr, uptr, uptr, uptr, uptr, uptr, uptr, uptr, uptr);

/* The call goes through this small function that keeps a frame pointer: its
 * closing "leave" restores the stack pointer even if the called function pops
 * extra bytes (functions returning a struct do "ret 4" on i386). Only call
 * functions that return void, bool, an integer or a pointer. */
#if defined(__i386__)
__attribute__((noinline, optimize("no-omit-frame-pointer")))
#else
__attribute__((noinline))
#endif
static uptr call12(uptr fn, const uptr *a)
{
    return ((fn12_t)fn)(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9], a[10], a[11]);
}

/* 0 = called and the result is "ok", 1 = called but not ok (or refused),
 * -1 = not configured / not usable, -2 = bad argument list */
static int call_fn_d(const cfg_t *c, int which, ctx_t *x, int depth)
{
    const callspec_t *cs = &c->call[which];
    if (!cs->addr)
        return -1;
    if (depth > 3) {
        tlog("call.%s: pre-call chain too deep", CALLNAME[which]);
        return -2;
    }
    for (int i = 0; i < cs->npre; i++) {
        int r = call_fn_d(c, cs->pre[i], x, depth + 1);
        if (r) {
            tlog("call.%s: pre-call %s failed (rc %d)", CALLNAME[which], CALLNAME[cs->pre[i]], r);
            return r < 0 ? r : 1;
        }
    }
    uptr a[12] = { 0 };
    int n = 0;
    char tmp[256], *save = NULL, *t;
    copyz(tmp, sizeof tmp, cs->args);
    for (t = strtok_r(tmp, ",", &save); t; t = strtok_r(NULL, ",", &save)) {
        t = trim(t);
        if (!*t)
            continue;
        if (n == 12) {
            tlog("call.%s: more than 12 arguments", CALLNAME[which]);
            return -2;
        }
        int bad = 0;
        a[n++] = tokval(t, x, &bad);
        if (bad == 1) {
            tlog("call.%s: unknown argument '%s'", CALLNAME[which], t);
            return -2;
        }
        if (bad) {
            tlog("call.%s refused: argument '%s' is %s", CALLNAME[which], t,
                 bad == 2 ? "0 (check the off.* lines / the call that makes it)"
                          : "the result of a call that has not run");
            return 1;
        }
    }
    if (!strcmp(cs->ok, "invalid"))
        return 1;
    uptr r = call12(cs->addr, a);
    x->ret[which] = r;
    x->ran |= 1u << which;
    int ok = 1;
    if (!strcmp(cs->ok, "true"))
        ok = (r & 0xff) != 0; /* a C++ bool comes back in AL only */
    else if (!strcmp(cs->ok, "false"))
        ok = (r & 0xff) == 0;
    else if (!strcmp(cs->ok, "nonzero"))
        ok = r != 0;
    else if (!strcmp(cs->ok, "zero"))
        ok = r == 0;
    return ok ? 0 : 1;
}

static int call_fn(const cfg_t *c, int which, ctx_t *x) { return call_fn_d(c, which, x, 0); }

static void run_event(const cfg_t *c, int ev, ctx_t *x)
{
    for (int i = 0; i < c->non[ev]; i++) {
        int r = call_fn(c, c->on[ev][i], x);
        tlog("on.%s: call.%s rc %d", EVNAME[ev], CALLNAME[c->on[ev][i]], r);
    }
}

/* ------------------------------------------------------------------ */
/* packets                                                              */
/* ------------------------------------------------------------------ */
typedef struct { u32 id, count, box, order; } prize_t; /* order: 0 = not opened, else 1..10 */

static int put_le(u8 *out, u32 cap, u32 *pos, const char *type, u32 v)
{
    u32 sz = !strcmp(type, "u8") ? 1 : !strcmp(type, "u16") ? 2 : !strcmp(type, "u32") ? 4 : 0;
    if (!sz || *pos + sz > cap)
        return -1;
    for (u32 i = 0; i < sz; i++)
        out[*pos + i] = (u8)(v >> (8 * i));
    *pos += sz;
    return 0;
}

/* layout e.g. "id:u32, box:u32, count:u32, lot:u8"; fields id count lot box pos order open zero.
 * On any problem nothing of this entry is kept (*pos is put back). */
static int pack_entry(const char *layout, const prize_t *p, u32 lot, u8 *out, u32 cap, u32 *pos)
{
    char tmp[256], *save = NULL, *t;
    u32 start = *pos;
    copyz(tmp, sizeof tmp, layout);
    for (t = strtok_r(tmp, ",", &save); t; t = strtok_r(NULL, ",", &save)) {
        t = trim(t);
        char *colon = strchr(t, ':');
        if (!colon)
            continue;
        *colon = 0;
        const char *f = trim(t), *ty = trim(colon + 1);
        u32 v = !strcmp(f, "id") ? p->id : !strcmp(f, "count") ? p->count :
                !strcmp(f, "lot") ? lot : !strcmp(f, "box") ? p->box :
                !strcmp(f, "pos") ? p->box + 1 : !strcmp(f, "order") ? p->order :
                !strcmp(f, "open") ? (p->order != 0) : 0;
        if (put_le(out, cap, pos, ty, v)) {
            *pos = start;
            return -1;
        }
    }
    return 0;
}

/* raw.info = u16:434, u8:manager, ..., lots, boxes  (u8/u16/u32 : word or number).
 * Returns the packet length, or 0 if the spec has a problem (then nothing is sent). */
static u32 build_raw(const char *spec, const ctx_t *x, u8 *out, u32 cap)
{
    u32 pos = 0;
    char tmp[512], *save = NULL, *t;
    copyz(tmp, sizeof tmp, spec);
    for (t = strtok_r(tmp, ",", &save); t; t = strtok_r(NULL, ",", &save)) {
        t = trim(t);
        if (!strcmp(t, "lots") || !strcmp(t, "boxes")) {
            const u8 *src = t[0] == 'l' ? x->lots : x->boxes;
            u32 n = t[0] == 'l' ? x->lots_bytes : x->boxes_bytes;
            if (pos + n > cap) {
                tlog("raw.info: packet too long");
                return 0;
            }
            if (n)
                memcpy(out + pos, src, n);
            pos += n;
            continue;
        }
        char *colon = strchr(t, ':');
        int bad = !colon;
        u32 v = 0;
        if (colon) {
            *colon = 0;
            v = (u32)tokval(trim(colon + 1), x, &bad);
        }
        if (bad || put_le(out, cap, &pos, trim(t), v)) {
            tlog("raw.info: bad item '%s'; nothing sent", t);
            return 0;
        }
    }
    return pos;
}

static void send_msg(const cfg_t *c, ctx_t *x, u32 code)
{
    if (!code || !c->call[C_MSG].addr)
        return;
    x->err = code;
    call_fn(c, C_MSG, x);
}

static void send_info(const cfg_t *c, ctx_t *x)
{
    if (!strcmp(c->info_send, "raw")) {
        u8 pkt[1024];
        x->len = build_raw(c->raw_info, x, pkt, sizeof pkt);
        if (x->len) {
            x->buf = pkt;
            tlog_hex("raw info packet", pkt, x->len);
            if (call_fn(c, C_RAW, x) < 0)
                tlog("info not sent: call.raw is not configured or not usable");
            x->buf = NULL;
        }
    } else if (!strcmp(c->info_send, "native")) {
        if (x->lots_bytes)
            tlog_hex("LOT entries", x->lots, x->lots_bytes);
        if (x->boxes_bytes)
            tlog_hex("BOX entries", x->boxes, x->boxes_bytes);
        if (call_fn(c, C_INFO, x) < 0)
            tlog("info not sent: call.info is not configured or not usable");
    }
    tlog("board: manager=%u score=%u free=%u lots=%u boxes=%u", x->manager, x->score,
         x->free_c, x->nlots, x->nboxes);
}

/* ------------------------------------------------------------------ */
/* random numbers (re-seeded per process: gs forks one child per map)   */
/* ------------------------------------------------------------------ */
static __thread u32 rng_s;
static __thread pid_t rng_pid;

static u32 rnd(void)
{
    if (!rng_s || rng_pid != getpid()) {
        u32 seed = 0;
        int fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);
        if (fd >= 0) {
            if (read(fd, &seed, sizeof seed) != (ssize_t)sizeof seed)
                seed = 0;
            close(fd);
        }
        struct timeval tv;
        gettimeofday(&tv, NULL);
        rng_s = seed ^ (u32)tv.tv_usec ^ ((u32)getpid() << 16) ^ 0x9e3779b9u;
        if (!rng_s)
            rng_s = 0x12345678u;
        rng_pid = getpid();
    }
    rng_s ^= rng_s << 13;
    rng_s ^= rng_s >> 17;
    rng_s ^= rng_s << 5;
    return rng_s;
}

static double rnd01(void) { return (double)(rnd() >> 8) / 16777216.0; }

/* weighted pick by chance; with used[] given, rows already drawn are skipped */
static int pick_loot(const cfg_t *c, const u8 *used)
{
    double sum = 0;
    for (int i = 0; i < c->nloot; i++)
        if (!used || !used[i])
            sum += c->loot[i].p;
    if (sum <= 0)
        return -1;
    double r = rnd01() * sum;
    int last = -1;
    for (int i = 0; i < c->nloot; i++) {
        if (used && used[i])
            continue;
        last = i;
        r -= c->loot[i].p;
        if (r < 0)
            return i;
    }
    return last;
}

/* ------------------------------------------------------------------ */
/* per-character state file <state_dir>/<roleid>.st                      */
/* (a file, not memory: a board survives map changes and restarts)       */
/* ------------------------------------------------------------------ */
#define TS_MAGIC 0x31485254u /* "TRH1" */
#define TS_VERSION 3u

typedef struct {
    u32 magic, version, roleid;
    u32 manager; /* last board state sent: 0 none yet, 1 after seek, 2 after open */
    u32 score;   /* Aurum: +1 per key seek */
    u32 free_c;  /* free chest opens left */
    u32 active;  /* a board with closed chests is out */
    u32 num_open;
    u32 pay_broken; /* taking keys failed after a paid open: paid opens off on this board */
    prize_t prize[NCHEST]; /* index = prize ("lot"); box = chest position */
    u32 seeks, opens;
} tstate_t;

/* fd >= 0 on success, -1 cannot open, -2 busy (another map process holds it) */
static int state_open(const cfg_t *c, u32 roleid)
{
    char path[600];
    mkdir(c->state_dir, 0700);
    snprintf(path, sizeof path, "%s/%u.st", c->state_dir, roleid);
    int fd = open(path, O_RDWR | O_CREAT | O_CLOEXEC, 0600);
    if (fd < 0)
        return -1;
    for (int i = 0; i < 200; i++) { /* up to about 2 seconds */
        if (flock(fd, LOCK_EX | LOCK_NB) == 0)
            return fd;
        if (errno != EWOULDBLOCK && errno != EINTR)
            break;
        struct timespec ts = { 0, 10 * 1000 * 1000 };
        nanosleep(&ts, NULL);
    }
    close(fd);
    return -2;
}

static void state_read(int fd, tstate_t *s, u32 roleid)
{
    ssize_t r = pread(fd, s, sizeof *s, 0);
    if (r == (ssize_t)sizeof *s && s->magic == TS_MAGIC && s->version == TS_VERSION &&
        s->roleid == roleid)
        return;
    if (r > 0)
        tlog("state file of role %u is unreadable or from another version (%ld bytes); "
             "starting it fresh", roleid, (long)r);
    memset(s, 0, sizeof *s);
    s->magic = TS_MAGIC;
    s->version = TS_VERSION;
    s->roleid = roleid;
}

static int state_commit(int fd, const tstate_t *s)
{
    if (pwrite(fd, s, sizeof *s, 0) != (ssize_t)sizeof *s || fsync(fd)) {
        tlog("could not save the state of role %u: %s", s->roleid, strerror(errno));
        return -1;
    }
    return 0;
}

static void state_close(int fd)
{
    flock(fd, LOCK_UN);
    close(fd);
}

/* ------------------------------------------------------------------ */
/* Treasures logic                                                      */
/* ------------------------------------------------------------------ */
typedef struct { u8 lots[NCHEST * 32], boxes[NCHEST * 32]; } boardbuf_t;

static void fill_board(const cfg_t *c, ctx_t *x, const tstate_t *s, u32 manager, boardbuf_t *b)
{
    u32 lp = 0, bp = 0;
    x->manager = manager;
    x->score = s->score;
    x->free_c = s->free_c;
    x->nlots = x->nboxes = 0;
    if (s->active) /* LOT list: prizes still hidden, in prize order */
        for (u32 i = 0; i < NCHEST; i++)
            if (!s->prize[i].order &&
                pack_entry(c->lot_layout, &s->prize[i], i, b->lots, sizeof b->lots, &lp) == 0)
                x->nlots++;
    for (u32 k = 1; k <= s->num_open && k <= NCHEST; k++) /* BOX list: opened, in open order */
        for (u32 i = 0; i < NCHEST; i++)
            if (s->prize[i].order == k &&
                pack_entry(c->box_layout, &s->prize[i], i, b->boxes, sizeof b->boxes, &bp) == 0)
                x->nboxes++;
    x->lots = b->lots;
    x->lots_bytes = lp;
    x->boxes = b->boxes;
    x->boxes_bytes = bp;
}

/* Login-session guard. When the Treasures window is opened for the first time
 * after a login, the 1.7.3 client sends type 3 (the same as the Seek button) to
 * get its board back. Charging keys for that is wrong, so the first seek of each
 * login session (told apart by the link session id gs keeps for the player)
 * only resends the saved board. Stored in <state_dir>/<roleid>.sid.
 * Returns 1 = this is a new session (file updated), 0 = same session, -1 = unknown. */
static int session_is_new(const cfg_t *c, const ctx_t *x)
{
    if (c->off_cssid < 0 || c->off_csidx < 0 || !x->cssid)
        return -1;
    char path[600];
    snprintf(path, sizeof path, "%s/%u.sid", c->state_dir, x->roleid);
    s32 old[2] = { 0, 0 }, now[2] = { x->csidx, x->cssid };
    int fd = open(path, O_RDWR | O_CREAT | O_CLOEXEC, 0600);
    if (fd < 0)
        return -1;
    ssize_t r = pread(fd, old, sizeof old, 0);
    int fresh = !(r == (ssize_t)sizeof old && old[0] == now[0] && old[1] == now[1]);
    if (fresh && pwrite(fd, now, sizeof now, 0) != (ssize_t)sizeof now)
        fresh = -1;
    close(fd);
    return fresh;
}

static void do_refresh(const cfg_t *c, ctx_t *x, const tstate_t *s)
{
    boardbuf_t b;
    fill_board(c, x, s, s->manager, &b);
    send_info(c, x);
    if (c->call[C_INV].addr)
        call_fn(c, C_INV, x);
    run_event(c, EV_REFRESH, x);
}

static int safelock_blocks(const cfg_t *c, ctx_t *x)
{
    if (!c->call[C_SAFELOCK].addr)
        return 0;
    if (call_fn(c, C_SAFELOCK, x) == 1) {
        tlog("refused: role %u has the safety lock on (or the check failed)", x->roleid);
        send_msg(c, x, c->err_safelock);
        return 1;
    }
    return 0;
}

static int has_keys(const cfg_t *c, ctx_t *x, u32 n)
{
    x->id = c->key_item;
    x->count = n;
    int r = call_fn(c, C_COUNT, x);
    if (r < 0)
        tlog("cannot check keys: call.count is not configured or not usable (rc %d)", r);
    return r == 0;
}

static void do_seek(const cfg_t *c, ctx_t *x, tstate_t *s, int fd, int aurum)
{
    if (c->nloot <= 0) {
        tlog("seek refused: no loot lines in the config");
        do_refresh(c, x, s);
        return;
    }
    if (safelock_blocks(c, x))
        return;
    if (aurum && s->score < c->aurum_cost) {
        tlog("seek refused: role %u has %u Aurum, needs %u", x->roleid, s->score, c->aurum_cost);
        send_msg(c, x, c->err_noaurum);
        do_refresh(c, x, s);
        return;
    }
    if (!has_keys(c, x, c->keys_per_seek)) {
        tlog("seek refused: role %u lacks %u x item %u", x->roleid, c->keys_per_seek, c->key_item);
        send_msg(c, x, c->err_nokeys);
        do_refresh(c, x, s);
        return;
    }
    /* build the new board, save it, and only then take the keys */
    tstate_t n = *s;
    if (aurum)
        n.score -= c->aurum_cost;
    else
        n.score += 1;
    u8 used[MAXLOOT];
    memset(used, 0, sizeof used);
    int uniq = c->loot_unique && c->nloot >= NCHEST;
    u32 boxes[NCHEST];
    for (u32 i = 0; i < NCHEST; i++) {
        int k = pick_loot(c, uniq ? used : NULL);
        if (k < 0) { /* fewer different items than chests: allow repeats from here on */
            uniq = 0;
            k = pick_loot(c, NULL);
        }
        if (k < 0)
            k = 0;
        if (uniq) /* the same item may sit on several rows: block them all */
            for (int j = 0; j < c->nloot; j++)
                if (c->loot[j].id == c->loot[k].id)
                    used[j] = 1;
        n.prize[i].id = c->loot[k].id;
        n.prize[i].count = c->loot[k].count;
        n.prize[i].order = 0;
        boxes[i] = i;
    }
    for (u32 i = NCHEST - 1; i > 0; i--) { /* Fisher-Yates shuffle of chest positions */
        u32 j = rnd() % (i + 1), t = boxes[i];
        boxes[i] = boxes[j];
        boxes[j] = t;
    }
    for (u32 i = 0; i < NCHEST; i++)
        n.prize[i].box = boxes[i];
    n.active = 1;
    n.num_open = 0;
    n.pay_broken = 0;
    n.free_c = aurum ? c->aurum_free : 1;
    n.manager = 1;
    n.seeks++;
    if (state_commit(fd, &n)) {
        tlog("seek stopped: the new board could not be saved; nothing taken");
        do_refresh(c, x, s);
        return;
    }
    x->id = c->key_item;
    x->count = c->keys_per_seek;
    int r = call_fn(c, C_REMOVE, x);
    if (r) {
        tlog("seek stopped: taking the keys failed (call.remove rc %d)", r);
        if (state_commit(fd, s))
            tlog("WARNING: role %u: could not put the old board back", x->roleid);
        do_refresh(c, x, s);
        return;
    }
    *s = n;
    tlog("seek: role %u paid %u keys%s; new board, free opens %u, Aurum now %u", x->roleid,
         c->keys_per_seek, aurum ? " + Aurum" : "", s->free_c, s->score);
    boardbuf_t b;
    if (c->seek_clear) { /* an empty board first, so the client drops the old opened chests */
        tstate_t e;
        memset(&e, 0, sizeof e);
        e.score = s->score;
        fill_board(c, x, &e, 0, &b);
        send_info(c, x);
    }
    fill_board(c, x, s, 1, &b);
    send_info(c, x);
    run_event(c, EV_SEEK, x);
}

static void do_open(const cfg_t *c, ctx_t *x, tstate_t *s, int fd)
{
    if (!s->active) {
        tlog("open ignored: role %u has no board out", x->roleid);
        do_refresh(c, x, s);
        return;
    }
    s32 slot = x->param - (s32)c->chest_base;
    int i = -1;
    if (slot >= 0 && slot < NCHEST)
        for (int k = 0; k < NCHEST; k++)
            if (s->prize[k].box == (u32)slot)
                i = k;
    if (i < 0 || s->prize[i].order) {
        tlog("open ignored: role %u chest %d is %s", x->roleid, x->param,
             i < 0 ? "out of range" : "already open");
        do_refresh(c, x, s);
        return;
    }
    if (safelock_blocks(c, x))
        return;
    u32 cost = s->free_c ? 0 : c->cost[s->num_open < NCHEST ? s->num_open : NCHEST - 1];
    if (cost && s->pay_broken) {
        tlog("open refused: paid opens are off on this board because taking keys failed "
             "earlier; check call.remove");
        send_msg(c, x, c->err_nokeys);
        do_refresh(c, x, s);
        return;
    }
    if (cost && !has_keys(c, x, cost)) {
        tlog("open refused: role %u lacks %u keys", x->roleid, cost);
        send_msg(c, x, c->err_nokeys);
        do_refresh(c, x, s);
        return;
    }
    /* save the opened chest first, then give the prize (if the bag is full,
     * nothing is taken and the saved state is put back), then take the keys */
    tstate_t n = *s;
    if (n.free_c)
        n.free_c--;
    n.prize[i].order = ++n.num_open;
    n.opens++;
    n.manager = 2;
    if (n.num_open >= NCHEST)
        n.active = 0;
    if (state_commit(fd, &n)) {
        tlog("open stopped: could not save; nothing given or taken");
        do_refresh(c, x, s);
        return;
    }
    int via = !strcmp(c->deliver, "lotadd") ? C_LOTADD : C_OBTAIN;
    x->id = n.prize[i].id;
    x->count = n.prize[i].count;
    x->slot = (u32)slot;
    x->lot = (u32)i;
    int r = call_fn(c, via, x);
    if (r) {
        tlog("open failed: could not give item %u x%u to role %u (call.%s rc %d)", x->id,
             x->count, x->roleid, CALLNAME[via], r);
        if (state_commit(fd, s))
            tlog("WARNING: role %u: could not put the board back", x->roleid);
        send_msg(c, x, c->err_bagfull);
        do_refresh(c, x, s);
        return;
    }
    if (cost) {
        x->id = c->key_item;
        x->count = cost;
        if ((r = call_fn(c, C_REMOVE, x))) {
            tlog("WARNING: role %u got the prize but taking %u keys failed (rc %d); paid opens "
                 "are now off on this board", x->roleid, cost, r);
            n.pay_broken = 1;
            state_commit(fd, &n);
        }
    }
    *s = n;
    tlog("open: role %u chest %d -> prize %d item %u x%u (cost %u keys, %u/10 open)", x->roleid,
         slot, i, s->prize[i].id, s->prize[i].count, cost, s->num_open);
    boardbuf_t b;
    fill_board(c, x, s, 2, &b);
    x->id = s->prize[i].id; /* the prize stays in id/count/slot/lot for on.open calls */
    x->count = s->prize[i].count;
    send_info(c, x);
    if (via == C_LOTADD && c->call[C_INV].addr)
        call_fn(c, C_INV, x);
    run_event(c, EV_OPEN, x);
}

static void do_probe(const cfg_t *c, ctx_t *x)
{
    tstate_t s;
    memset(&s, 0, sizeof s);
    u32 fill = c->probe_fill > NCHEST ? NCHEST : c->probe_fill;
    for (u32 i = 0; i < NCHEST; i++) {
        s.prize[i].id = c->nloot ? c->loot[i % (u32)c->nloot].id : c->key_item;
        s.prize[i].count = 1;
        s.prize[i].box = i;
        s.prize[i].order = i < fill ? i + 1 : 0;
    }
    s.active = fill < NCHEST;
    s.num_open = fill;
    s.score = c->probe_score;
    s.free_c = c->probe_free;
    tlog("probe for role %u (client sent type %d param %d)", x->roleid, x->type, x->param);
    boardbuf_t b;
    fill_board(c, x, &s, c->probe_manager, &b);
    if (!strcmp(c->probe_send, "info") || !strcmp(c->probe_send, "both"))
        send_info(c, x);
    if (!strcmp(c->probe_send, "inv") || !strcmp(c->probe_send, "both"))
        tlog("probe inv: rc %d", call_fn(c, C_INV, x));
}

/* ------------------------------------------------------------------ */
/* dispatch (shared by both hook points)                                */
/* ------------------------------------------------------------------ */
static int role_allowed(const cfg_t *c, u32 roleid)
{
    if (c->allow_all)
        return 1;
    for (int i = 0; i < c->nallow; i++)
        if (c->allow[i] == roleid)
            return 1;
    return 0; /* empty allow_roles = nobody */
}

static int classify(const cfg_t *c, int type, int param)
{
    if (c->type_seek_aurum >= 0 && type == c->type_seek_aurum)
        return A_SEEK_AURUM;
    if (type == c->type_seek)
        return (c->aurum_param >= 0 && param == c->aurum_param) ? A_SEEK_AURUM : A_SEEK;
    if (type == c->type_open)
        return A_OPEN;
    if (type == c->type_refresh)
        return A_REFRESH;
    return A_NONE;
}

static void read_ptr(uptr base, long off, uptr *out)
{
    if (!base || off < 0 || safe_read(base + (uptr)off, out, sizeof *out))
        *out = 0;
}

static void read_s32(uptr base, long off, s32 *out)
{
    if (!base || off < 0 || safe_read(base + (uptr)off, out, sizeof *out))
        *out = 0;
}

/* 1 = handled here, 0 = hand it to gs's own code */
static int treasure_dispatch(const cfg_t *c, uptr imp, int type, int param)
{
    ctx_t x;
    memset(&x, 0, sizeof x);
    x.imp = imp;
    x.type = type;
    x.param = param;
    read_ptr(x.imp, c->off_parent, &x.parent);
    read_ptr(x.imp, c->off_runner, &x.runner);
    s32 rid = 0;
    read_s32(x.parent, c->off_roleid, &rid);
    x.roleid = rid > 0 ? (u32)rid : 0;
    read_s32(x.parent, c->off_csidx, &x.csidx);
    read_s32(x.parent, c->off_cssid, &x.cssid);
    int act = classify(c, type, param);
    tlog("Lottery_Notice1 role=%u type=%d param=%d -> %s (mode %s)", x.roleid, type, param,
         ACTNAME[act], MODENAME[c->mode]);
    if (c->mode == MODE_LOG || act == A_NONE)
        return 0;
    if (!x.roleid) {
        tlog("no role id: set off.parent and off.roleid from the recon output");
        return 0;
    }
    if (!role_allowed(c, x.roleid))
        return 0;
    if (c->mode == MODE_PROBE) {
        do_probe(c, &x);
        return 1;
    }
    int fd = state_open(c, x.roleid);
    if (fd < 0) {
        tlog(fd == -2 ? "state file of role %u is busy; command dropped"
                      : "cannot open the state file of role %u; command dropped", x.roleid);
        return 1;
    }
    tstate_t s;
    state_read(fd, &s, x.roleid);
    int newsess = session_is_new(c, &x);
    if ((act == A_SEEK || act == A_SEEK_AURUM) && newsess == 1) {
        tlog("seek from role %u is the first of this login (window reopened): resending the "
             "saved board, no keys taken", x.roleid);
        do_refresh(c, &x, &s);
    } else if (act == A_SEEK || act == A_SEEK_AURUM)
        do_seek(c, &x, &s, fd, act == A_SEEK_AURUM);
    else if (act == A_OPEN)
        do_open(c, &x, &s, fd);
    else
        do_refresh(c, &x, &s);
    state_close(fd);
    return 1;
}

/* ------------------------------------------------------------------ */
/* the two hook points                                                  */
/* ------------------------------------------------------------------ */
typedef int (*notice_fn)(void *self, int type, int param);
typedef int (*cmd_fn)(void *self, int cmd, const void *buf, size_t size);
static notice_fn g_orig_notice;
static cmd_fn g_orig_cmd;

/* stands in for gplayer_imp::Lottery_Notice1(int type, int param) */
__attribute__((visibility("default"), used)) ENTRY
int hook_notice1(void *self, int type, int param)
{
    int saved = errno;
    if (!g_in_hook) {
        maybe_reload(NULL);
        const cfg_t *c = cfg_now();
        if (c) {
            g_in_hook = 1;
            int handled = treasure_dispatch(c, (uptr)self, type, param);
            g_in_hook = 0;
            if (handled) {
                errno = saved;
                return (int)c->hook_ret;
            }
        }
    }
    errno = saved;
    return g_orig_notice ? g_orig_notice(self, type, param) : 0;
}

/* stands in for gplayer_controller::CommandHandler(int cmd, const void *buf, size_t size):
 * every client command passes here, so anything but the Treasures command goes
 * straight on to gs */
__attribute__((visibility("default"), used)) ENTRY
int hook_cmd(void *self, int cmd, const void *buf, size_t size)
{
    const cfg_t *c = cfg_now();
    if (!c || c->cmd_id < 0 || cmd != c->cmd_id || g_in_hook || !g_orig_cmd)
        return g_orig_cmd ? g_orig_cmd(self, cmd, buf, size) : 0;
    int saved = errno;
    maybe_reload(NULL);
    c = cfg_now();
    s32 type = 0, param = 0;
    uptr imp = 0;
    long need = (c->cmd_type_off > c->cmd_param_off ? c->cmd_type_off : c->cmd_param_off) + 4;
    if (cmd == c->cmd_id && c->cmd_type_off >= 0 && c->cmd_param_off >= 0 && (long)size >= need &&
        !safe_read((uptr)buf + (uptr)c->cmd_type_off, &type, 4) &&
        !safe_read((uptr)buf + (uptr)c->cmd_param_off, &param, 4)) {
        read_ptr((uptr)self, c->off_ctrl_imp, &imp);
        if (imp) {
            g_in_hook = 1;
            int handled = treasure_dispatch(c, imp, type, param);
            g_in_hook = 0;
            if (handled) {
                errno = saved;
                return (int)c->cmd_ret;
            }
        } else
            tlog("command %d: no player object (set off.ctrl_imp from the recon output)", cmd);
    } else if (cmd == c->cmd_id)
        tlog("command %d: could not read type/param (size %lu; check cmd.type_off/param_off)",
             cmd, (unsigned long)size);
    errno = saved;
    return g_orig_cmd(self, cmd, buf, size);
}

/* ------------------------------------------------------------------ */
/* install                                                              */
/* ------------------------------------------------------------------ */
static int name_matches_any(const char *name, const char *list)
{
    char tmp[256], *save = NULL, *t;
    copyz(tmp, sizeof tmp, list);
    for (t = strtok_r(tmp, ",", &save); t; t = strtok_r(NULL, ",", &save)) {
        t = trim(t);
        if (!strcmp(t, "*") || (*t && strstr(name, t)))
            return 1;
    }
    return 0;
}

static u8 *read_range(uptr a, size_t n)
{
    u8 *b = malloc(n ? n : 1);
    if (b && safe_read(a, b, n)) {
        free(b);
        b = NULL;
    }
    return b;
}

/* the function to hook: the configured name, else the one global function whose
 * name starts with 'prefix'. Refuses if that is not exactly one function. */
static uptr find_target(const symtab_t *t, const char *configured, const char *prefix,
                        const char *base_name, size_t *size, const char **chosen)
{
    uptr tgt = 0;
    if (configured[0]) {
        if (sym_find_func(t, configured, &tgt, size))
            *chosen = configured;
        else
            tlog("ERROR: %s is not a usable function in gs", configured);
        return tgt;
    }
    int n = 0;
    for (size_t i = 0; i < t->nsyms; i++) {
        const ElfW(Sym) *s = &t->syms[i];
        const char *nm = symname(t, s);
        if (strncmp(nm, prefix, strlen(prefix)))
            continue;
        if (!sym_callable(t, s)) {
            tlog("note: %s is a local or compiler-made copy; calls to it are NOT hooked", nm);
            continue;
        }
        n++;
        tlog("candidate %s", nm);
        tgt = (uptr)s->st_value + g_base;
        *size = s->st_size;
        *chosen = nm;
    }
    if (n != 1) {
        tlog("ERROR: found %d candidates for %s; set the exact name in the config", n, base_name);
        return 0;
    }
    return tgt;
}

/* Recorder for the client command that carries Treasures (197). gs itself
 * refuses action types other than 0-3 with "invalid action" BEFORE it calls
 * Lottery_Notice1, so those never reach hook_notice1. This sits in the
 * CommandHandler vtable slot, writes the raw packet to hook.log and always
 * hands the command on to gs unchanged. */
static cmd_fn g_orig_cmdlog;
__attribute__((visibility("default"), used)) ENTRY
int hook_cmdlog(void *self, int cmd, const void *buf, size_t size)
{
    const cfg_t *c = cfg_now();
    if (c && (c->cmd_log == -2 || (c->cmd_log >= 0 && cmd == c->cmd_log)) && !g_in_hook) {
        int saved = errno;
        s32 type = -1;
        if (size >= 6)
            safe_read((uptr)buf + 2, &type, 4);
        /* "any": every command id, at most 3 lines per id per 10 s (movement is chatty) */
        static time_t win[1024];
        static int cnt[1024];
        int show;
        if (c->cmd_log == -2 && cmd != 197) {
            unsigned k = (unsigned)cmd & 1023u;
            time_t now = time(NULL);
            if (now - win[k] >= 10) {
                win[k] = now;
                cnt[k] = 0;
            }
            show = ++cnt[k] <= 3;
        } else
            show = c->cmd_log_all || type < 0 || type > 3;
        if (show) {
            u8 tmp[256];
            size_t n = size < sizeof tmp ? size : sizeof tmp;
            char hex[3 * sizeof tmp + 1];
            hex[0] = 0;
            if (!safe_read((uptr)buf, tmp, n))
                for (size_t i = 0; i < n; i++)
                    snprintf(hex + 3 * i, 4, "%02x ", tmp[i]);
            uptr imp = 0, parent = 0;
            s32 rid = 0;
            read_ptr((uptr)self, c->off_ctrl_imp, &imp);
            read_ptr(imp, c->off_parent, &parent);
            read_s32(parent, c->off_roleid, &rid);
            tlog("client command %d from role %d: type %d, %lu bytes%s: %s", cmd, rid, type,
                 (unsigned long)size, size > n ? " (first 256)" : "", hex);
        }
        errno = saved;
    }
    return g_orig_cmdlog ? g_orig_cmdlog(self, cmd, buf, size) : 0;
}

static void install_cmdlog(const cfg_t *c, const symtab_t *t)
{
    const char *chosen = "";
    size_t tsz = 0;
    uptr tgt = find_target(t, c->cmd_sym, "_ZN18gplayer_controller14CommandHandlerE",
                           "gplayer_controller::CommandHandler", &tsz, &chosen);
    if (!tgt) {
        tlog("command recorder NOT installed");
        return;
    }
    g_orig_cmdlog = (cmd_fn)tgt;
    uptr hook = (uptr)&hook_cmdlog;
    int nv = 0;
    for (size_t i = 0; i < t->nsyms; i++) {
        const ElfW(Sym) *s = &t->syms[i];
        if (!s->st_size || !sym_loaded(t, s))
            continue;
        const char *nm = symname(t, s);
        if (ST_TYPE(s->st_info) != STT_OBJECT || strncmp(nm, "_ZTV", 4))
            continue;
        uptr a0 = (uptr)s->st_value + g_base;
        size_t sz = s->st_size;
        u8 *b = read_range(a0, sz);
        if (!b)
            continue;
        for (size_t o = (sizeof(uptr) - (a0 % sizeof(uptr))) % sizeof(uptr);
             o + sizeof(uptr) <= sz; o += sizeof(uptr)) {
            uptr v;
            memcpy(&v, b + o, sizeof v);
            if (v != tgt)
                continue;
            if (c->patch && poke(a0 + o, &hook, sizeof hook) == 0)
                nv++;
        }
        free(b);
    }
    tlog("command recorder for command %s: %d vtable slot(s) patched",
         c->cmd_log == -2 ? "any" : "197 or as set", nv);
}

static void install_hooks(const cfg_t *c, const symtab_t *t)
{
    int cmdmode = !strcmp(c->hook_mode, "command");
    const char *chosen = "";
    size_t tsz = 0;
    uptr tgt = cmdmode
        ? find_target(t, c->cmd_sym, "_ZN18gplayer_controller14CommandHandlerE",
                      "gplayer_controller::CommandHandler", &tsz, &chosen)
        : find_target(t, c->notice1_sym, "_ZN11gplayer_imp15Lottery_Notice1E",
                      "gplayer_imp::Lottery_Notice1", &tsz, &chosen);
    if (!tgt) {
        tlog("hook NOT installed");
        return;
    }
    const char *scan = c->scan_funcs[0] ? c->scan_funcs : cmdmode ? "*" : "CommandHandler";
    tlog("hook mode %s: target %s at %#lx (size %lu); scanning functions matching '%s'%s",
         cmdmode ? "command" : "notice1", chosen, (unsigned long)tgt, (unsigned long)tsz, scan,
         c->patch ? "" : " - DRY RUN, nothing will be patched (hook.patch = no)");
    if (cmdmode)
        g_orig_cmd = (cmd_fn)tgt;
    else
        g_orig_notice = (notice_fn)tgt;
    uptr hook = cmdmode ? (uptr)&hook_cmd : (uptr)&hook_notice1;
    int nv = 0, nc = 0;

    for (size_t i = 0; i < t->nsyms; i++) {
        const ElfW(Sym) *s = &t->syms[i];
        if (!s->st_size || !sym_loaded(t, s))
            continue;
        const char *nm = symname(t, s);
        uptr a0 = (uptr)s->st_value + g_base;
        size_t sz = s->st_size;
        int is_vt = ST_TYPE(s->st_info) == STT_OBJECT && !strncmp(nm, "_ZTV", 4);
        int is_fn = ST_TYPE(s->st_info) == STT_FUNC && a0 != tgt && name_matches_any(nm, scan);
        if (!is_vt && !is_fn)
            continue;
        u8 *b = read_range(a0, sz);
        if (!b)
            continue;
        if (is_vt) /* 1) vtable slots that hold the target (virtual calls) */
            for (size_t o = (sizeof(uptr) - (a0 % sizeof(uptr))) % sizeof(uptr);
                 o + sizeof(uptr) <= sz; o += sizeof(uptr)) {
                uptr v;
                memcpy(&v, b + o, sizeof v);
                if (v != tgt)
                    continue;
                nv++;
                if (!c->patch)
                    tlog("would patch vtable slot %#lx in %s", (unsigned long)(a0 + o), nm);
                else if (poke(a0 + o, &hook, sizeof hook) == 0)
                    tlog("patched vtable slot %#lx in %s", (unsigned long)(a0 + o), nm);
                else
                    tlog("could not patch vtable slot %#lx: %s", (unsigned long)(a0 + o),
                         strerror(errno));
            }
        if (is_fn) /* 2) direct calls (E8 rel32) and tail jumps (E9 rel32) */
            for (size_t o = 0; o + 5 <= sz; o++) {
                if (b[o] != 0xE8 && b[o] != 0xE9)
                    continue;
                s32 rel;
                memcpy(&rel, b + o + 1, 4);
                uptr site = a0 + o;
                if (site + 5 + (uptr)(intptr_t)rel != tgt)
                    continue;
                nc++;
                const char *kind = b[o] == 0xE8 ? "call" : "jump";
                if (!c->patch) {
                    tlog("would patch direct %s at %#lx in %s", kind, (unsigned long)site, nm);
                    continue;
                }
                uptr dest = hook;
#if defined(__x86_64__)
                if (!in_reach(site + 5, dest) && !(dest = tramp_near(site, hook))) {
                    tlog("could not place a jump stub near %#lx", (unsigned long)site);
                    continue;
                }
#endif
                s32 nrel = (s32)(dest - (site + 5));
                if (poke(site + 1, &nrel, 4) == 0)
                    tlog("patched direct %s at %#lx in %s", kind, (unsigned long)site, nm);
                else
                    tlog("could not patch %s at %#lx: %s", kind, (unsigned long)site,
                         strerror(errno));
            }
        free(b);
    }
    if (nv + nc == 0)
        tlog("WARNING: no calls to the target found; the hook is inactive");
    else
        tlog("%s: %d vtable slot(s), %d direct call(s)/jump(s)",
             c->patch ? "hook installed" : "dry run", nv, nc);
}

ENTRY __attribute__((constructor)) static void treasure_hook_init(void)
{
    char exe[512];
    ssize_t n = readlink("/proc/self/exe", exe, sizeof exe - 1);
    if (n <= 0)
        return;
    exe[n] = 0;
    const char *base = strrchr(exe, '/');
    base = base ? base + 1 : exe;
    if (strcmp(base, "gs") && !getenv("TREASURE_HOOK_ANY"))
        return; /* only ever act inside the game server */
    if (getenv("TREASURE_HOOK_DISABLE"))
        return;
    const char *e;
    if ((e = getenv("TREASURE_HOOK_CONF")))
        copyz(g_confpath, sizeof g_confpath, e);
    if ((e = getenv("TREASURE_HOOK_LOG")))
        copyz(g_logpath, sizeof g_logpath, e);
    pthread_atfork(atfork_prepare, atfork_release, atfork_release);
    dl_iterate_phdr(phdr_cb, &g_base);
    tlog("treasure_hook loading in %s (image base %#lx, %d-bit)", exe, (unsigned long)g_base,
         (int)(8 * sizeof(void *)));
    symtab_t t;
    int have = symtab_load(&t) == 0; /* read once, used for the config and the install */
    if (!have)
        tlog("ERROR: cannot read the gs symbol table");
    maybe_reload(have ? &t : NULL);
    if (!g_cfg)
        tlog("ERROR: cannot read %s; hook NOT installed", g_confpath);
    else if (have) {
        install_hooks(g_cfg, &t);
        if (g_cfg->cmd_log != -1 && strcmp(g_cfg->hook_mode, "command"))
            install_cmdlog(g_cfg, &t);
    }
    if (have)
        symtab_free(&t);
}
