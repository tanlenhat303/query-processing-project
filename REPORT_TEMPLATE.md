# Query Processing Performance Comparison: MySQL vs MongoDB

## 1. Introduction
Objective: assess query-processing performance for e-commerce workloads, selecting a suitable DBMS for filtering, joining and aggregation.

## 2. DBMS and query-processing theory
MySQL: SQL parser, optimizer, execution plan, join strategy and index access. MongoDB: query planner, winning plan, aggregation pipeline and $lookup.

## 3. Dataset and fairness
Describe customer/product/order/order_items schema, number of rows, data-generation seed, hardware, Docker image versions, index inventory, normalized model, workload selectivity, repeated measurements, warm-up and timing methodology.

## 4. Experiments
### E1: Filter products by price > 500
SQL WHERE vs MongoDB find. Capture scan type and elapsed time.
### E2: Join orders and customers
SQL JOIN vs MongoDB $lookup. Capture plans, counts and timing.
### E3: Revenue per customer
SQL GROUP BY vs MongoDB $group. Compare runtime and correctness.
### E4: Customer order lookup with/without index
Compare explain plans and performance. **Important:** foreign keys in MySQL may automatically create an index; design a genuinely nonindexed baseline before claiming a before/after result.

## 5. Results (fill after actual runs)
| Dataset | Query | MySQL median (ms) | MongoDB median (ms) | Plan notes | Winner |
|---|---|---:|---:|---|---|
| 10k | Filter | TBD | TBD | TBD | TBD |
| 10k | Join | TBD | TBD | TBD | TBD |
| 10k | Aggregation | TBD | TBD | TBD | TBD |
| 10k | Customer filter | TBD | TBD | TBD | TBD |

## 6. Discussion
Explain effects of dataset size, indexes, join execution, cardinality and result transfer. Acknowledge benchmark limits and document-model tradeoffs.

## 7. Application architecture
Browser HTML/JS -> Express.js API -> MySQL 8.4. Endpoints: GET /api/products?minPrice=500, GET /api/orders, GET /api/revenue. Show screenshots and explain the API design.

## 8. Conclusion
Recommend a DBMS **only after measuring**, tied to the e-commerce workload and data model.

## References
1. MySQL 8.4 Reference Manual: https://dev.mysql.com/doc/refman/8.4/en/explain.html
2. MySQL EXPLAIN ANALYZE: https://dev.mysql.com/doc/refman/8.4/en/explain-analyze.html
3. MongoDB Explain Results: https://www.mongodb.com/docs/v8.0/reference/explain-results/
4. MongoDB $lookup: https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/lookup/
