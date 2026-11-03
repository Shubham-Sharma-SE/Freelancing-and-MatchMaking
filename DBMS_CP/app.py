import os
import re
import time
import sqlite3
import decimal
import pathlib

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Freelancer DBMS Dashboard", layout="wide")

DB_PATH = pathlib.Path(__file__).with_name("freelancer_demo.db")
DEFAULT_DB = "FreelancerDB"

# ----------------------------------------------------------------------------
# SCHEMA + SAMPLE DATA  (copied verbatim from report sections 8.2 and 8.3)
# ----------------------------------------------------------------------------
DDL_SQL = """CREATE TABLE Client (
    ClientID INT PRIMARY KEY,
    ClientName VARCHAR(100) NOT NULL,
    Email VARCHAR(120) UNIQUE,
    Phone VARCHAR(15) NOT NULL,
    City VARCHAR(50) NOT NULL
) ENGINE = InnoDB;

CREATE TABLE Freelancer (
    FreelancerID INT PRIMARY KEY,
    FullName VARCHAR(100) NOT NULL,
    Email VARCHAR(120) UNIQUE,
    Phone VARCHAR(15) NOT NULL,
    City VARCHAR(50) NOT NULL,
    HourlyRate DECIMAL(8,2) NOT NULL CHECK (HourlyRate > 0),
    ExperienceYears INT NOT NULL CHECK (ExperienceYears >= 0),
    Rating DECIMAL(2,1) CHECK (Rating BETWEEN 0 AND 5)
) ENGINE = InnoDB;

CREATE TABLE Skill (
    SkillID INT PRIMARY KEY,
    SkillName VARCHAR(50) NOT NULL UNIQUE,
    Category VARCHAR(50) NOT NULL
) ENGINE = InnoDB;

CREATE TABLE Freelancer_Skill (
    FreelancerID INT NOT NULL,
    SkillID INT NOT NULL,
    ProficiencyLevel VARCHAR(20) NOT NULL,
    PRIMARY KEY (FreelancerID, SkillID),
    FOREIGN KEY (FreelancerID)
        REFERENCES Freelancer(FreelancerID)
        ON DELETE CASCADE,
    FOREIGN KEY (SkillID)
        REFERENCES Skill(SkillID)
        ON DELETE RESTRICT,
    CHECK (ProficiencyLevel IN ('Beginner', 'Intermediate', 'Expert'))
) ENGINE = InnoDB;

CREATE TABLE Project (
    ProjectID INT PRIMARY KEY,
    ClientID INT NOT NULL,
    Title VARCHAR(150) NOT NULL,
    Budget DECIMAL(10,2) NOT NULL,
    PostedDate DATE NOT NULL,
    Deadline DATE NOT NULL,
    Status VARCHAR(20) NOT NULL DEFAULT 'Open',
    FOREIGN KEY (ClientID)
        REFERENCES Client(ClientID)
        ON DELETE RESTRICT,
    CHECK (Budget > 0),
    CHECK (Deadline > PostedDate),
    CHECK (Status IN ('Open', 'In Progress', 'Completed', 'Cancelled'))
) ENGINE = InnoDB;

CREATE TABLE Project_Skill (
    ProjectID INT NOT NULL,
    SkillID INT NOT NULL,
    RequiredLevel VARCHAR(20) NOT NULL,
    PRIMARY KEY (ProjectID, SkillID),
    FOREIGN KEY (ProjectID)
        REFERENCES Project(ProjectID)
        ON DELETE CASCADE,
    FOREIGN KEY (SkillID)
        REFERENCES Skill(SkillID)
        ON DELETE RESTRICT,
    CHECK (RequiredLevel IN ('Beginner', 'Intermediate', 'Expert'))
) ENGINE = InnoDB;

CREATE TABLE Proposal (
    ProposalID INT PRIMARY KEY,
    ProjectID INT NOT NULL,
    FreelancerID INT NOT NULL,
    BidAmount DECIMAL(10,2) NOT NULL,
    SubmittedDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (ProjectID)
        REFERENCES Project(ProjectID)
        ON DELETE RESTRICT,
    FOREIGN KEY (FreelancerID)
        REFERENCES Freelancer(FreelancerID)
        ON DELETE RESTRICT,
    UNIQUE (ProjectID, FreelancerID),
    CHECK (BidAmount > 0),
    CHECK (Status IN ('Pending', 'Accepted', 'Rejected', 'Withdrawn'))
) ENGINE = InnoDB;

CREATE TABLE Payment (
    PaymentID INT PRIMARY KEY,
    ProposalID INT NOT NULL UNIQUE,
    Amount DECIMAL(10,2) NOT NULL,
    PaymentDate DATE NULL,
    PaymentMethod VARCHAR(20) NOT NULL,
    PaymentStatus VARCHAR(20) NOT NULL,
    FOREIGN KEY (ProposalID)
        REFERENCES Proposal(ProposalID)
        ON DELETE CASCADE,
    CHECK (Amount >= 0),
    CHECK (PaymentMethod IN ('UPI', 'Card', 'NetBanking', 'BankTransfer')),
    CHECK (PaymentStatus IN ('Paid', 'Pending', 'Failed', 'Refunded'))
) ENGINE = InnoDB;"""

INSERT_SQL = """INSERT INTO Client VALUES
(1, 'TechNova Solutions', 'contact@technova.example.com', '9820010001', 'Pune'),
(2, 'GreenLeaf Organics', 'hello@greenleaf.example.com', '9820010002', 'Nashik'),
(3, 'UrbanCart Retail', 'support@urbancart.example.com', '9820010003', 'Mumbai'),
(4, 'EduSpark Learning', 'team@eduspark.example.com', '9820010004', 'Bengaluru'),
(5, 'MediCare Plus', 'info@medicareplus.example.com', '9820010005', 'Hyderabad'),
(6, 'FinEdge Capital', 'admin@finedge.example.com', '9820010006', 'Mumbai'),
(7, 'TravelBuddy Pvt Ltd', 'trips@travelbuddy.example.com', '9820010007', 'Delhi'),
(8, 'FoodieHub', 'orders@foodiehub.example.com', '9820010008', 'Pune'),
(9, 'SmartHome Devices', 'sales@smarthome.example.com', '9820010009', 'Chennai'),
(10, 'PixelCraft Studios', 'studio@pixelcraft.example.com', '9820010010', 'Bengaluru'),
(11, 'AgroTrade India', 'office@agrotrade.example.com', '9820010011', 'Nashik'),
(12, 'BrightFuture Foundation', 'ngo@brightfuture.example.com', '9820010012', 'Pune'),
(13, 'CloudNest Technologies', 'hr@cloudnest.example.com', '9820010013', 'Hyderabad'),
(14, 'FitLife Gym Network', 'join@fitlife.example.com', '9820010014', 'Ahmedabad'),
(15, 'UrbanNest Realty', 'leads@urbannest.example.com', '9820010015', 'Mumbai'),
(16, 'StyleSutra Fashion', 'shop@stylesutra.example.com', '9820010016', 'Jaipur'),
(17, 'AutoDrive Motors', 'service@autodrive.example.com', '9820010017', 'Pune'),
(18, 'HealthFirst Clinics', 'care@healthfirst.example.com', '9820010018', 'Kolkata'),
(19, 'BookWorm Publications', 'books@bookworm.example.com', '9820010019', 'Delhi'),
(20, 'SolarBright Energy', 'power@solarbright.example.com', '9820010020', 'Ahmedabad'),
(21, 'QuickLogix Couriers', 'ops@quicklogix.example.com', '9820010021', 'Mumbai'),
(22, 'NextGen Gaming', 'play@nextgen.example.com', '9820010022', 'Bengaluru'),
(23, 'EventPro Planners', 'events@eventpro.example.com', '9820010023', 'Chennai'),
(24, 'PetPals Care', 'woof@petpals.example.com', '9820010024', 'Pune'),
(25, 'LegalEase Advisors', 'advice@legalease.example.com', '9820010025', 'Delhi');
INSERT INTO Freelancer VALUES
(1, 'Aarav Mehta', 'aarav.mehta@example.com', '9876500001', 'Pune', 850.00, 5, 4.6),
(2, 'Ananya Iyer', 'ananya.iyer@example.com', '9876500002', 'Bengaluru', 1200.00, 7, 4.8),
(3, 'Rohan Kulkarni', 'rohan.kulkarni@example.com', '9876500003', 'Pune', 700.00, 3, 4.2),
(4, 'Sneha Patil', 'sneha.patil@example.com', '9876500004', 'Nashik', 600.00, 2, 4.0),
(5, 'Vikram Singh', 'vikram.singh@example.com', '9876500005', 'Delhi', 1500.00, 9, 4.9),
(6, 'Priya Nair', 'priya.nair@example.com', '9876500006', 'Chennai', 950.00, 4, 4.5),
(7, 'Karan Shah', 'karan.shah@example.com', '9876500007', 'Ahmedabad', 800.00, 4, 4.3),
(8, 'Neha Joshi', 'neha.joshi@example.com', '9876500008', 'Pune', 650.00, 3, 4.1),
(9, 'Arjun Reddy', 'arjun.reddy@example.com', '9876500009', 'Hyderabad', 1100.00, 6, 4.7),
(10, 'Divya Menon', 'divya.menon@example.com', '9876500010', 'Bengaluru', 1000.00, 5, 4.4),
(11, 'Siddharth Rao', 'siddharth.rao@example.com', '9876500011', 'Mumbai', 1300.00, 8, 4.8),
(12, 'Pooja Deshmukh', 'pooja.deshmukh@example.com', '9876500012', 'Mumbai', 750.00, 3, 4.2),
(13, 'Rahul Verma', 'rahul.verma@example.com', '9876500013', 'Delhi', 900.00, 5, 4.3),
(14, 'Isha Gupta', 'isha.gupta@example.com', '9876500014', 'Jaipur', 550.00, 2, 3.9),
(15, 'Manish Kapoor', 'manish.kapoor@example.com', '9876500015', 'Kolkata', 1400.00, 10, 4.9),
(16, 'Tanvi Bhosale', 'tanvi.bhosale@example.com', '9876500016', 'Pune', 500.00, 1, 3.8),
(17, 'Aditya Jain', 'aditya.jain@example.com', '9876500017', 'Ahmedabad', 1050.00, 6, 4.5),
(18, 'Kavya Krishnan', 'kavya.krishnan@example.com', '9876500018', 'Chennai', 880.00, 4, 4.4),
(19, 'Harsh Agarwal', 'harsh.agarwal@example.com', '9876500019', 'Jaipur', 720.00, 3, 4.0),
(20, 'Meera Pawar', 'meera.pawar@example.com', '9876500020', 'Nashik', 680.00, 3, 4.1),
(21, 'Nikhil Chavan', 'nikhil.chavan@example.com', '9876500021', 'Mumbai', 1250.00, 7, 4.7),
(22, 'Shreya Banerjee', 'shreya.banerjee@example.com', '9876500022', 'Kolkata', 780.00, 4, 4.2),
(23, 'Omkar Gaikwad', 'omkar.gaikwad@example.com', '9876500023', 'Pune', 900.00, 5, 4.5),
(24, 'Riya Malhotra', 'riya.malhotra@example.com', '9876500024', 'Delhi', 600.00, 2, 3.9),
(25, 'Yash Thakur', 'yash.thakur@example.com', '9876500025', 'Hyderabad', 1150.00, 6, 4.6);
INSERT INTO Skill VALUES
(1, 'Python', 'Programming'),
(2, 'Java', 'Programming'),
(3, 'JavaScript', 'Web Development'),
(4, 'React', 'Web Development'),
(5, 'Node.js', 'Web Development'),
(6, 'HTML/CSS', 'Web Development'),
(7, 'PHP', 'Web Development'),
(8, 'SQL', 'Database'),
(9, 'MongoDB', 'Database'),
(10, 'Android Development', 'Mobile'),
(11, 'Flutter', 'Mobile'),
(12, 'UI/UX Design', 'Design'),
(13, 'Graphic Design', 'Design'),
(14, 'Figma', 'Design'),
(15, 'Content Writing', 'Writing'),
(16, 'Technical Writing', 'Writing'),
(17, 'SEO', 'Marketing'),
(18, 'Digital Marketing', 'Marketing'),
(19, 'Data Analysis', 'Data Science'),
(20, 'Machine Learning', 'Data Science'),
(21, 'Power BI', 'Data Science'),
(22, 'Video Editing', 'Multimedia'),
(23, 'Cloud Computing', 'Cloud'),
(24, 'Cybersecurity', 'Security'),
(25, 'Project Management', 'Management');
INSERT INTO Freelancer_Skill VALUES
(1, 1, 'Expert'),
(1, 8, 'Intermediate'),
(1, 19, 'Intermediate'),
(2, 4, 'Expert'),
(2, 3, 'Expert'),
(2, 5, 'Intermediate'),
(2, 12, 'Intermediate'),
(3, 2, 'Intermediate'),
(3, 8, 'Intermediate'),
(3, 10, 'Beginner'),
(4, 13, 'Intermediate'),
(4, 14, 'Intermediate'),
(4, 12, 'Beginner'),
(5, 23, 'Expert'),
(5, 24, 'Expert'),
(5, 1, 'Intermediate'),
(6, 15, 'Expert'),
(6, 17, 'Intermediate'),
(6, 18, 'Intermediate'),
(7, 7, 'Expert'),
(7, 6, 'Expert'),
(7, 3, 'Intermediate'),
(7, 8, 'Intermediate'),
(8, 19, 'Intermediate'),
(8, 21, 'Intermediate'),
(8, 8, 'Intermediate'),
(9, 20, 'Expert'),
(9, 1, 'Expert'),
(9, 19, 'Expert'),
(10, 12, 'Expert'),
(10, 14, 'Expert'),
(10, 6, 'Intermediate'),
(11, 2, 'Expert'),
(11, 8, 'Expert'),
(11, 23, 'Intermediate'),
(12, 22, 'Expert'),
(12, 13, 'Intermediate'),
(13, 5, 'Expert'),
(13, 9, 'Expert'),
(13, 3, 'Expert'),
(13, 4, 'Intermediate'),
(14, 16, 'Intermediate'),
(14, 15, 'Intermediate'),
(15, 11, 'Expert'),
(15, 10, 'Expert'),
(15, 12, 'Intermediate'),
(15, 5, 'Beginner'),
(16, 6, 'Intermediate'),
(16, 3, 'Beginner'),
(16, 13, 'Beginner'),
(17, 18, 'Expert'),
(17, 17, 'Expert'),
(17, 15, 'Intermediate'),
(18, 21, 'Expert'),
(18, 19, 'Expert'),
(18, 8, 'Intermediate'),
(19, 25, 'Intermediate'),
(19, 16, 'Expert'),
(20, 13, 'Expert'),
(20, 22, 'Intermediate'),
(21, 1, 'Expert'),
(21, 20, 'Intermediate'),
(21, 8, 'Expert'),
(21, 4, 'Intermediate'),
(22, 11, 'Intermediate'),
(22, 12, 'Intermediate'),
(22, 3, 'Intermediate'),
(23, 4, 'Expert'),
(23, 5, 'Expert'),
(23, 9, 'Intermediate'),
(23, 8, 'Intermediate'),
(24, 17, 'Intermediate'),
(24, 15, 'Intermediate'),
(24, 18, 'Beginner'),
(25, 10, 'Expert'),
(25, 2, 'Expert'),
(25, 5, 'Intermediate'),
(25, 24, 'Intermediate');
INSERT INTO Project VALUES
(1, 1, 'Company Website Redesign', 45000.00, '2026-08-01', '2026-09-01', 'Completed'),
(2, 2, 'Organic Store Mobile App', 90000.00, '2026-08-03', '2026-09-30', 'Completed'),
(3, 3, 'Product Catalog Database Design', 30000.00, '2026-08-05', '2026-08-25', 'Completed'),
(4, 4, 'Online Learning Portal', 120000.00, '2026-08-08', '2026-10-15', 'Completed'),
(5, 5, 'Patient Appointment Booking System', 85000.00, '2026-08-10', '2026-10-05', 'Completed'),
(6, 6, 'Loan Default Prediction Model', 100000.00, '2026-08-12', '2026-10-10', 'Completed'),
(7, 7, 'Travel Blog Content Series', 20000.00, '2026-08-14', '2026-09-14', 'Completed'),
(8, 8, 'Restaurant Brand Identity Design', 25000.00, '2026-08-16', '2026-09-10', 'Completed'),
(9, 9, 'IoT Device Dashboard', 70000.00, '2026-08-18', '2026-10-12', 'Completed'),
(10, 10, 'Promotional Video Editing', 18000.00, '2026-08-20', '2026-09-05', 'Completed'),
(11, 11, 'Crop Sales Analytics Dashboard', 55000.00, '2026-08-22', '2026-10-01', 'Completed'),
(12, 12, 'NGO Donation Website', 40000.00, '2026-08-25', '2026-09-25', 'Completed'),
(13, 13, 'Cloud Migration Planning', 150000.00, '2026-09-01', '2026-12-15', 'In Progress'),
(14, 14, 'Fitness Tracking App', 95000.00, '2026-09-03', '2026-12-05', 'In Progress'),
(15, 15, 'Property Listing Portal', 110000.00, '2026-09-05', '2026-12-10', 'In Progress'),
(16, 16, 'E-Commerce Digital Marketing Campaign', 60000.00, '2026-09-08', '2026-11-30', 'In Progress'),
(17, 17, 'Vehicle Service Booking System', 80000.00, '2026-09-10', '2026-11-25', 'In Progress'),
(18, 18, 'Clinic Data Analytics', 65000.00, '2026-09-12', '2026-11-20', 'In Progress'),
(19, 19, 'Technical Documentation for API', 30000.00, '2026-09-15', '2026-11-15', 'In Progress'),
(20, 20, 'Solar Plant Monitoring Dashboard', 125000.00, '2026-09-18', '2026-12-20', 'In Progress'),
(21, 21, 'Courier Tracking Mobile App', 105000.00, '2026-09-20', '2026-12-12', 'In Progress'),
(22, 22, 'Game Landing Page and Trailer', 50000.00, '2026-09-22', '2026-11-28', 'In Progress'),
(23, 1, 'Customer Support Chatbot', 75000.00, '2026-09-25', '2026-11-10', 'Cancelled'),
(24, 3, 'Seasonal Sale Banner Pack', 12000.00, '2026-09-27', '2026-10-20', 'Cancelled'),
(25, 10, 'Mobile Game Prototype', 140000.00, '2026-09-30', '2026-12-30', 'Cancelled'),
(26, 2, 'Inventory Management Web App', 70000.00, '2026-10-10', '2026-12-20', 'Open'),
(27, 4, 'Course Recommendation Engine', 130000.00, '2026-10-12', '2027-01-15', 'Open'),
(28, 6, 'Fraud Detection Dashboard', 115000.00, '2026-10-15', '2027-01-10', 'Open'),
(29, 9, 'Smart Home Companion App', 98000.00, '2026-10-18', '2027-01-20', 'Open'),
(30, 11, 'Farmer Marketplace Website', 85000.00, '2026-10-22', '2027-01-05', 'Open');
INSERT INTO Project_Skill VALUES
(1, 6, 'Intermediate'),
(1, 3, 'Intermediate'),
(1, 12, 'Intermediate'),
(2, 11, 'Expert'),
(2, 12, 'Intermediate'),
(3, 8, 'Expert'),
(4, 4, 'Expert'),
(4, 5, 'Intermediate'),
(4, 8, 'Intermediate'),
(5, 2, 'Expert'),
(5, 8, 'Intermediate'),
(6, 1, 'Expert'),
(6, 20, 'Expert'),
(6, 19, 'Intermediate'),
(7, 15, 'Intermediate'),
(7, 17, 'Intermediate'),
(8, 13, 'Intermediate'),
(8, 14, 'Intermediate'),
(9, 4, 'Intermediate'),
(9, 5, 'Expert'),
(10, 22, 'Expert'),
(11, 21, 'Expert'),
(11, 19, 'Intermediate'),
(11, 8, 'Intermediate'),
(12, 7, 'Expert'),
(12, 6, 'Intermediate'),
(12, 8, 'Intermediate'),
(13, 23, 'Expert'),
(13, 24, 'Intermediate'),
(14, 11, 'Expert'),
(14, 10, 'Intermediate'),
(14, 12, 'Intermediate'),
(15, 4, 'Intermediate'),
(15, 5, 'Intermediate'),
(15, 9, 'Intermediate'),
(16, 18, 'Expert'),
(16, 17, 'Intermediate'),
(16, 15, 'Intermediate'),
(17, 2, 'Intermediate'),
(17, 8, 'Intermediate'),
(18, 21, 'Intermediate'),
(18, 8, 'Intermediate'),
(18, 19, 'Intermediate'),
(19, 16, 'Expert'),
(20, 1, 'Intermediate'),
(20, 19, 'Intermediate'),
(20, 4, 'Intermediate'),
(21, 10, 'Expert'),
(21, 5, 'Intermediate'),
(22, 3, 'Intermediate'),
(22, 22, 'Intermediate'),
(22, 12, 'Intermediate'),
(23, 1, 'Intermediate'),
(23, 20, 'Intermediate'),
(24, 13, 'Intermediate'),
(25, 10, 'Intermediate'),
(25, 13, 'Intermediate'),
(26, 1, 'Intermediate'),
(26, 8, 'Intermediate'),
(26, 4, 'Intermediate'),
(27, 1, 'Expert'),
(27, 20, 'Intermediate'),
(27, 8, 'Intermediate'),
(28, 21, 'Intermediate'),
(28, 8, 'Intermediate'),
(28, 19, 'Intermediate'),
(29, 11, 'Intermediate'),
(29, 12, 'Intermediate'),
(29, 5, 'Beginner'),
(30, 4, 'Intermediate'),
(30, 5, 'Intermediate'),
(30, 9, 'Intermediate');
INSERT INTO Proposal VALUES
(1, 1, 10, 42000.00, '2026-08-02', 'Accepted'),
(2, 2, 15, 85000.00, '2026-08-04', 'Accepted'),
(3, 3, 11, 28000.00, '2026-08-06', 'Accepted'),
(4, 4, 23, 112000.00, '2026-08-09', 'Accepted'),
(5, 5, 25, 80000.00, '2026-08-11', 'Accepted'),
(6, 6, 9, 95000.00, '2026-08-13', 'Accepted'),
(7, 7, 6, 18000.00, '2026-08-15', 'Accepted'),
(8, 8, 20, 23000.00, '2026-08-17', 'Accepted'),
(9, 9, 13, 66000.00, '2026-08-19', 'Accepted'),
(10, 10, 12, 16500.00, '2026-08-21', 'Accepted'),
(11, 11, 18, 52000.00, '2026-08-23', 'Accepted'),
(12, 12, 7, 38000.00, '2026-08-26', 'Accepted'),
(13, 13, 5, 140000.00, '2026-09-02', 'Accepted'),
(14, 14, 15, 90000.00, '2026-09-04', 'Accepted'),
(15, 15, 13, 105000.00, '2026-09-06', 'Accepted'),
(16, 16, 17, 57000.00, '2026-09-09', 'Accepted'),
(17, 17, 11, 76000.00, '2026-09-11', 'Accepted'),
(18, 18, 8, 62000.00, '2026-09-13', 'Accepted'),
(19, 19, 19, 28000.00, '2026-09-16', 'Accepted'),
(20, 20, 21, 118000.00, '2026-09-19', 'Accepted'),
(21, 21, 25, 100000.00, '2026-09-21', 'Accepted'),
(22, 22, 22, 47000.00, '2026-09-23', 'Accepted'),
(23, 23, 1, 70000.00, '2026-09-26', 'Accepted'),
(24, 24, 4, 11000.00, '2026-09-28', 'Accepted'),
(25, 25, 3, 130000.00, '2026-10-01', 'Accepted'),
(26, 1, 7, 44000.00, '2026-08-02', 'Rejected'),
(27, 1, 16, 39000.00, '2026-08-03', 'Rejected'),
(28, 2, 22, 88000.00, '2026-08-05', 'Rejected'),
(29, 4, 2, 115000.00, '2026-08-10', 'Rejected'),
(30, 6, 21, 98000.00, '2026-08-14', 'Rejected'),
(31, 9, 23, 68000.00, '2026-08-20', 'Rejected'),
(32, 11, 8, 54000.00, '2026-08-24', 'Rejected'),
(33, 13, 11, 145000.00, '2026-09-03', 'Rejected'),
(34, 20, 9, 120000.00, '2026-09-20', 'Rejected'),
(35, 14, 22, 92000.00, '2026-09-05', 'Withdrawn'),
(36, 16, 6, 59000.00, '2026-09-10', 'Withdrawn'),
(37, 26, 1, 66000.00, '2026-10-11', 'Pending'),
(38, 26, 23, 68000.00, '2026-10-12', 'Pending'),
(39, 26, 21, 69000.00, '2026-10-13', 'Pending'),
(40, 27, 9, 125000.00, '2026-10-13', 'Pending'),
(41, 27, 21, 128000.00, '2026-10-14', 'Pending'),
(42, 28, 18, 110000.00, '2026-10-16', 'Pending'),
(43, 28, 8, 105000.00, '2026-10-17', 'Pending'),
(44, 29, 15, 95000.00, '2026-10-19', 'Pending'),
(45, 29, 22, 90000.00, '2026-10-20', 'Pending'),
(46, 30, 13, 82000.00, '2026-10-23', 'Pending'),
(47, 30, 23, 80000.00, '2026-10-24', 'Pending');
INSERT INTO Payment VALUES
(5001, 1, 42000.00, '2026-09-02', 'UPI', 'Paid'),
(5002, 2, 85000.00, '2026-10-01', 'Card', 'Paid'),
(5003, 3, 28000.00, '2026-08-26', 'NetBanking', 'Paid'),
(5004, 4, 112000.00, '2026-10-16', 'BankTransfer', 'Paid'),
(5005, 5, 80000.00, '2026-10-06', 'UPI', 'Paid'),
(5006, 6, 95000.00, '2026-10-11', 'BankTransfer', 'Paid'),
(5007, 7, 18000.00, '2026-09-15', 'UPI', 'Paid'),
(5008, 8, 23000.00, '2026-09-11', 'Card', 'Paid'),
(5009, 9, 66000.00, '2026-10-13', 'NetBanking', 'Paid'),
(5010, 10, 16500.00, '2026-09-06', 'UPI', 'Paid'),
(5011, 11, 52000.00, '2026-10-02', 'BankTransfer', 'Paid'),
(5012, 12, 38000.00, '2026-09-26', 'Card', 'Paid'),
(5013, 13, 70000.00, '2026-09-05', 'BankTransfer', 'Paid'),
(5014, 14, 45000.00, '2026-09-08', 'UPI', 'Paid'),
(5015, 15, 52500.00, '2026-09-10', 'NetBanking', 'Paid'),
(5016, 16, 28500.00, '2026-09-12', 'Card', 'Paid'),
(5017, 17, 38000.00, '2026-09-14', 'UPI', 'Paid'),
(5018, 18, 31000.00, NULL, 'Card', 'Pending'),
(5019, 19, 14000.00, '2026-09-18', 'UPI', 'Paid'),
(5020, 20, 59000.00, '2026-09-22', 'BankTransfer', 'Paid'),
(5021, 21, 50000.00, '2026-09-25', 'NetBanking', 'Failed'),
(5022, 22, 23500.00, NULL, 'UPI', 'Pending'),
(5023, 23, 35000.00, '2026-09-29', 'Card', 'Refunded'),
(5024, 24, 5500.00, '2026-09-30', 'UPI', 'Refunded'),
(5025, 25, 65000.00, '2026-10-03', 'Card', 'Failed');"""


def split_sql(text):
    statements = []
    for statement in text.split(";"):
        statement = statement.strip()
        if statement:
            statements.append(statement)
    return statements


DDL_STATEMENTS = split_sql(DDL_SQL)
INSERT_STATEMENTS = split_sql(INSERT_SQL)
DROP_ORDER = ["Payment", "Proposal", "Project_Skill", "Project",
              "Freelancer_Skill", "Skill", "Freelancer", "Client"]
TABLES = list(reversed(DROP_ORDER))
EXPECTED_COUNTS = {"Client": 25, "Freelancer": 25, "Skill": 25, "Freelancer_Skill": 78,
                   "Project": 30, "Project_Skill": 72, "Proposal": 47, "Payment": 25}


# ----------------------------------------------------------------------------
# DATABASE LAYER
# ----------------------------------------------------------------------------
def adapt(sql, engine):
    """Translate MySQL syntax used in the report to SQLite where needed."""
    if engine == "mysql":
        return sql
    s = sql.strip().rstrip(";")
    s = re.sub(r"\s*ENGINE\s*=\s*InnoDB", "", s, flags=re.I)
    s = re.sub(r"^START TRANSACTION", "BEGIN", s, flags=re.I)
    s = re.sub(r"\s*WITH\s+CASCADED\s+CHECK\s+OPTION", "", s, flags=re.I)
    s = re.sub(r"^EXPLAIN\b", "EXPLAIN QUERY PLAN", s, flags=re.I)
    m = re.match(r"^DESCRIBE\s+(\w+)", s, flags=re.I)
    if m:
        s = f"PRAGMA table_info({m.group(1)})"
    s = re.sub(r"^CREATE INDEX (?!IF )", "CREATE INDEX IF NOT EXISTS ", s, flags=re.I)
    return s


def _conv(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", "replace")
    return v


class DB:
    def __init__(self, cfg, create_db=False):
        self.engine = cfg["engine"]
        if self.engine == "sqlite":
            self.con = sqlite3.connect(DB_PATH, isolation_level=None, timeout=5)
            self.con.execute("PRAGMA foreign_keys = ON")
        else:
            import mysql.connector
            kw = dict(host=cfg["host"], port=int(cfg["port"]), user=cfg["user"],
                      password=cfg["password"], autocommit=True, connection_timeout=5)
            if create_db:
                self.con = mysql.connector.connect(**kw)
                cur = self.con.cursor()
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}`")
                cur.execute(f"USE `{cfg['database']}`")
                cur.close()
            else:
                self.con = mysql.connector.connect(database=cfg["database"], **kw)

    def run(self, sql):
        """Execute one statement -> (DataFrame | None, rowcount, milliseconds)."""
        sql = adapt(sql, self.engine)
        cur = self.con.cursor()
        t0 = time.perf_counter()
        try:
            cur.execute(sql)
            df = None
            if cur.description:
                cols = []
                for description in cur.description:
                    cols.append(description[0])
                df = pd.DataFrame(cur.fetchall(), columns=cols)
                for c in df.columns:
                    df[c] = df[c].map(_conv)
            ms = (time.perf_counter() - t0) * 1000
            return df, cur.rowcount, ms
        finally:
            cur.close()

    def close(self):
        try:
            self.con.rollback()          # never leave a transaction hanging
        except Exception:
            pass
        try:
            self.con.close()
        except Exception:
            pass


def q(cfg, sql):
    """Run a read-only query on a fresh connection and return a DataFrame."""
    db = DB(cfg)
    try:
        df, _, _ = db.run(sql)
        return df
    finally:
        db.close()


def init_db(cfg):
    db = DB(cfg, create_db=True)
    try:
        if db.engine == "mysql":
            db.run("SET FOREIGN_KEY_CHECKS = 0")
        for v in ("ProposalDetails", "OpenProjects"):
            db.run(f"DROP VIEW IF EXISTS {v}")
        for t in DROP_ORDER:
            db.run(f"DROP TABLE IF EXISTS {t}")
        if db.engine == "mysql":
            db.run("SET FOREIGN_KEY_CHECKS = 1")
        for stmt in DDL_STATEMENTS + INSERT_STATEMENTS:
            db.run(stmt)
    finally:
        db.close()


def table_counts(cfg):
    db = DB(cfg)
    try:
        counts = {}
        for table in TABLES:
            result = db.run(f"SELECT COUNT(*) FROM {table}")
            counts[table] = int(result[0].iloc[0, 0])
        return counts
    finally:
        db.close()


# ----------------------------------------------------------------------------
# STEP ENGINE  (runs a list of statements on one session and records results)
# ----------------------------------------------------------------------------
def fmt(sql, cfg, ctx=None):
    out = sql.replace("{db}", cfg.get("database") or DEFAULT_DB)
    for k, v in (ctx or {}).items():
        out = out.replace("{" + k + "}", str(v))
    return out


def pick(x, cfg):
    return x[cfg["engine"]] if isinstance(x, dict) else x


def sql_step(label, sql, **kw):
    return dict(kind="sql", label=label, sql=sql, **kw)


def show_step(label, sql, **kw):
    return dict(kind="show", label=label, sql=sql, **kw)


def ctl_step(label, sql, **kw):
    return dict(kind="ctl", label=label, sql=sql, **kw)


def execute_steps(cfg, steps):
    results, main, other = [], None, None
    try:
        main = DB(cfg)
        for s in steps:
            r = dict(kind=s["kind"], label=s["label"], sql=s["sql"], echo=s.get("echo", False),
                     session=s.get("session", "main"), status="ok", msg="", df=None, rows=None, ms=0.0)
            try:
                conn = main
                if r["session"] == "other":
                    other = other or DB(cfg)
                    conn = other
                df, rc, ms = conn.run(s["sql"])
                r.update(df=df, rows=(len(df) if df is not None else rc), ms=ms)
                if s.get("expect_error"):
                    r["status"] = "unexpected_ok"
            except Exception as e:                      # noqa: BLE001
                msg = str(e)
                if s.get("expect_error"):
                    r.update(status="expected", msg=msg)
                elif s.get("soft") and any(w in msg.lower() for w in ("already exists", "duplicate")):
                    r.update(status="soft", msg=msg)
                else:
                    r.update(status="err", msg=msg)
                    results.append(r)
                    break
            results.append(r)
    except Exception as e:                              # noqa: BLE001  (connection problems)
        results.append(dict(kind="sql", label="Connection", sql="", echo=False, session="main",
                            status="err", msg=str(e), df=None, rows=None, ms=0.0))
    finally:
        for c in (main, other):
            if c:
                c.close()
    return results


def render_results(results):
    for r in results:
        rows = "" if (r["rows"] is None or r["rows"] < 0) else f" - {r['rows']} row(s)"
        who = " - second session" if r["session"] == "other" else ""
        if r["kind"] == "ctl":
            if r["status"] == "err":
                st.error(f"{r['label']} failed: {r['msg']}")
            else:
                st.caption(f"**{r['label']}** - `{r['sql']}` - {r['ms']:.1f} ms")
            continue
        if r["kind"] == "show":
            if r["status"] == "err":
                st.error(f"{r['label']} failed: {r['msg']}")
                continue
            st.markdown(f"**{r['label']}**{who}{rows} - {r['ms']:.1f} ms")
            if r["df"] is not None:
                st.dataframe(r["df"], hide_index=True)
            continue
        status_text = {
            "ok": "OK",
            "expected": "EXPECTED",
            "soft": "INFO",
            "unexpected_ok": "WARNING",
            "err": "ERROR",
        }[r["status"]]
        st.markdown(f"[{status_text}] **{r['label']}**{rows} - {r['ms']:.1f} ms")
        if r["echo"]:
            st.code(r["sql"], language="sql")
        if r["df"] is not None:
            st.dataframe(r["df"], hide_index=True)
        if r["status"] == "expected":
            st.success(f"Rejected by the database, as expected: {r['msg']}")
        elif r["status"] == "soft":
            st.info(f"Already applied earlier ({r['msg']}). Use Reset in the sidebar to start fresh.")
        elif r["status"] == "unexpected_ok":
            st.warning("This statement was expected to be rejected but it succeeded.")
        elif r["status"] == "err":
            st.error(r["msg"])


# ----------------------------------------------------------------------------
# QUERY CATALOGUE  (every statement in the report)
# ----------------------------------------------------------------------------
SHOW_VIEWS = {"mysql": "SHOW FULL TABLES WHERE Table_type = 'VIEW'",
              "sqlite": "SELECT name AS View_Name FROM sqlite_master WHERE type = 'view' ORDER BY name"}


def show_indexes(table):
    return {"mysql": f"SHOW INDEX FROM {table}", "sqlite": f"PRAGMA index_list({table})"}


Q18_SQL = """CREATE VIEW ProposalDetails AS
SELECT pr.ProposalID,
       f.FullName,
       p.Title,
       pr.BidAmount,
       pr.SubmittedDate,
       pr.Status
FROM Proposal pr
JOIN Freelancer f
    ON pr.FreelancerID = f.FreelancerID
JOIN Project p
    ON pr.ProjectID = p.ProjectID;

SELECT *
FROM ProposalDetails;

CREATE VIEW OpenProjects AS
SELECT ProjectID, ClientID, Title, Budget, Deadline
FROM Project
WHERE Status = 'Open'
WITH CASCADED CHECK OPTION;"""

Q18_VIEW1 = Q18_SQL.split(";")[0]
Q18_VIEW2 = Q18_SQL.split(";")[2].strip()


def steps_dml(show_sql, change_sql, expect_error=False):
    def build(ctx, cfg, persist):
        end = ("COMMIT  (changes kept)", "COMMIT") if persist else ("ROLLBACK  (preview only)", "ROLLBACK")
        return [show_step("Before", show_sql),
                ctl_step("Begin transaction", "START TRANSACTION"),
                sql_step("Execute statement", change_sql, echo=True, expect_error=expect_error),
                show_step("Inside the transaction", show_sql),
                ctl_step(end[0], end[1]),
                show_step("After", show_sql)]
    return build


def steps_q18(ctx, cfg, persist):
    return [ctl_step("Prep: drop old view (re-runnable)", "DROP VIEW IF EXISTS ProposalDetails"),
            sql_step("CREATE VIEW ProposalDetails", Q18_VIEW1),
            show_step("SELECT * FROM ProposalDetails", "SELECT * FROM ProposalDetails"),
            ctl_step("Prep: drop old view (re-runnable)", "DROP VIEW IF EXISTS OpenProjects"),
            sql_step("CREATE VIEW OpenProjects with CASCADED CHECK OPTION", Q18_VIEW2),
            show_step("SELECT * FROM OpenProjects", "SELECT * FROM OpenProjects")]


def steps_index(name, table, col):
    def build(ctx, cfg, persist):
        return [sql_step(f"CREATE INDEX {name}", f"CREATE INDEX {name} ON {table}({col})", soft=True),
                show_step(f"Indexes on {table}", show_indexes(table)[cfg["engine"]])]
    return build


def steps_explain(ctx, cfg, persist):
    return [sql_step("EXPLAIN", "EXPLAIN SELECT * FROM Project WHERE Deadline = '2026-12-20'")]


def steps_dcl(ctx, cfg, persist):
    u = "'freelance_user'@'localhost'"
    return [ctl_step("Prep: drop user if it exists", f"DROP USER IF EXISTS {u}"),
            ctl_step("Prep: make sure the view exists", "DROP VIEW IF EXISTS ProposalDetails"),
            ctl_step("Prep: recreate view", Q18_VIEW1),
            sql_step("CREATE USER", f"CREATE USER {u} IDENTIFIED BY 'ChangeThis_StrongPassword_123!'", echo=True),
            sql_step("GRANT SELECT on the view", f"GRANT SELECT ON {{db}}.ProposalDetails TO {u}", echo=True),
            sql_step("GRANT INSERT on Proposal", f"GRANT INSERT ON {{db}}.Proposal TO {u}", echo=True),
            show_step("SHOW GRANTS (after GRANT)", f"SHOW GRANTS FOR {u}"),
            sql_step("REVOKE INSERT", f"REVOKE INSERT ON {{db}}.Proposal FROM {u}", echo=True),
            show_step("SHOW GRANTS (after REVOKE)", f"SHOW GRANTS FOR {u}")]


def steps_q21(ctx, cfg, persist):
    s = "SELECT ProjectID, Title, Status FROM Project WHERE ProjectID = 26"
    return [show_step("Before", s),
            ctl_step("Begin", "START TRANSACTION"),
            sql_step("UPDATE", "UPDATE Project SET Status = 'In Progress' WHERE ProjectID = 26", echo=True),
            show_step("This session sees (uncommitted)", s),
            show_step("Another session sees (before COMMIT)", s, session="other"),
            ctl_step("COMMIT", "COMMIT"),
            show_step("Another session sees (after COMMIT)", s, session="other")]


def steps_q22(ctx, cfg, persist):
    s = "SELECT ProjectID, Title, Status FROM Project WHERE ProjectID = 1"
    return [show_step("Before", s),
            ctl_step("Begin", "START TRANSACTION"),
            sql_step("UPDATE", "UPDATE Project SET Status = 'Cancelled' WHERE ProjectID = 1", echo=True),
            show_step("This session sees (uncommitted)", s),
            ctl_step("ROLLBACK", "ROLLBACK"),
            show_step("After ROLLBACK (change undone)", s)]


def steps_q23(ctx, cfg, persist):
    s = "SELECT ProjectID, Title, Status FROM Project WHERE ProjectID IN (27, 28) ORDER BY ProjectID"
    return [show_step("Before", s),
            ctl_step("Begin", "START TRANSACTION"),
            sql_step("UPDATE project 27", "UPDATE Project SET Status = 'In Progress' WHERE ProjectID = 27", echo=True),
            ctl_step("SAVEPOINT", "SAVEPOINT BeforeSecondUpdate"),
            sql_step("UPDATE project 28", "UPDATE Project SET Status = 'Cancelled' WHERE ProjectID = 28", echo=True),
            show_step("Both updates applied (uncommitted)", s),
            ctl_step("ROLLBACK TO SAVEPOINT", "ROLLBACK TO SAVEPOINT BeforeSecondUpdate"),
            show_step("After ROLLBACK TO SAVEPOINT (28 restored, 27 kept)", s),
            ctl_step("COMMIT", "COMMIT"),
            show_step("Another session sees (after COMMIT)", s, session="other")]


def steps_q24(ctx, cfg, persist):
    s = "SELECT * FROM Proposal WHERE ProposalID = 48"
    return [show_step("Before (no proposal 48)", s),
            ctl_step("Begin", "START TRANSACTION"),
            sql_step("INSERT proposal 48",
                     "INSERT INTO Proposal (ProposalID, ProjectID, FreelancerID, BidAmount, SubmittedDate, Status) "
                     "VALUES (48, 29, 10, 96000.00, '2026-10-27', 'Pending')", echo=True),
            ctl_step("COMMIT", "COMMIT"),
            show_step("After", s)]


def steps_alter(ctx, cfg, persist):
    return [sql_step("ALTER TABLE", "ALTER TABLE Client ADD COLUMN Address VARCHAR(200)", soft=True),
            show_step("DESCRIBE Client", "DESCRIBE Client")]


def steps_dropview(ctx, cfg, persist):
    return [ctl_step("Prep: drop if present", "DROP VIEW IF EXISTS OpenProjects"),
            ctl_step("Prep: create view", Q18_VIEW2),
            show_step("Views before", SHOW_VIEWS[cfg["engine"]]),
            sql_step("DROP VIEW IF EXISTS OpenProjects", "DROP VIEW IF EXISTS OpenProjects"),
            show_step("Views after", SHOW_VIEWS[cfg["engine"]])]


ITEMS = [
    # ---- 8.4 DML ------------------------------------------------------------------
    dict(id="D1", sec="dml", section="8.4", title="UPDATE a freelancer's contact number", concept="UPDATE",
         sql="UPDATE Freelancer\nSET Phone = '9999999999'\nWHERE FreelancerID = 1;",
         steps=steps_dml("SELECT FreelancerID, FullName, Phone FROM Freelancer WHERE FreelancerID = 1",
                         "UPDATE Freelancer SET Phone = '9999999999' WHERE FreelancerID = 1")),
    dict(id="D2", sec="dml", section="8.4", title="UPDATE a proposal status", concept="UPDATE",
         sql="UPDATE Proposal\nSET Status = 'Accepted'\nWHERE ProposalID = 38;",
         steps=steps_dml("SELECT ProposalID, ProjectID, FreelancerID, Status FROM Proposal WHERE ProposalID = 38",
                         "UPDATE Proposal SET Status = 'Accepted' WHERE ProposalID = 38")),
    dict(id="D3", sec="dml", section="8.4", title="DELETE a payment record", concept="DELETE",
         sql="DELETE FROM Payment\nWHERE PaymentID = 5022;",
         steps=steps_dml("SELECT * FROM Payment WHERE PaymentID = 5022",
                         "DELETE FROM Payment WHERE PaymentID = 5022"),
         note="The proposal row stays: Payment references Proposal, not the other way round."),
    dict(id="D4", sec="dml", section="8.4", title="Referential integrity: delete a client that has projects",
         concept="FOREIGN KEY and ON DELETE RESTRICT",
         sql="-- This operation should fail while the client\n-- has associated projects.\nDELETE FROM Client\nWHERE ClientID = 1;",
         steps=steps_dml("SELECT c.ClientID, c.ClientName, (SELECT COUNT(*) FROM Project p WHERE p.ClientID = c.ClientID) AS Projects "
                         "FROM Client c WHERE c.ClientID = 1",
                         "DELETE FROM Client WHERE ClientID = 1", expect_error=True)),

    # ---- 9 DQL --------------------------------------------------------------------
    dict(id="Q1", sec="dql", section="9", title="Display all freelancers", concept="SELECT *", readonly=True,
         sql="SELECT * FROM Freelancer;"),
    dict(id="Q2", sec="dql", section="9", title="Retrieve open projects", concept="WHERE", readonly=True,
         sql="SELECT ProjectID, ClientID, Title, Budget\nFROM Project\nWHERE Status = 'Open';"),
    dict(id="Q3", sec="dql", section="9", title="Sort freelancers alphabetically", concept="ORDER BY", readonly=True,
         sql="SELECT FreelancerID, FullName\nFROM Freelancer\nORDER BY FullName ASC;"),
    dict(id="Q4", sec="dql", section="9", title="Display distinct project statuses", concept="DISTINCT", readonly=True,
         sql="SELECT DISTINCT Status\nFROM Project;"),
    dict(id="Q5", sec="dql", section="9", title="Count total freelancers", concept="COUNT", readonly=True,
         sql="SELECT COUNT(*) AS TotalFreelancers\nFROM Freelancer;"),
    dict(id="Q6", sec="dql", section="9", title="Calculate total paid amount", concept="SUM", readonly=True,
         sql="SELECT SUM(Amount) AS TotalPaidAmount\nFROM Payment\nWHERE PaymentStatus = 'Paid';"),
    dict(id="Q7", sec="dql", section="9", title="Calculate average payment amount", concept="AVG", readonly=True,
         sql="SELECT AVG(Amount) AS AveragePayment\nFROM Payment;"),
    dict(id="Q8", sec="dql", section="9", title="Find minimum and maximum payment amounts", concept="MIN / MAX",
         readonly=True,
         sql="SELECT MIN(Amount) AS MinimumAmount,\n       MAX(Amount) AS MaximumAmount\nFROM Payment;"),
    dict(id="Q9", sec="dql", section="9", title="Count proposals received by each project", concept="GROUP BY",
         readonly=True,
         sql="SELECT ProjectID, COUNT(*) AS ProposalCount\nFROM Proposal\nGROUP BY ProjectID;"),
    dict(id="Q10", sec="dql", section="9", title="Find projects with more than one proposal", concept="HAVING",
         readonly=True,
         sql="SELECT ProjectID, COUNT(*) AS ProposalCount\nFROM Proposal\nGROUP BY ProjectID\nHAVING COUNT(*) > 1;"),

    # ---- 10 Joins and subqueries ---------------------------------------------------
    dict(id="Q11", sec="join", section="10.1", title="Freelancer names with project titles and bid amounts",
         concept="INNER JOIN", readonly=True,
         sql="SELECT f.FullName, p.Title, pr.BidAmount\nFROM Freelancer f\nINNER JOIN Proposal pr\n    ON f.FreelancerID = pr.FreelancerID\nINNER JOIN Project p\n    ON pr.ProjectID = p.ProjectID;"),
    dict(id="Q12", sec="join", section="10.2", title="All clients, including those without projects",
         concept="LEFT OUTER JOIN", readonly=True,
         sql="SELECT c.ClientName, p.ProjectID\nFROM Client c\nLEFT JOIN Project p\n    ON c.ClientID = p.ClientID;"),
    dict(id="Q13", sec="join", section="10.3", title="Pairs of freelancers who live in the same city",
         concept="SELF JOIN", readonly=True,
         sql="SELECT f1.FullName AS Freelancer1,\n       f2.FullName AS Freelancer2,\n       f1.City\nFROM Freelancer f1\nJOIN Freelancer f2\n    ON f1.City = f2.City\n   AND f1.FreelancerID < f2.FreelancerID\nORDER BY f1.City;",
         note="Report: 23 pairs. The condition f1.FreelancerID < f2.FreelancerID makes each pair appear once."),
    dict(id="Q14", sec="join", section="10.4", title="Freelancers who proposed on projects posted by TechNova Solutions",
         concept="Nested subquery", readonly=True,
         sql="SELECT FullName\nFROM Freelancer\nWHERE FreelancerID IN (\n    SELECT FreelancerID\n    FROM Proposal\n    WHERE ProjectID IN (\n        SELECT ProjectID\n        FROM Project\n        WHERE ClientID = (\n            SELECT ClientID\n            FROM Client\n            WHERE ClientName = 'TechNova Solutions'\n        )\n    )\n);"),
    dict(id="Q15", sec="join", section="10.5", title="Payments greater than the average payment",
         concept="Single-row subquery", readonly=True,
         sql="SELECT PaymentID, ProposalID, Amount\nFROM Payment\nWHERE Amount > (\n    SELECT AVG(Amount)\n    FROM Payment\n);"),
    dict(id="Q16", sec="join", section="10.6", title="Freelancers who bid on projects with more than one proposal",
         concept="Multi-row subquery", readonly=True,
         sql="SELECT DISTINCT FullName\nFROM Freelancer\nWHERE FreelancerID IN (\n    SELECT FreelancerID\n    FROM Proposal\n    WHERE ProjectID IN (\n        SELECT ProjectID\n        FROM Proposal\n        GROUP BY ProjectID\n        HAVING COUNT(*) > 1\n    )\n);"),
    dict(id="Q17", sec="join", section="10.7", title="Freelancers who submitted at least one proposal",
         concept="Correlated subquery (EXISTS)", readonly=True,
         sql="SELECT f.FreelancerID, f.FullName\nFROM Freelancer f\nWHERE EXISTS (\n    SELECT 1\n    FROM Proposal pr\n    WHERE pr.FreelancerID = f.FreelancerID\n);"),

    # ---- 11 Views, indexes, DCL ---------------------------------------------------
    dict(id="Q18", sec="view", section="11.1", title="Create the ProposalDetails and OpenProjects views",
         concept="CREATE VIEW", sql=Q18_SQL, steps=steps_q18,
         note="SQLite has no CHECK OPTION, so it is dropped automatically in demo mode."),
    dict(id="Q19", sec="view", section="11.2", title="Create an index on the project deadline", concept="CREATE INDEX",
         sql="CREATE INDEX idx_project_deadline\nON Project(Deadline);",
         steps=steps_index("idx_project_deadline", "Project", "Deadline")),
    dict(id="Q20", sec="view", section="11.2", title="Create an index on the freelancer city", concept="CREATE INDEX",
         sql="CREATE INDEX idx_freelancer_city\nON Freelancer(City);",
         steps=steps_index("idx_freelancer_city", "Freelancer", "City")),
    dict(id="EXPLAIN", sec="view", section="11.2", title="Inspect the query execution plan", concept="EXPLAIN",
         sql="EXPLAIN\nSELECT *\nFROM Project\nWHERE Deadline = '2026-12-20';", steps=steps_explain, readonly=True,
         note="Run Q19 first: the plan should then use idx_project_deadline."),
    dict(id="DCL", sec="view", section="11.3", title="CREATE USER, GRANT, REVOKE, SHOW GRANTS", concept="DCL",
         mysql_only=True,
         sql="CREATE USER 'freelance_user'@'localhost'\nIDENTIFIED BY 'ChangeThis_StrongPassword_123!';\n\nGRANT SELECT\nON FreelancerDB.ProposalDetails\nTO 'freelance_user'@'localhost';\n\nGRANT INSERT\nON FreelancerDB.Proposal\nTO 'freelance_user'@'localhost';\n\nREVOKE INSERT\nON FreelancerDB.Proposal\nFROM 'freelance_user'@'localhost';\n\nSHOW GRANTS FOR 'freelance_user'@'localhost';",
         steps=steps_dcl, warn="Needs a MySQL account with CREATE USER and GRANT OPTION (for example root)."),

    # ---- 12 TCL -------------------------------------------------------------------
    dict(id="Q21", sec="tcl", section="12.1", title="Update a project status and COMMIT", concept="COMMIT",
         sql="START TRANSACTION;\nUPDATE Project\nSET Status = 'In Progress'\nWHERE ProjectID = 26;\nCOMMIT;",
         steps=steps_q21, warn="Permanent: this really commits. Use Reset in the sidebar to restore the sample data."),
    dict(id="Q22", sec="tcl", section="12.2", title="Demonstrate ROLLBACK", concept="ROLLBACK",
         sql="START TRANSACTION;\nUPDATE Project\nSET Status = 'Cancelled'\nWHERE ProjectID = 1;\nROLLBACK;",
         steps=steps_q22),
    dict(id="Q23", sec="tcl", section="12.3", title="Partial rollback with a SAVEPOINT", concept="SAVEPOINT",
         sql="START TRANSACTION;\nUPDATE Project\nSET Status = 'In Progress'\nWHERE ProjectID = 27;\nSAVEPOINT BeforeSecondUpdate;\nUPDATE Project\nSET Status = 'Cancelled'\nWHERE ProjectID = 28;\nROLLBACK TO SAVEPOINT BeforeSecondUpdate;\nCOMMIT;",
         steps=steps_q23, warn="Permanent: project 27 stays 'In Progress'. Use Reset in the sidebar to restore the sample data."),
    dict(id="Q24", sec="tcl", section="12.4", title="Insert a proposal inside a transaction", concept="Transactional INSERT",
         sql="START TRANSACTION;\nINSERT INTO Proposal\n(ProposalID, ProjectID, FreelancerID, BidAmount,\n SubmittedDate, Status)\nVALUES\n(48, 29, 10, 96000.00, '2026-10-27', 'Pending');\nCOMMIT;",
         steps=steps_q24, warn="Permanent: running it twice fails with a duplicate key. Use Reset to repeat it."),

    # ---- 13 Additional operations -------------------------------------------------
    dict(id="13.1", sec="extra", section="13.1", title="Accepted proposals without a successful payment",
         concept="LEFT JOIN + IS NULL", readonly=True,
         sql="SELECT pr.ProposalID, pr.Status\nFROM Proposal pr\nLEFT JOIN Payment p\n    ON pr.ProposalID = p.ProposalID\nWHERE pr.Status = 'Accepted'\n  AND (p.PaymentID IS NULL\n   OR p.PaymentStatus <> 'Paid');"),
    dict(id="13.2", sec="extra", section="13.2", title="Payment summary by payment method", concept="GROUP BY + SUM",
         readonly=True,
         sql="SELECT PaymentMethod,\n       COUNT(*) AS TotalTransactions,\n       SUM(Amount) AS TotalAmount\nFROM Payment\nGROUP BY PaymentMethod;"),
    dict(id="13.3", sec="extra", section="13.3", title="Clients with more than one project", concept="JOIN + HAVING",
         readonly=True,
         sql="SELECT c.ClientID, c.ClientName,\n       COUNT(p.ProjectID) AS TotalProjects\nFROM Client c\nJOIN Project p\n    ON c.ClientID = p.ClientID\nGROUP BY c.ClientID, c.ClientName\nHAVING COUNT(p.ProjectID) > 1;"),
    dict(id="13.4", sec="extra", section="13.4", title="All skills of a particular freelancer", concept="Multi-table JOIN",
         readonly=True, params=("email",),
         sql="SELECT f.FullName, s.SkillName, fs.ProficiencyLevel\nFROM Freelancer_Skill fs\nJOIN Freelancer f\n    ON fs.FreelancerID = f.FreelancerID\nJOIN Skill s\n    ON fs.SkillID = s.SkillID\nWHERE f.Email = '{email}'\nORDER BY s.SkillName;"),
    dict(id="13.5", sec="extra", section="13.5", title="Alter a table", concept="ALTER TABLE",
         sql="ALTER TABLE Client\nADD COLUMN Address VARCHAR(200);", steps=steps_alter),
    dict(id="13.6", sec="extra", section="13.6", title="Delete a view", concept="DROP VIEW",
         sql="DROP VIEW IF EXISTS OpenProjects;", steps=steps_dropview),
    dict(id="13.7", sec="extra", section="13.7", title="Inspect table structure", concept="DESCRIBE", readonly=True,
         sql="DESCRIBE Proposal;"),
    dict(id="13.8", sec="extra", section="13.8", title="Inspect database records", concept="COUNT", readonly=True,
         sql="SELECT COUNT(*) AS TotalProposals\nFROM Proposal;"),
    dict(id="13.9", sec="extra", section="13.9", title="Match freelancers to an open project by skills",
         concept="Skill-based matching (ranked)", readonly=True, params=("pid",),
         sql="SELECT f.FreelancerID, f.FullName,\n       COUNT(ps.SkillID) AS MatchedSkills,\n       (SELECT COUNT(*)\n        FROM Project_Skill\n        WHERE ProjectID = {pid}) AS RequiredSkills,\n       f.Rating\nFROM Freelancer f\nJOIN Freelancer_Skill fs\n    ON f.FreelancerID = fs.FreelancerID\nJOIN Project_Skill ps\n    ON fs.SkillID = ps.SkillID\n   AND ps.ProjectID = {pid}\nGROUP BY f.FreelancerID, f.FullName, f.Rating\nORDER BY MatchedSkills DESC, f.Rating DESC;"),
    dict(id="13.10", sec="extra", section="13.10", title="Freelancers who match ALL required skills of a project",
         concept="Skill-based matching (exact)", readonly=True, params=("pid",),
         sql="SELECT f.FreelancerID, f.FullName, f.HourlyRate\nFROM Freelancer f\nJOIN Freelancer_Skill fs\n    ON f.FreelancerID = fs.FreelancerID\nJOIN Project_Skill ps\n    ON fs.SkillID = ps.SkillID\nWHERE ps.ProjectID = {pid}\nGROUP BY f.FreelancerID, f.FullName, f.HourlyRate\nHAVING COUNT(DISTINCT ps.SkillID) = (\n    SELECT COUNT(*)\n    FROM Project_Skill\n    WHERE ProjectID = {pid}\n);",
         note="Report: for Project 26 only Nikhil Chavan matches all three skills."),
]

DEFAULT_CTX = {"pid": 26, "email": "nikhil.chavan@example.com"}


def render_params(item, cfg):
    ctx = {}
    for p in item.get("params", ()):
        if p == "pid":
            df = q(cfg, "SELECT ProjectID, Title, Status FROM Project ORDER BY ProjectID")
            labels = {}
            for row in df.itertuples():
                labels[int(row.ProjectID)] = f"{row.ProjectID} - {row.Title} ({row.Status})"
            ids = list(labels)
            project_index = ids.index(26) if 26 in ids else 0
            ctx["pid"] = st.selectbox(
                "Project",
                ids,
                index=project_index,
                format_func=labels.get,
                key=f"p_{item['id']}",
            )
        elif p == "email":
            df = q(cfg, "SELECT FullName, Email FROM Freelancer ORDER BY FullName")
            labels = dict(zip(df.Email, df.FullName + " - " + df.Email))
            emails = list(labels)
            default = emails.index(DEFAULT_CTX["email"]) if DEFAULT_CTX["email"] in emails else 0
            ctx["email"] = st.selectbox(
                "Freelancer",
                emails,
                index=default,
                format_func=labels.get,
                key=f"p_{item['id']}",
            )
    return ctx


def build_steps(item, cfg, ctx, persist):
    if item.get("steps"):
        raw = item["steps"](ctx, cfg, persist)
    else:
        raw = [sql_step("Result", item["sql"])]
    steps = []
    for step in raw:
        steps.append(dict(step, sql=fmt(pick(step["sql"], cfg), cfg, ctx)))
    return steps


def render_item(item, cfg, persist=False):
    with st.container(border=True):
        st.markdown(f"##### {item['id']} - {item['title']}")
        st.markdown(f"**Concept:** `{item['concept']}`  -  **Report section {item['section']}**")
        ctx = render_params(item, cfg)
        st.code(fmt(item["sql"], cfg, ctx), language="sql")
        if item.get("mysql_only") and cfg["engine"] != "mysql":
            st.warning("SQLite has no users or privileges, so GRANT / REVOKE / SHOW GRANTS only run on MySQL. "
                       "Switch the engine in the sidebar to execute this one.")
            return
        steps = build_steps(item, cfg, ctx, persist)
        if item.get("readonly"):
            results = execute_steps(cfg, steps)
        else:
            if item.get("warn"):
                st.caption(f"Warning: {item['warn']}")
            if st.button("Run", key=f"run_{item['id']}"):
                st.session_state.res[item["id"]] = execute_steps(cfg, steps)
            results = st.session_state.res.get(item["id"])
        if results:
            render_results(results)
        if item.get("note"):
            st.caption(f"Note: {item['note']}")


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
st.session_state.setdefault("res", {})

with st.sidebar:
    st.title("Freelancer DBMS")
    st.caption("Freelancer Project Matching and Management - SQL execution dashboard")
    engine_label = st.radio("Database engine", ["SQLite (demo, no setup)", "MySQL"],
                            help="MySQL is the engine used in the report. SQLite needs no installation.")
    cfg = {"engine": "mysql" if engine_label == "MySQL" else "sqlite"}
    if cfg["engine"] == "mysql":
        cfg["host"] = st.text_input("Host", os.getenv("MYSQL_HOST", "localhost"))
        cfg["port"] = st.text_input("Port", os.getenv("MYSQL_PORT", "3306"))
        cfg["user"] = st.text_input("User", os.getenv("MYSQL_USER", "root"))
        cfg["password"] = st.text_input("Password", os.getenv("MYSQL_PASSWORD", ""), type="password")
        cfg["database"] = st.text_input("Database", os.getenv("MYSQL_DATABASE", DEFAULT_DB))
    else:
        cfg["database"] = DEFAULT_DB
        st.caption(f"Data file: `{DB_PATH.name}` (created automatically)")

    if st.button("Initialize / Reset sample database", type="primary"):
        try:
            init_db(cfg)
            st.session_state.res = {}
            st.success("Database recreated with the sample data from the report.")
        except Exception as e:                           # noqa: BLE001
            st.error(f"Could not initialize: {e}")

    st.divider()
    SECTIONS = {
        "overview": "Dashboard overview",
        "schema": "Schema and data",
        "dml": "DML: UPDATE / DELETE (8.4)",
        "dql": "DQL: Queries 1-10 (9)",
        "join": "Joins and subqueries: 11-17 (10)",
        "view": "Views, indexes, DCL: 18-20 (11)",
        "tcl": "Transactions: 21-24 (12)",
        "extra": "Additional operations (13)",
        "test": "Testing and verification (14-15)",
        "play": "SQL playground",
    }
    section = st.radio("Section", list(SECTIONS), format_func=SECTIONS.get)

# ----------------------------------------------------------------------------
# GUARD: make sure the database is reachable and populated
# ----------------------------------------------------------------------------
try:
    counts = table_counts(cfg)
except Exception as e:                                   # noqa: BLE001
    st.title("Freelancer Project Matching and Management")
    msg = str(e).lower()
    if "no such table" in msg or "doesn't exist" in msg or "unknown database" in msg:
        st.info("Welcome! Click **Initialize / Reset sample database** in the sidebar to create the sample "
                "database from the report.")
    else:
        st.warning(f"Could not read the database: {e}")
        st.info("For MySQL, check that the server is running and that host, user and password are correct, "
                "then click **Initialize / Reset sample database**.")
    st.stop()


# ----------------------------------------------------------------------------
# SECTIONS
# ----------------------------------------------------------------------------
def page_overview():
    st.title("Freelancer Project Matching and Management")
    k = q(cfg, """SELECT
        (SELECT COUNT(*) FROM Client) AS Clients,
        (SELECT COUNT(*) FROM Freelancer) AS Freelancers,
        (SELECT COUNT(*) FROM Project) AS Projects,
        (SELECT COUNT(*) FROM Proposal) AS Proposals,
        (SELECT COALESCE(SUM(Amount), 0) FROM Payment WHERE PaymentStatus = 'Paid') AS TotalPaid""").iloc[0]
    c = st.columns(5)
    c[0].metric("Clients", int(k.Clients))
    c[1].metric("Freelancers", int(k.Freelancers))
    c[2].metric("Projects", int(k.Projects))
    c[3].metric("Proposals", int(k.Proposals))
    c[4].metric("Total paid", f"{k.TotalPaid:,.0f}")

    r1 = st.columns(3)
    with r1[0]:
        st.subheader("Projects by status")
        st.bar_chart(q(cfg, "SELECT Status, COUNT(*) AS Projects FROM Project GROUP BY Status").set_index("Status"))
    with r1[1]:
        st.subheader("Proposals by status")
        st.bar_chart(q(cfg, "SELECT Status, COUNT(*) AS Proposals FROM Proposal GROUP BY Status").set_index("Status"))
    with r1[2]:
        st.subheader("Paid amount by method")
        st.bar_chart(q(cfg, "SELECT PaymentMethod, SUM(Amount) AS Paid FROM Payment "
                            "WHERE PaymentStatus = 'Paid' GROUP BY PaymentMethod").set_index("PaymentMethod"))
    r2 = st.columns(3)
    with r2[0]:
        st.subheader("Freelancers by city")
        st.bar_chart(q(cfg, "SELECT City, COUNT(*) AS Freelancers FROM Freelancer GROUP BY City "
                            "ORDER BY Freelancers DESC").set_index("City"))
    with r2[1]:
        st.subheader("Skill demand vs supply (top 10)")
        st.bar_chart(q(cfg, """SELECT s.SkillName,
            (SELECT COUNT(*) FROM Project_Skill ps WHERE ps.SkillID = s.SkillID) AS Demand,
            (SELECT COUNT(*) FROM Freelancer_Skill fs WHERE fs.SkillID = s.SkillID) AS Supply
            FROM Skill s ORDER BY Demand DESC, Supply DESC LIMIT 10""").set_index("SkillName"))
    with r2[2]:
        st.subheader("Top earners (paid)")
        st.bar_chart(q(cfg, """SELECT f.FullName, SUM(p.Amount) AS Earned
            FROM Payment p JOIN Proposal pr ON p.ProposalID = pr.ProposalID
            JOIN Freelancer f ON pr.FreelancerID = f.FreelancerID
            WHERE p.PaymentStatus = 'Paid' GROUP BY f.FullName
            ORDER BY Earned DESC LIMIT 8""").set_index("FullName"))
    st.caption("Every chart on this page is itself produced by a SQL query against the live database.")


ER_DOT = """digraph ER {
  rankdir=LR; node [shape=record, fontname="Helvetica", fontsize=10]; edge [fontname="Helvetica", fontsize=9];
  Client [label="{Client|ClientID (PK)\\lClientName\\lEmail\\lPhone\\lCity\\l}"];
  Project [label="{Project|ProjectID (PK)\\lClientID (FK)\\lTitle\\lBudget\\lPostedDate\\lDeadline\\lStatus\\l}"];
  Proposal [label="{Proposal|ProposalID (PK)\\lProjectID (FK)\\lFreelancerID (FK)\\lBidAmount\\lSubmittedDate\\lStatus\\l}"];
  Payment [label="{Payment|PaymentID (PK)\\lProposalID (FK, unique)\\lAmount\\lPaymentDate\\lPaymentMethod\\lPaymentStatus\\l}"];
  Freelancer [label="{Freelancer|FreelancerID (PK)\\lFullName\\lEmail\\lPhone\\lCity\\lHourlyRate\\lExperienceYears\\lRating\\l}"];
  Skill [label="{Skill|SkillID (PK)\\lSkillName\\lCategory\\l}"];
  Freelancer_Skill [label="{Freelancer_Skill|FreelancerID (PK, FK)\\lSkillID (PK, FK)\\lProficiencyLevel\\l}"];
  Project_Skill [label="{Project_Skill|ProjectID (PK, FK)\\lSkillID (PK, FK)\\lRequiredLevel\\l}"];
  Client -> Project [label="1:N"]; Project -> Proposal [label="1:N"]; Freelancer -> Proposal [label="1:N"];
  Proposal -> Payment [label="1:0..1"]; Freelancer -> Freelancer_Skill [label="1:N"]; Skill -> Freelancer_Skill [label="1:N"];
  Project -> Project_Skill [label="1:N"]; Skill -> Project_Skill [label="1:N"];
}"""


def page_schema():
    st.title("Schema and data")
    st.subheader("Entity relationship diagram")
    st.graphviz_chart(ER_DOT)
    st.subheader("Browse tables")
    t = st.selectbox("Table", TABLES)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.dataframe(q(cfg, f"SELECT * FROM {t}"), hide_index=True)
    with c2:
        st.markdown("**Structure**")
        st.dataframe(q(cfg, f"DESCRIBE {t}"), hide_index=True)
    with st.expander("CREATE TABLE statements (report 8.2)"):
        st.code(DDL_SQL, language="sql")


def page_items(sec, title, intro, persist_toggle=False):
    st.title(title)
    st.write(intro)
    persist = False
    if persist_toggle:
        persist = st.toggle("Keep the changes (COMMIT). Off = run, show the effect, then ROLLBACK", value=False)
    for item in ITEMS:
        if item["sec"] == sec:
            render_item(item, cfg, persist)


def page_test():
    st.title("Testing and verification")
    st.subheader("Row counts (report 14)")
    count_rows = []
    for table in TABLES:
        count_rows.append({
            "Table": table,
            "Expected": EXPECTED_COUNTS[table],
            "Actual": counts[table],
            "Status": "OK" if counts[table] == EXPECTED_COUNTS[table] else "differs",
        })
    df = pd.DataFrame(count_rows)
    st.dataframe(df, hide_index=True)
    st.caption("Counts differ after you COMMIT Q24 (a 48th proposal) or the D3 delete. Reset restores them.")

    st.subheader("Aggregate checks (report 14)")
    a = q(cfg, """SELECT
        (SELECT COUNT(*) FROM Freelancer) AS Freelancers,
        (SELECT SUM(Amount) FROM Payment WHERE PaymentStatus = 'Paid') AS TotalPaid,
        (SELECT AVG(Amount) FROM Payment) AS AvgPayment,
        (SELECT MIN(Amount) FROM Payment) AS MinPayment,
        (SELECT MAX(Amount) FROM Payment) AS MaxPayment""").iloc[0]
    pairs = int(q(cfg, "SELECT COUNT(*) FROM Freelancer f1 JOIN Freelancer f2 ON f1.City = f2.City "
                       "AND f1.FreelancerID < f2.FreelancerID").iloc[0, 0])
    exp = [("Freelancers", 25, a.Freelancers), ("Total paid amount", 962500, a.TotalPaid),
           ("Average payment (after D3 delete)", 47875, a.AvgPayment), ("Minimum payment", 5500, a.MinPayment),
           ("Maximum payment", 112000, a.MaxPayment), ("Same-city freelancer pairs", 23, pairs)]
    st.dataframe(pd.DataFrame([{"Check": n, "Expected": e, "Actual": float(v),
                                "Status": "OK" if abs(float(v) - e) < 0.01 else
                                ("persist D3 (COMMIT) first" if "after D3" in n else "differs")}
                               for n, e, v in exp]),
                 hide_index=True)
    st.caption("The report derives its average from the data after the 8.4 DELETE. Persist D3 (COMMIT) to get 47,875.")

    st.subheader("Run all read-only queries")
    if st.button("Run every SELECT query (smoke test)"):
        rows = []
        for item in ITEMS:
            if not item.get("readonly"):
                continue
            res = execute_steps(cfg, build_steps(item, cfg, DEFAULT_CTX, False))
            last = res[-1]
            ok = all(r["status"] in ("ok", "soft") for r in res)
            rows.append({"Query": item["id"], "Title": item["title"], "Concept": item["concept"],
                         "Rows": last["rows"], "Time (ms)": round(sum(r["ms"] for r in res), 2),
                         "Status": "OK" if ok else f"ERROR: {last['msg']}"})
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.subheader("Constraint test cases (report 15, TC01-TC07)")
    st.caption("Each test runs inside a transaction and is rolled back, so your data is never changed.")
    tests = [
        ("TC01", "Insert a valid freelancer", "Record inserted successfully", False,
         "INSERT INTO Freelancer VALUES (26, 'Test Freelancer', 'test.freelancer@example.com', '9000000000', 'Pune', 500.00, 1, 4.0)"),
        ("TC02", "Insert a duplicate FreelancerID", "Primary key violation", True,
         "INSERT INTO Freelancer VALUES (1, 'Dup Id', 'dup.id@example.com', '9000000001', 'Pune', 500.00, 1, 4.0)"),
        ("TC03", "Insert a duplicate email", "Unique constraint violation", True,
         "INSERT INTO Freelancer VALUES (27, 'Dup Email', 'aarav.mehta@example.com', '9000000002', 'Pune', 500.00, 1, 4.0)"),
        ("TC04", "Proposal for a nonexistent freelancer", "Foreign key violation", True,
         "INSERT INTO Proposal VALUES (99, 26, 999, 50000.00, '2026-10-30', 'Pending')"),
        ("TC05", "Insert a negative bid amount", "Check constraint violation", True,
         "INSERT INTO Proposal VALUES (99, 30, 1, -100.00, '2026-10-30', 'Pending')"),
        ("TC06", "Two proposals by the same freelancer for the same project", "Unique constraint violation", True,
         "INSERT INTO Proposal VALUES (99, 26, 1, 66000.00, '2026-10-30', 'Pending')"),
        ("TC07", "Delete a client having projects", "Deletion restricted", True,
         "DELETE FROM Client WHERE ClientID = 1"),
    ]
    if st.button("Run test cases TC01-TC07"):
        out = []
        for tc, proc, expected, must_fail, stmt in tests:
            res = execute_steps(cfg, [ctl_step("begin", "START TRANSACTION"),
                                      sql_step("test", stmt, expect_error=must_fail),
                                      ctl_step("rollback", "ROLLBACK")])
            t = next((r for r in res if r["label"] == "test"), None)
            passed = t is not None and t["status"] in ("ok", "expected") and (t["status"] == "expected") == must_fail
            out.append({"Test": tc, "Procedure": proc, "Expected": expected,
                        "Actual": (t["msg"] if t and t["msg"] else "Inserted (rolled back afterwards)") if t else "n/a",
                        "Result": "PASS" if passed else "FAIL"})
        st.dataframe(pd.DataFrame(out), hide_index=True)
    st.caption("TC08-TC15 (joins, aggregates, views, COMMIT / ROLLBACK / SAVEPOINT, REVOKE, skill matching) "
               "are demonstrated live in the other sections.")


def page_play():
    st.title("SQL playground")
    st.caption("Read-only: SELECT, WITH, EXPLAIN, DESCRIBE and SHOW statements.")
    sql = st.text_area("SQL", "SELECT f.FullName, COUNT(*) AS Skills\nFROM Freelancer f\nJOIN Freelancer_Skill fs ON f.FreelancerID = fs.FreelancerID\nGROUP BY f.FullName\nORDER BY Skills DESC;",
                       height=160)
    if st.button("Run"):
        s = sql.strip().rstrip(";")
        if ";" in s or not re.match(r"^(select|with|explain|describe|show|pragma)\b", s, flags=re.I):
            st.error("Only a single read-only statement is allowed here.")
        else:
            render_results(execute_steps(cfg, [sql_step("Result", s)]))


if section == "overview":
    page_overview()
elif section == "schema":
    page_schema()
elif section == "dml":
    page_items("dml", "DML: UPDATE and DELETE (8.4)",
               "Each statement runs inside a transaction so you can see the row before, during and after.",
               persist_toggle=True)
elif section == "dql":
    page_items("dql", "Data extraction with DQL (9)",
               "SELECT, WHERE, ORDER BY, DISTINCT, aggregates, GROUP BY and HAVING. Results run live.")
elif section == "join":
    page_items("join", "Joins and subqueries (10)",
               "INNER / LEFT / SELF joins plus nested, single-row, multi-row and correlated subqueries.")
elif section == "view":
    page_items("view", "Views, indexing and access control (11)",
               "Press Run on each card. Q19 and Q20 are re-runnable; DCL needs MySQL.")
elif section == "tcl":
    page_items("tcl", "Transaction management with TCL (12)",
               "Watch COMMIT, ROLLBACK and SAVEPOINT work, including what a second session can see.")
elif section == "extra":
    page_items("extra", "Additional SQL operations (13)",
               "Reports, ALTER / DROP VIEW / DESCRIBE, and the skill-based matching queries. "
               "Pick any project or freelancer with the dropdowns.")
elif section == "test":
    page_test()
else:
    page_play()
