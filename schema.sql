-- =====================================================================
-- Job Application Tracker - Database Creation Script
-- Run with:  mysql -u root -p < schema.sql
-- WARNING: this drops and recreates the job_tracker database.
-- =====================================================================

DROP DATABASE IF EXISTS job_tracker;
CREATE DATABASE job_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE job_tracker;

-- ---------------------------------------------------------------------
-- companies: organizations I am interested in / applying to
-- ---------------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    CONSTRAINT uq_company_name UNIQUE (company_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- jobs: specific openings posted by a company
-- requirements JSON example:
--   {"skills": ["Python", "SQL"], "experience_years": 2, "education": "Bachelor's"}
-- ---------------------------------------------------------------------
CREATE TABLE jobs (
    job_id       INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time','Part-time','Contract','Internship') DEFAULT 'Full-time',
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    CONSTRAINT fk_jobs_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_salary_range CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max),
    CONSTRAINT chk_salary_positive CHECK ((salary_min IS NULL OR salary_min >= 0) AND (salary_max IS NULL OR salary_max >= 0))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- applications: my application to a specific job
-- interview_data JSON example:
--   {"interviews": [{"date": "2026-10-02", "type": "Phone Screen",
--                    "interviewer": "Jane Doe", "notes": "Went well"}]}
-- ---------------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT PRIMARY KEY AUTO_INCREMENT,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn') NOT NULL DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE,
    interview_data    JSON,
    CONSTRAINT fk_applications_job FOREIGN KEY (job_id)
        REFERENCES jobs(job_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- contacts: people I know / have talked to at a company
-- ---------------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    CONSTRAINT fk_contacts_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Indexes on foreign keys / common filters
CREATE INDEX idx_jobs_company        ON jobs(company_id);
CREATE INDEX idx_applications_job    ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_contacts_company    ON contacts(company_id);

-- =====================================================================
-- Sample data
-- =====================================================================
INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp',        'Software',      'https://www.techcorp.example.com',   'Miami',         'FL', 'Fast-growing SaaS company. Great benefits.'),
('DataCo',          'Analytics',     'https://www.dataco.example.com',     'Orlando',       'FL', 'Data consulting firm with many entry-level roles.'),
('CloudNine',       'Cloud Services','https://www.cloudnine.example.com',  'Austin',        'TX', 'Remote-friendly; met recruiter at career fair.'),
('FinServe Bank',   'Finance',       'https://www.finserve.example.com',   'New York',      'NY', 'Large bank with a strong internship program.'),
('HealthBridge',    'Healthcare',    'https://www.healthbridge.example.com','Tampa',        'FL', NULL),
('GreenGrid Energy','Energy',        'https://www.greengrid.example.com',  'Denver',        'CO', 'Renewable energy startup.');

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer',        'Full-time',  75000, 95000, 'https://www.techcorp.example.com/careers/101', '2026-09-01',
    '{"skills": ["Python", "SQL", "Flask"], "experience_years": 1, "education": "Bachelor''s"}'),
(2, 'Data Analyst',              'Full-time',  60000, 80000, 'https://www.dataco.example.com/jobs/22',       '2026-09-05',
    '{"skills": ["Python", "SQL", "Tableau"], "experience_years": 0, "education": "Bachelor''s"}'),
(3, 'Cloud Engineer Intern',     'Internship', 25000, 32000, 'https://www.cloudnine.example.com/jobs/7',     '2026-09-10',
    '{"skills": ["AWS", "Linux", "Python", "Docker"], "experience_years": 0, "education": "In progress"}'),
(4, 'Junior Java Developer',     'Full-time',  70000, 88000, 'https://www.finserve.example.com/careers/55',  '2026-08-20',
    '{"skills": ["Java", "Spring", "SQL", "Git"], "experience_years": 1, "education": "Bachelor''s"}'),
(5, 'Database Administrator',    'Contract',   65000, 85000, 'https://www.healthbridge.example.com/jobs/3',  '2026-09-15',
    '{"skills": ["MySQL", "SQL", "Linux", "Backup and Recovery"], "experience_years": 2, "education": "Bachelor''s"}'),
(6, 'Front-End Developer',       'Part-time',  30000, 45000, 'https://www.greengrid.example.com/jobs/12',    '2026-09-20',
    '{"skills": ["HTML", "CSS", "JavaScript", "React"], "experience_years": 0, "education": "Any"}'),
(1, 'QA Automation Engineer',    'Full-time',  68000, 82000, 'https://www.techcorp.example.com/careers/114', '2026-10-01',
    '{"skills": ["Python", "Selenium", "Git"], "experience_years": 1, "education": "Bachelor''s"}');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-09-03', 'Interview', 'v3-software', TRUE,
    '{"interviews": [{"date": "2026-09-12", "type": "Phone Screen", "interviewer": "Maria Lopez", "notes": "Talked about my Flask project."},
                     {"date": "2026-12-02", "type": "Technical", "interviewer": "Kevin Chen", "notes": "Prepare SQL joins and Python questions."}]}'),
(2, '2026-09-07', 'Screening', 'v2-data', FALSE,
    '{"interviews": [{"date": "2026-09-18", "type": "Recruiter Call", "interviewer": "Priya Patel", "notes": "Asked about Tableau experience."}]}'),
(3, '2026-09-12', 'Applied',   'v3-software', TRUE,  '{"interviews": []}'),
(4, '2026-08-25', 'Rejected',  'v1-general',  FALSE, '{"interviews": []}'),
(6, '2026-09-22', 'Offer',     'v3-software', TRUE,
    '{"interviews": [{"date": "2026-10-01", "type": "Onsite", "interviewer": "Sam Rivera", "notes": "Built a small React component live."}]}'),
(7, '2026-10-03', 'Withdrawn', 'v3-software', FALSE, '{"interviews": []}');

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Maria Lopez',  'Technical Recruiter',   'maria.lopez@techcorp.example.com', '305-555-0101', 'https://www.linkedin.com/in/maria-lopez-example', 'Very responsive over email.'),
(1, 'Kevin Chen',   'Engineering Manager',   'kevin.chen@techcorp.example.com',  '305-555-0102', NULL, 'Will run the technical interview.'),
(2, 'Priya Patel',  'Talent Acquisition',    'priya@dataco.example.com',         '407-555-0199', 'https://www.linkedin.com/in/priya-patel-example', NULL),
(3, 'Jordan Smith', 'University Recruiter',  'jsmith@cloudnine.example.com',     NULL,           'https://www.linkedin.com/in/jordan-smith-example', 'Met at the FIU career fair.'),
(6, 'Sam Rivera',   'Lead Front-End Developer','sam.rivera@greengrid.example.com','720-555-0123', NULL, 'Sent thank-you email after onsite.');
