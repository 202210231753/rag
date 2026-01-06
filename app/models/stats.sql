-- 统计相关表结构
-- 执行方式：mysql -u rag_user -p rag_data < app/models/stats.sql
-- 或通过 Python 脚本执行

-- 1. 用户基础画像表
CREATE TABLE IF NOT EXISTS `user_profiles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `gender` VARCHAR(10) NOT NULL COMMENT '性别',
    `age` INT NOT NULL COMMENT '年龄',
    `city` VARCHAR(50) NOT NULL COMMENT '城市',
    `signup_ts` DATETIME NOT NULL COMMENT '注册时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户基础画像表';

-- 2. 用户行为聚合日志表
CREATE TABLE IF NOT EXISTS `behavior_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `pv` INT NOT NULL COMMENT '页面浏览量',
    `uv` INT NOT NULL COMMENT '独立访客数',
    `duration` INT NOT NULL COMMENT '平均停留秒数',
    INDEX `idx_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户行为聚合日志表';

-- 3. 搜索行为日志表
CREATE TABLE IF NOT EXISTS `search_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL COMMENT '用户ID',
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `query` VARCHAR(500) NULL COMMENT '搜索查询词',
    `clicked_doc_id` VARCHAR(255) NULL COMMENT '点击的文档ID',
    `clicked_doc_title` VARCHAR(500) NULL COMMENT '点击的文档标题',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_timestamp` (`timestamp`),
    INDEX `idx_query` (`query`),
    INDEX `idx_clicked_doc_id` (`clicked_doc_id`),
    INDEX `idx_query_doc_id` (`query`, `clicked_doc_id`),
    UNIQUE KEY `uq_search_log_user_time` (`user_id`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索行为日志表';



