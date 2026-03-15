CREATE DATABASE amazon_prices;

USE amazon_prices;

CREATE TABLE price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asin VARCHAR(50),
    seller VARCHAR(255),
    price FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);