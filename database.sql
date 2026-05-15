CREATE DATABASE skin_care_db ; 
USE skin_care_db ; 
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY , 
    username VARCHAR(50), 
    password VARCHAR(50)
) ; 
CREATE TABLE patients(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    result VARCHAR(20),
    probability FLOAT , 
    image_path VARCHAR(50) , 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);