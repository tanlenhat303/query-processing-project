import argparse, random, datetime
import mysql.connector
from pymongo import MongoClient
from indexes import MONGO_URI, add_mongo_indexes

parser=argparse.ArgumentParser()
parser.add_argument('--orders',type=int,default=10000)
parser.add_argument('--index',action='store_true',help='Create both MongoDB experiment indexes after loading')
a=parser.parse_args()
if a.orders < 1:
    parser.error("--orders must be positive")
random.seed(42)
mc=MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
mc.admin.command('ping')
my=mysql.connector.connect(host='127.0.0.1',user='root',password='rootpass',database='ecommerce',connection_timeout=5)
cu=my.cursor()
cu.execute('SET FOREIGN_KEY_CHECKS=0')
for table in ('order_items','orders','products','customers'): cu.execute('DROP TABLE IF EXISTS '+table)
cu.execute('SET FOREIGN_KEY_CHECKS=1')
cu.execute('CREATE TABLE customers (customer_id INT PRIMARY KEY, name VARCHAR(100), email VARCHAR(150)) ENGINE=InnoDB')
cu.execute('CREATE TABLE products (product_id INT PRIMARY KEY, name VARCHAR(100), price DECIMAL(10,2)) ENGINE=InnoDB')
cu.execute('CREATE TABLE orders (order_id INT PRIMARY KEY, customer_id INT NOT NULL, order_date DATE NOT NULL, total_amount DECIMAL(12,2) NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(customer_id)) ENGINE=InnoDB')
cu.execute('CREATE TABLE order_items (order_id INT, product_id INT, quantity INT, unit_price DECIMAL(10,2), PRIMARY KEY(order_id,product_id), FOREIGN KEY(order_id) REFERENCES orders(order_id), FOREIGN KEY(product_id) REFERENCES products(product_id)) ENGINE=InnoDB')
db=mc.ecommerce
for coll in ('customers','products','orders','order_items'): db[coll].drop()
customers=[(i,f'Customer {i}',f'user{i}@example.test') for i in range(1,1001)]
products=[(i,f'Product {i}',float(50+(i*37)%950)) for i in range(1,501)]
cu.executemany('INSERT INTO customers VALUES (%s,%s,%s)',customers)
cu.executemany('INSERT INTO products VALUES (%s,%s,%s)',products)
db.customers.insert_many([{'_id':i,'customer_id':i,'name':n,'email':e} for i,n,e in customers])
db.products.insert_many([{'_id':i,'product_id':i,'name':n,'price':pr} for i,n,pr in products])
for start in range(1,a.orders+1,2000):
    rows=[]; docs=[]; item_rows=[]; item_docs=[]
    for i in range(start,min(start+2000,a.orders+1)):
        cid=1+((i*17)%1000); day=datetime.date(2025,1,1)+datetime.timedelta(days=i%365)
        ids=random.sample(range(1,501),2); quantities=[1+i%3,1+(i//3)%3]
        items=[(pid,qty,float(50+(pid*37)%950)) for pid,qty in zip(ids,quantities)]
        total=round(sum(q*pr for _,q,pr in items),2)
        rows.append((i,cid,day,total))
        docs.append({'_id':i,'order_id':i,'customer_id':cid,'order_date':datetime.datetime.combine(day,datetime.time()),'total_amount':total})
        for pid,qty,price in items:
            item_rows.append((i,pid,qty,price))
            item_docs.append({'order_id':i,'product_id':pid,'quantity':qty,'unit_price':price})
    cu.executemany('INSERT INTO orders VALUES (%s,%s,%s,%s)',rows)
    cu.executemany('INSERT INTO order_items VALUES (%s,%s,%s,%s)',item_rows)
    db.orders.insert_many(docs); db.order_items.insert_many(item_docs)
    my.commit(); print('Loaded',min(start+1999,a.orders),'/',a.orders,flush=True)
if a.index:
    add_mongo_indexes(db)
my.commit(); my.close(); mc.close()
print('Done. MySQL and MongoDB contain equivalent normalized logical records.')
