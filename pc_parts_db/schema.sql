-- Schema for the PC parts database (SQLite).
-- generate_data.py runs this file, or you can run: sqlite3 pcparts.db < schema.sql
-- Note: ids are "integer" instead of "int" so SQLite auto-numbers them.
pragma foreign_keys = on;

-- main tables (from the ER diagram)
create table categories (
    category_id    integer,
    name           varchar(50)   not null unique,
    description    varchar(500),
    required       numeric(1,0)  not null default 0 check (required in (0, 1)),       -- needed in a finished build
    multi_allowed  numeric(1,0)  not null default 0 check (multi_allowed in (0, 1)),  -- several parts of this kind per build
    primary key (category_id)
);

create table products (
    product_id     integer,
    category_id    integer       not null,
    name           varchar(150)  not null,
    brand          varchar(100)  not null,
    model          varchar(100)  not null,
    specification  varchar(1000),
    primary key (product_id),
    foreign key (category_id) references categories (category_id)
);
create index idx_products_category on products (category_id);

create table stores (
    store_id  integer,
    name      varchar(100)  not null unique,
    website   varchar(255),
    primary key (store_id)
);

create table users (
    user_id   integer,
    username  varchar(50)   not null unique,
    email     varchar(255)  not null unique,
    role      varchar(20)   not null check (role in ('admin', 'customer')),
    primary key (user_id)
);

create table listings (
    listing_id          integer,
    product_id          integer        not null,
    store_id            integer        not null,
    created_by_user_id  integer        not null,
    price               numeric(10,2)  not null check (price >= 0),
    availability        varchar(20)    not null check (availability in ('in_stock', 'out_of_stock', 'preorder')),
    product_url         varchar(500),
    last_updated        datetime       not null default (datetime('now')),
    primary key (listing_id),
    unique (product_id, store_id),     -- one current listing per product per store
    foreign key (product_id) references products (product_id),
    foreign key (store_id) references stores (store_id),
    foreign key (created_by_user_id) references users (user_id)
);
create index idx_listings_store on listings (store_id);

-- Only administrators may create listings.
create trigger trg_listing_creator_admin before insert on listings
when (select role
      from users
      where user_id = new.created_by_user_id) <> 'admin'
begin
    select raise(abort, 'Only administrators can create listings');
end;

-- Any change to a listing refreshes its timestamp.
create trigger trg_listing_touch after update of price, availability, product_url on listings
begin
    update listings
    set last_updated = datetime('now')
    where listing_id = new.listing_id;
end;

-- part specs and builds, used for compatibility checking
create table socket (                 -- AM5, LGA1700, ...
    socket_id  integer,
    name       varchar(20)  not null unique,
    primary key (socket_id)
);

create table form_factor (            -- ATX, Micro-ATX, ...
    form_factor_id  integer,
    name            varchar(20)  not null unique,
    primary key (form_factor_id)
);

-- One specification table per kind of product (sub-type of products, same primary key).
create table cpu (
    product_id  integer,
    socket_id   integer  not null,
    cores       integer  not null check (cores > 0),
    threads     integer  not null check (threads >= cores),
    base_ghz    real     not null,
    boost_ghz   real     not null check (boost_ghz >= base_ghz),
    tdp_w       integer  not null check (tdp_w > 0),
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade,
    foreign key (socket_id) references socket (socket_id)
);

create table motherboard (
    product_id      integer,
    socket_id       integer      not null,
    form_factor_id  integer      not null,
    chipset         varchar(20)  not null,
    ram_type        varchar(4)   not null check (ram_type in ('DDR4', 'DDR5')),
    ram_slots       integer      not null check (ram_slots > 0),
    max_ram_gb      integer      not null check (max_ram_gb > 0),
    m2_slots        integer      not null check (m2_slots >= 0),
    sata_ports      integer      not null check (sata_ports >= 0),
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade,
    foreign key (socket_id) references socket (socket_id),
    foreign key (form_factor_id) references form_factor (form_factor_id)
);

create table ram (                    -- one product = one kit (e.g. 2 x 16 GB)
    product_id   integer,
    ram_type     varchar(4)  not null check (ram_type in ('DDR4', 'DDR5')),
    capacity_gb  integer     not null check (capacity_gb > 0),
    modules      integer     not null check (modules > 0),
    speed_mhz    integer     not null,
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade
);

create table gpu (
    product_id  integer,
    chipset     varchar(50)  not null,
    vram_gb     integer      not null check (vram_gb > 0),
    length_mm   integer      not null check (length_mm > 0),
    tdp_w       integer      not null check (tdp_w > 0),
    min_psu_w   integer      not null check (min_psu_w > 0),
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade
);

create table psu (
    product_id  integer,
    wattage     integer      not null check (wattage > 0),
    efficiency  varchar(20)  not null,
    modular     varchar(4)   not null check (modular in ('Full', 'Semi', 'No')),
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade
);

create table pc_case (
    product_id            integer,
    max_gpu_length_mm     integer  not null check (max_gpu_length_mm > 0),
    max_cooler_height_mm  integer  not null check (max_cooler_height_mm > 0),
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade
);

create table case_form_factor (       -- N:M  case <-> motherboard sizes it can hold
    product_id      integer  not null,
    form_factor_id  integer  not null,
    primary key (product_id, form_factor_id),
    foreign key (product_id) references pc_case (product_id) on delete cascade,
    foreign key (form_factor_id) references form_factor (form_factor_id)
);

create table storage (
    product_id    integer,
    storage_type  varchar(10)  not null check (storage_type in ('NVMe SSD', 'SATA SSD', 'HDD')),
    capacity_gb   integer      not null check (capacity_gb > 0),
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade
);

create table cooler (
    product_id   integer,
    cooler_type  varchar(6)  not null check (cooler_type in ('Air', 'Liquid')),
    height_mm    integer     not null check (height_mm > 0),
    max_tdp_w    integer     not null check (max_tdp_w > 0),
    primary key (product_id),
    foreign key (product_id) references products (product_id) on delete cascade
);

create table cooler_socket (          -- N:M  cooler <-> CPU sockets it mounts on
    product_id  integer  not null,
    socket_id   integer  not null,
    primary key (product_id, socket_id),
    foreign key (product_id) references cooler (product_id) on delete cascade,
    foreign key (socket_id) references socket (socket_id)
);

-- Saved PC builds (a customer's parts list that gets compatibility-checked)
create table builds (
    build_id    integer,
    user_id     integer       not null,
    name        varchar(100)  not null,
    created_at  varchar(10)   not null default (date('now')),
    primary key (build_id),
    foreign key (user_id) references users (user_id) on delete cascade
);

create table build_items (
    build_id    integer  not null,
    product_id  integer  not null,
    quantity    integer  not null default 1 check (quantity > 0),
    primary key (build_id, product_id),
    foreign key (build_id) references builds (build_id) on delete cascade,
    foreign key (product_id) references products (product_id)
);

-- A specification row may only be attached to a product of the matching category.
create trigger trg_cpu_cat before insert on cpu
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'CPU'
begin
    select raise(abort, 'Product is not in the CPU category');
end;

create trigger trg_motherboard_cat before insert on motherboard
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'Motherboard'
begin
    select raise(abort, 'Product is not in the Motherboard category');
end;

create trigger trg_ram_cat before insert on ram
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'RAM'
begin
    select raise(abort, 'Product is not in the RAM category');
end;

create trigger trg_gpu_cat before insert on gpu
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'GPU'
begin
    select raise(abort, 'Product is not in the GPU category');
end;

create trigger trg_psu_cat before insert on psu
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'PSU'
begin
    select raise(abort, 'Product is not in the PSU category');
end;

create trigger trg_pc_case_cat before insert on pc_case
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'Case'
begin
    select raise(abort, 'Product is not in the Case category');
end;

create trigger trg_storage_cat before insert on storage
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'Storage'
begin
    select raise(abort, 'Product is not in the Storage category');
end;

create trigger trg_cooler_cat before insert on cooler
when (select c.name
      from products as p inner join categories as c on p.category_id = c.category_id
      where p.product_id = new.product_id) <> 'Cooler'
begin
    select raise(abort, 'Product is not in the Cooler category');
end;

-- A build may hold only one part from a category that does not allow several.
create trigger trg_build_single_slot before insert on build_items
when (select multi_allowed
      from categories
      where category_id = (select category_id
                           from products
                           where product_id = new.product_id)) = 0
 and exists (select 1
             from build_items as bi inner join products as p on p.product_id = bi.product_id
             where bi.build_id = new.build_id
               and p.category_id = (select category_id
                                    from products
                                    where product_id = new.product_id))
begin
    select raise(abort, 'This build already has a part of that category');
end;

-- views

-- Cheapest IN-STOCK listing of every product (products with no in-stock listing do not appear).
create view v_best_price as
select l.product_id, l.price as best_price, s.name as store, l.listing_id
from listings as l inner join stores as s on s.store_id = l.store_id
where l.availability = 'in_stock'
  and l.price = (select min(x.price)
                 from listings as x
                 where x.product_id = l.product_id and x.availability = 'in_stock')
  and l.listing_id = (select min(y.listing_id)
                      from listings as y
                      where y.product_id = l.product_id and y.availability = 'in_stock'
                        and y.price = l.price);

-- Price of a build when every part is bought at its cheapest in-stock listing.
create view v_build_total as
select b.build_id, b.user_id, b.name,
       round(coalesce(sum(bi.quantity * bp.best_price), 0), 2) as total_price,
       count(bi.product_id) - count(bp.product_id) as parts_without_price
from builds as b
     left outer join build_items as bi on bi.build_id = b.build_id
     left outer join v_best_price as bp on bp.product_id = bi.product_id
group by b.build_id, b.user_id, b.name;

-- Compatibility check: one row for each problem in a build.
-- ERROR = parts don't work together, WARNING = build is missing a part.
create view v_build_issues as
-- 1. CPU socket must equal motherboard socket
select bm.build_id, 'ERROR' as severity, 'SOCKET' as rule,
       'CPU socket ' || sc.name || ' does not match motherboard socket ' || sm.name as message
from build_items as bc
     inner join cpu as c on c.product_id = bc.product_id
     inner join build_items as bm on bm.build_id = bc.build_id
     inner join motherboard as m on m.product_id = bm.product_id
     inner join socket as sc on sc.socket_id = c.socket_id
     inner join socket as sm on sm.socket_id = m.socket_id
where c.socket_id <> m.socket_id
union all
-- 2. RAM generation must equal motherboard memory type
select bm.build_id, 'ERROR', 'RAM_TYPE',
       'RAM is ' || r.ram_type || ' but motherboard supports ' || m.ram_type
from build_items as br
     inner join ram as r on r.product_id = br.product_id
     inner join build_items as bm on bm.build_id = br.build_id
     inner join motherboard as m on m.product_id = bm.product_id
where r.ram_type <> m.ram_type
union all
-- 3. Number of RAM sticks must fit the DIMM slots
select bm.build_id, 'ERROR', 'RAM_SLOTS',
       x.modules || ' RAM modules selected but motherboard has only ' || m.ram_slots || ' slots'
from (select bi.build_id, sum(r.modules * bi.quantity) as modules
      from build_items as bi inner join ram as r on r.product_id = bi.product_id
      group by bi.build_id) as x
     inner join build_items as bm on bm.build_id = x.build_id
     inner join motherboard as m on m.product_id = bm.product_id
where x.modules > m.ram_slots
union all
-- 4. Total RAM capacity must not exceed motherboard maximum
select bm.build_id, 'ERROR', 'RAM_CAPACITY',
       x.gb || ' GB of RAM selected but motherboard supports at most ' || m.max_ram_gb || ' GB'
from (select bi.build_id, sum(r.capacity_gb * bi.quantity) as gb
      from build_items as bi inner join ram as r on r.product_id = bi.product_id
      group by bi.build_id) as x
     inner join build_items as bm on bm.build_id = x.build_id
     inner join motherboard as m on m.product_id = bm.product_id
where x.gb > m.max_ram_gb
union all
-- 5. Motherboard size must be supported by the case
select bm.build_id, 'ERROR', 'FORM_FACTOR',
       'Case does not support ' || ff.name || ' motherboards'
from build_items as bm
     inner join motherboard as m on m.product_id = bm.product_id
     inner join build_items as bc on bc.build_id = bm.build_id
     inner join pc_case as pc on pc.product_id = bc.product_id
     inner join form_factor as ff on ff.form_factor_id = m.form_factor_id
where not exists (select 1
                  from case_form_factor as cf
                  where cf.product_id = pc.product_id and cf.form_factor_id = m.form_factor_id)
union all
-- 6. GPU must fit the case
select bg.build_id, 'ERROR', 'GPU_LENGTH',
       'GPU is ' || g.length_mm || ' mm long but case fits at most ' || pc.max_gpu_length_mm || ' mm'
from build_items as bg
     inner join gpu as g on g.product_id = bg.product_id
     inner join build_items as bc on bc.build_id = bg.build_id
     inner join pc_case as pc on pc.product_id = bc.product_id
where g.length_mm > pc.max_gpu_length_mm
union all
-- 7. Cooler must mount on the CPU socket
select bk.build_id, 'ERROR', 'COOLER_SOCKET',
       'Cooler does not support CPU socket ' || sc.name
from build_items as bk
     inner join cooler as k on k.product_id = bk.product_id
     inner join build_items as bc on bc.build_id = bk.build_id
     inner join cpu as c on c.product_id = bc.product_id
     inner join socket as sc on sc.socket_id = c.socket_id
where not exists (select 1
                  from cooler_socket as cs
                  where cs.product_id = k.product_id and cs.socket_id = c.socket_id)
union all
-- 8. Cooler must be able to handle the CPU's heat output
select bk.build_id, 'ERROR', 'COOLER_TDP',
       'Cooler rated for ' || k.max_tdp_w || ' W but CPU needs ' || c.tdp_w || ' W'
from build_items as bk
     inner join cooler as k on k.product_id = bk.product_id
     inner join build_items as bc on bc.build_id = bk.build_id
     inner join cpu as c on c.product_id = bc.product_id
where k.max_tdp_w < c.tdp_w
union all
-- 9. Cooler must fit inside the case
select bk.build_id, 'ERROR', 'COOLER_HEIGHT',
       'Cooler is ' || k.height_mm || ' mm tall but case allows at most ' || pc.max_cooler_height_mm || ' mm'
from build_items as bk
     inner join cooler as k on k.product_id = bk.product_id
     inner join build_items as bc on bc.build_id = bk.build_id
     inner join pc_case as pc on pc.product_id = bc.product_id
where k.height_mm > pc.max_cooler_height_mm
union all
-- 10. PSU must cover CPU + GPU + 100 W for the rest, and the GPU's own minimum
select bp.build_id, 'ERROR', 'PSU_POWER',
       'PSU is ' || p.wattage || ' W but build needs about ' ||
       max(c.tdp_w + coalesce(g.tdp_w, 0) + 100, coalesce(g.min_psu_w, 0)) || ' W'
from build_items as bp
     inner join psu as p on p.product_id = bp.product_id
     inner join build_items as bc on bc.build_id = bp.build_id
     inner join cpu as c on c.product_id = bc.product_id
     left outer join (select bi.build_id, g.tdp_w, g.min_psu_w
                      from build_items as bi inner join gpu as g on g.product_id = bi.product_id) as g
          on g.build_id = bp.build_id
where p.wattage < max(c.tdp_w + coalesce(g.tdp_w, 0) + 100, coalesce(g.min_psu_w, 0))
union all
-- 11. NVMe drives need M.2 slots
select bm.build_id, 'ERROR', 'M2_SLOTS',
       x.n || ' NVMe drives selected but motherboard has only ' || m.m2_slots || ' M.2 slots'
from (select bi.build_id, sum(bi.quantity) as n
      from build_items as bi inner join storage as s on s.product_id = bi.product_id
      where s.storage_type = 'NVMe SSD'
      group by bi.build_id) as x
     inner join build_items as bm on bm.build_id = x.build_id
     inner join motherboard as m on m.product_id = bm.product_id
where x.n > m.m2_slots
union all
-- 12. SATA SSD / HDD drives need SATA ports
select bm.build_id, 'ERROR', 'SATA_PORTS',
       x.n || ' SATA drives selected but motherboard has only ' || m.sata_ports || ' ports'
from (select bi.build_id, sum(bi.quantity) as n
      from build_items as bi inner join storage as s on s.product_id = bi.product_id
      where s.storage_type <> 'NVMe SSD'
      group by bi.build_id) as x
     inner join build_items as bm on bm.build_id = x.build_id
     inner join motherboard as m on m.product_id = bm.product_id
where x.n > m.sata_ports
union all
-- 13. Incomplete build: a required category is still empty
select b.build_id, 'WARNING', 'MISSING', 'No ' || c.name || ' selected yet'
from builds as b, categories as c
where c.required = 1
  and not exists (select 1
                  from build_items as bi inner join products as p on p.product_id = bi.product_id
                  where bi.build_id = b.build_id and p.category_id = c.category_id);
