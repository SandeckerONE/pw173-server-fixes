// fake_gs.cpp - a tiny stand-in for the 1.7.3 game server, ONLY for testing
// treasure_hook on Claude's side. It copies the shape of the real thing:
//   gplayer_controller::CommandHandler -> gplayer_imp::Lottery_Notice1(type, param)
// with the same "only type 2 works" behaviour, plus item and packet functions
// for the hook to call by symbol name. The real gs signatures are NOT known yet;
// these are plausible placeholders.
//
// It reads commands on stdin, one per line, and answers with lines on stdout:
//   offsets                       -> OFFSETS parent=.. runner=.. roleid=.. csidx=.. cssid=..
//   give <role> <item> <count>    put items in the bag
//   take <role> <item> <count>    remove items from the bag
//   bag <role> / lotinv <role>    print the bag / Treasure Warehouse
//   lock <role> 0|1               safety lock off/on
//   full <role> 0|1               bag full (ObtainItem fails)
//   cmd <role> <c2s> <type> <param>   send a client command (197 = virtual call path,
//                                     198 = direct call path)
// Every command ends with a line "DONE".
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>

#define NOINL __attribute__((noinline, used))

struct XID { int type; int id; };

class gobject {
public:
    int spinlock;
    int pad[5];
    XID ID;
    int cs_index;
    int cs_sid;
};
class gplayer : public gobject { public: int extra[3]; };

struct item_data { int id; unsigned count; int magic; };

class gplayer_imp;

class dispatcher {
public:
    virtual ~dispatcher() {}
    virtual void error_message(int msg);
};

class gplayer_dispatcher : public dispatcher {
public:
    gplayer_imp *_imp;
    void error_message(int msg) override;
    void send_lot_info3(unsigned char manager, unsigned score, unsigned free_count,
                        unsigned lot_count, unsigned box_count, const void *lots, const void *boxes);
    void send_lot_inv();
};

class gobject_imp {
public:
    virtual ~gobject_imp() {}
    void *_plane;
    gobject *_parent;
    dispatcher *_runner;
};

class gplayer_imp : public gobject_imp {
public:
    std::map<int, unsigned> bag, lot_inv;
    bool safelock = false, bagfull = false;
    virtual int Lottery_Notice1(int type, int param);
    virtual int Lottery_Notice2(int type, int param);
    bool CheckItemExist(int id, unsigned count);
    bool RemoveItems(int id, unsigned count);
    bool ObtainItem(int id, unsigned count);
    bool ObtainItemData(item_data *d);
    bool AddLotItem(int id, unsigned count);
    bool TestSafeLock();
    gplayer *who() { return (gplayer *)_parent; }
};

class controller {
public:
    virtual ~controller() {}
    virtual int CommandHandler(int cmd, const void *buf, size_t size) = 0;
};

class gplayer_controller : public controller {
public:
    gplayer_imp *_imp;
    int CommandHandler(int cmd, const void *buf, size_t size) override;
};

namespace GMSV {
bool SendClientData(int lid, int uid, int sid, const void *buf, unsigned size);
}
item_data *MakeItem(int id, unsigned count);

// ---------------------------------------------------------------------------
NOINL void dispatcher::error_message(int msg) { printf("ERRMSG(base) %d\n", msg); }
NOINL void gplayer_dispatcher::error_message(int msg) { printf("ERRMSG %d\n", msg); }

static unsigned rd32(const unsigned char *p) { return p[0] | p[1] << 8 | p[2] << 16 | (unsigned)p[3] << 24; }

NOINL void gplayer_dispatcher::send_lot_info3(unsigned char manager, unsigned score,
                                               unsigned free_count, unsigned lot_count,
                                               unsigned box_count, const void *lots,
                                               const void *boxes)
{
    // default layouts: LOT {u32 id, u32 count, u8 lot} = 9 bytes, BOX {u32 id, u32 box, u32 count, u8 lot} = 13
    printf("INFO3 manager=%u score=%u free=%u lots=%u boxes=%u", manager, score, free_count,
           lot_count, box_count);
    const unsigned char *l = (const unsigned char *)lots, *b = (const unsigned char *)boxes;
    printf(" L[");
    for (unsigned i = 0; i < lot_count; i++, l += 9)
        printf("%s%u:%ux%u", i ? " " : "", (unsigned)l[8], rd32(l), rd32(l + 4));
    printf("] B[");
    for (unsigned i = 0; i < box_count; i++, b += 13)
        printf("%s%u@%u:%ux%u", i ? " " : "", (unsigned)b[12], rd32(b + 4), rd32(b), rd32(b + 8));
    printf("]\n");
}

NOINL void gplayer_dispatcher::send_lot_inv()
{
    printf("LOTINV");
    for (auto &kv : _imp->lot_inv)
        printf(" %d:%u", kv.first, kv.second);
    printf("\n");
}

NOINL bool GMSV::SendClientData(int lid, int uid, int sid, const void *buf, unsigned size)
{
    printf("RAW lid=%d uid=%d sid=%d size=%u hex=", lid, uid, sid, size);
    for (unsigned i = 0; i < size; i++)
        printf("%02x", ((const unsigned char *)buf)[i]);
    printf("\n");
    return true;
}

NOINL item_data *MakeItem(int id, unsigned count)
{
    static item_data d;
    d.id = id;
    d.count = count;
    d.magic = 0x17E4;
    return &d;
}

// a stand-in for a GCC-made local copy ("...Eii.part.0"); calling it is a test failure
static int fake_clone(void *, int, int) __asm__("_ZN11gplayer_imp15Lottery_Notice1Eii.part.0");
__attribute__((used, noinline)) static int fake_clone(void *, int, int)
{
    printf("FAKE CLONE CALLED\n");
    abort();
}

// what the real 1.7.3 gs does: only type 2 (withdraw) works, the rest only print
NOINL int gplayer_imp::Lottery_Notice1(int type, int param)
{
    printf("Lottery_Notice1 roleid=%d %d %d\n", who()->ID.id, type, param);
    if (type == 2) {
        int i = 0;
        for (auto it = lot_inv.begin(); it != lot_inv.end(); ++it, ++i)
            if (i == param) {
                bag[it->first] += it->second;
                printf("ORIG withdraw %d x%u\n", it->first, it->second);
                lot_inv.erase(it);
                break;
            }
        ((gplayer_dispatcher *)_runner)->send_lot_inv();
    }
    return 0;
}

NOINL int gplayer_imp::Lottery_Notice2(int type, int param)
{
    printf("Lottery_Notice2 %d %d\n", type, param);
    return 0;
}

NOINL bool gplayer_imp::CheckItemExist(int id, unsigned count)
{
    auto it = bag.find(id);
    return it != bag.end() && it->second >= count;
}

NOINL bool gplayer_imp::RemoveItems(int id, unsigned count)
{
    if (!CheckItemExist(id, count))
        return false;
    if ((bag[id] -= count) == 0)
        bag.erase(id);
    return true;
}

NOINL bool gplayer_imp::ObtainItem(int id, unsigned count)
{
    if (bagfull)
        return false;
    bag[id] += count;
    return true;
}

NOINL bool gplayer_imp::ObtainItemData(item_data *d)
{
    if (bagfull || !d || d->magic != 0x17E4)
        return false;
    bag[d->id] += d->count;
    return true;
}

NOINL bool gplayer_imp::AddLotItem(int id, unsigned count)
{
    lot_inv[id] += count;
    return true;
}

NOINL bool gplayer_imp::TestSafeLock() { return safelock; }

#pragma pack(push, 1)
struct lottery_manager_cmd { unsigned short cmd; unsigned manager; int param; };
#pragma pack(pop)

NOINL int gplayer_controller::CommandHandler(int cmd, const void *buf, size_t size)
{
    if (size < sizeof(lottery_manager_cmd))
        return -1;
    const lottery_manager_cmd *c = (const lottery_manager_cmd *)buf;
    switch (cmd) {
    case 197: // virtual call, as most gs code does
        return _imp->Lottery_Notice1((int)c->manager, c->param);
    case 198: // direct (non-virtual) call
        return _imp->gplayer_imp::Lottery_Notice1((int)c->manager, c->param);
    case 236:
        return _imp->Lottery_Notice2((int)c->manager, c->param);
    }
    return -1;
}

// ---------------------------------------------------------------------------
struct role {
    gplayer pl;
    gplayer_imp imp;
    gplayer_dispatcher disp;
    gplayer_controller ctl;
};

static std::map<int, role *> roles;

static role *get_role(int id)
{
    role *&r = roles[id];
    if (!r) {
        r = new role();
        memset(&r->pl, 0, sizeof r->pl);
        r->pl.ID.type = 1;
        r->pl.ID.id = id;
        r->pl.cs_index = 3;
        r->pl.cs_sid = 7000 + id % 1000;
        r->imp._parent = &r->pl;
        r->imp._runner = &r->disp;
        r->imp._plane = nullptr;
        r->disp._imp = &r->imp;
        r->ctl._imp = &r->imp;
    }
    return r;
}

int main()
{
    setvbuf(stdout, nullptr, _IOLBF, 0);
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        char what[32] = "";
        int a = 0, b = 0, c = 0, d = 0;
        int n = sscanf(line, "%31s %d %d %d %d", what, &a, &b, &c, &d);
        if (n < 1)
            continue;
        std::string w = what;
        if (w == "quit")
            break;
        if (w == "offsets") {
            printf("OFFSETS parent=%zu runner=%zu roleid=%zu csidx=%zu cssid=%zu ctrl_imp=%zu\n",
                   offsetof(gplayer_imp, _parent), offsetof(gplayer_imp, _runner),
                   offsetof(gobject, ID) + offsetof(XID, id), offsetof(gobject, cs_index),
                   offsetof(gobject, cs_sid), offsetof(gplayer_controller, _imp));
        } else if (w == "give") {
            get_role(a)->imp.bag[b] += (unsigned)c;
        } else if (w == "take") {
            get_role(a)->imp.RemoveItems(b, (unsigned)c);
        } else if (w == "bag" || w == "lotinv") {
            role *r = get_role(a);
            auto &m = w == "bag" ? r->imp.bag : r->imp.lot_inv;
            printf("%s %d", w == "bag" ? "BAG" : "LOTINVLIST", a);
            for (auto &kv : m)
                printf(" %d:%u", kv.first, kv.second);
            printf("\n");
        } else if (w == "relog") {
            get_role(a)->pl.cs_sid += 1; /* a new login gets a new link session id */
        } else if (w == "lock") {
            get_role(a)->imp.safelock = b != 0;
        } else if (w == "full") {
            get_role(a)->imp.bagfull = b != 0;
        } else if (w == "cmd") {
            lottery_manager_cmd cm = { (unsigned short)b, (unsigned)c, d };
            controller *ctl = &get_role(a)->ctl; // virtual call, like the real network code
            int r = ctl->CommandHandler(b, &cm, sizeof cm);
            printf("RET %d\n", r);
        } else {
            printf("? %s\n", what);
        }
        printf("DONE\n");
    }
    return 0;
}
