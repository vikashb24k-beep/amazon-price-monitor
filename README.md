# Amazon Bearing Price Monitoring System

This project demonstrates a simplified architecture for monitoring Amazon India prices for products such as SKF bearings.

Components:
- Scrapy spiders for search, product pages, and seller offers
- PostgreSQL pipeline for storing price history
- Streamlit dashboard for analytics

Run spiders:
scrapy crawl amazon_search