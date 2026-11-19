import express from 'express';
import cors from 'cors';
import mysql from 'mysql2/promise';
const app=express(); app.use(cors()); app.use(express.static('public'));
const pool=mysql.createPool({host:'127.0.0.1',user:'root',password:'rootpass',database:'ecommerce',waitForConnections:true,connectionLimit:10});
app.get('/api/products',async(req,res)=>{try{const min=Number(req.query.minPrice||0);if(!Number.isFinite(min))return res.status(400).json({error:'Invalid price'});const [rows]=await pool.execute('SELECT product_id,name,price FROM products WHERE price > ? LIMIT 100',[min]);res.json(rows)}catch(e){res.status(500).json({error:'Database unavailable'})}});
app.get('/api/orders',async(req,res)=>{try{const [rows]=await pool.query('SELECT o.order_id,c.name AS customer,o.order_date,o.total_amount FROM orders o JOIN customers c ON o.customer_id=c.customer_id ORDER BY o.order_id DESC LIMIT 50');res.json(rows)}catch(e){res.status(500).json({error:'Database unavailable'})}});
app.get('/api/revenue',async(req,res)=>{try{const [rows]=await pool.query('SELECT customer_id,SUM(total_amount) AS revenue FROM orders GROUP BY customer_id ORDER BY revenue DESC LIMIT 20');res.json(rows)}catch(e){res.status(500).json({error:'Database unavailable'})}});
app.listen(3000,()=>console.log('Open http://localhost:3000'));
