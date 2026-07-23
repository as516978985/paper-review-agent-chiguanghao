-- 数据库和用户初始化脚本
-- 注意：密码请替换为实际值，不要使用硬编码密码
-- 如果使用 Docker Compose 部署，MySQL 服务会自动从 .env 读取 MYSQL_USER 和 MYSQL_PASSWORD

-- 创建主机访问用户（请替换 YOUR_PASSWORD_HERE 为实际密码）
CREATE USER IF NOT EXISTS 'paper_review_agent'@'127.0.0.1'
  IDENTIFIED BY 'YOUR_PASSWORD_HERE';
CREATE USER IF NOT EXISTS 'paper_review_agent'@'localhost'
  IDENTIFIED BY 'YOUR_PASSWORD_HERE';
CREATE USER IF NOT EXISTS 'paper_review_agent'@'%'
  IDENTIFIED BY 'YOUR_PASSWORD_HERE';

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