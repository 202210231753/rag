-- 同义词功能相关表结构
-- 执行方式：mysql -u rag_user -p rag_data < app/models/synonym.sql
-- 或通过 Python 脚本执行

-- 1. 同义词组表
CREATE TABLE IF NOT EXISTS `synonym_groups` (
    `group_id` INT AUTO_INCREMENT PRIMARY KEY,
    `domain` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '领域',
    `canonical` VARCHAR(255) NOT NULL COMMENT '标准词',
    `enabled` INT NOT NULL DEFAULT 1 COMMENT '是否启用：1启用，0禁用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_domain` (`domain`),
    INDEX `idx_domain_canonical` (`domain`, `canonical`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同义词组表';

-- 2. 同义词项表
CREATE TABLE IF NOT EXISTS `synonym_terms` (
    `term_id` INT AUTO_INCREMENT PRIMARY KEY,
    `group_id` INT NOT NULL COMMENT '同义词组ID',
    `term` VARCHAR(255) NOT NULL COMMENT '同义词',
    `weight` FLOAT NOT NULL DEFAULT 1.0 COMMENT '权重',
    INDEX `idx_group_id` (`group_id`),
    INDEX `idx_group_term` (`group_id`, `term`),
    CONSTRAINT `fk_synonym_term_group` FOREIGN KEY (`group_id`) 
        REFERENCES `synonym_groups` (`group_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同义词项表';

-- 3. 同义词候选表
CREATE TABLE IF NOT EXISTS `synonym_candidates` (
    `candidate_id` INT AUTO_INCREMENT PRIMARY KEY,
    `domain` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '领域',
    `canonical` VARCHAR(255) NOT NULL COMMENT '标准词',
    `synonym` VARCHAR(255) NOT NULL COMMENT '候选同义词',
    `score` FLOAT NOT NULL COMMENT '相似度分数',
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态：pending/approved/rejected',
    `source` VARCHAR(50) NOT NULL DEFAULT 'embedding' COMMENT '来源：embedding/manual等',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_domain` (`domain`),
    INDEX `idx_status` (`status`),
    INDEX `idx_domain_status` (`domain`, `status`),
    INDEX `idx_domain_canonical_synonym` (`domain`, `canonical`, `synonym`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同义词候选表';



