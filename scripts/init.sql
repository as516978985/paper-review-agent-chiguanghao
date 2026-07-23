-- 数据库和用户已由环境变量创建，这里补充权限和额外 host 的用户
CREATE USER IF NOT EXISTS 'paper_review_agent'@'127.0.0.1' IDENTIFIED BY 'PaperReview_2026';
CREATE USER IF NOT EXISTS 'paper_review_agent'@'localhost' IDENTIFIED BY 'PaperReview_2026';

GRANT SELECT, INSERT, UPDATE, CREATE, INDEX
  ON paper_review_agent.*
  TO 'paper_review_agent'@'%';

GRANT ALL PRIVILEGES
  ON paper_review_agent.*
  TO 'paper_review_agent'@'127.0.0.1';

GRANT ALL PRIVILEGES
  ON paper_review_agent.*
  TO 'paper_review_agent'@'localhost';

FLUSH PRIVILEGES;