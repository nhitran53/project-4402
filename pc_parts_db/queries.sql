-- Our 5 test queries. Run them with: python test_queries.py

-- Q1: Search for a product: show every RTX 4070 graphics card with its price at each store.
select p.product_id, p.name as product, c.name as category, s.name as store,
       l.price, l.availability, l.last_updated
from products as p
     inner join categories as c on c.category_id = p.category_id
     inner join listings as l on l.product_id = p.product_id
     inner join stores as s on s.store_id = l.store_id
where p.name like '%4070%'
order by p.name, l.price;

-- Q2: Cheapest available listing: which store sells the AMD Ryzen 7 7800X3D for the least while in stock?
select p.name as product, s.name as store, l.price, l.availability, l.product_url
from listings as l
     inner join products as p on p.product_id = l.product_id
     inner join stores as s on s.store_id = l.store_id
where p.name = 'AMD Ryzen 7 7800X3D' and l.availability = 'in_stock'
order by l.price
limit 1;

-- Q3: Average listing price by category (with the cheapest and most expensive listing).
select c.name as category, count(*) as listings,
       round(avg(l.price), 2) as avg_price, min(l.price) as lowest, max(l.price) as highest
from listings as l
     inner join products as p on p.product_id = l.product_id
     inner join categories as c on c.category_id = p.category_id
group by c.category_id, c.name
order by avg_price desc;

-- Q4: Products sold by more than one store: the 8 with the biggest price gap, with their lowest in-stock price.
select p.name as product, count(distinct l.store_id) as stores,
       min(l.price) as lowest_listed, max(l.price) as highest_listed,
       round(max(l.price) - min(l.price), 2) as price_gap,
       bp.best_price as lowest_in_stock, bp.store as cheapest_store
from listings as l
     inner join products as p on p.product_id = l.product_id
     left outer join v_best_price as bp on bp.product_id = p.product_id
group by p.product_id, p.name, bp.best_price, bp.store
having count(distinct l.store_id) > 1
order by price_gap desc
limit 8;

-- Q5: Compatibility check of saved build #59, priced with the cheapest in-stock listing of each part (view v_build_issues).
select b.build_id, b.name as build_name, u.username as owner, t.total_price as total_at_best_prices,
       i.severity, i.rule, i.message
from builds as b
     inner join users as u on u.user_id = b.user_id
     inner join v_build_total as t on t.build_id = b.build_id
     inner join v_build_issues as i on i.build_id = b.build_id
where b.build_id = 59
order by i.severity, i.rule;
