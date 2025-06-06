-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_pose_gallery CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建应用用户
CREATE USER IF NOT EXISTS 'aipose'@'%' IDENTIFIED BY 'aipose123';
GRANT ALL PRIVILEGES ON ai_pose_gallery.* TO 'aipose'@'%';
FLUSH PRIVILEGES;

-- 切换到应用数据库
USE ai_pose_gallery;

-- 创建示例表（后续会被SQLAlchemy覆盖，这里只是确保数据库正常）
CREATE TABLE IF NOT EXISTS health_check (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);