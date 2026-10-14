-- =============================================================================
-- Migration 09: Role-Based Access Control (RBAC) DDL
-- Tables: app_users, app_audit_log
-- =============================================================================

CREATE TABLE IF NOT EXISTS app_users (
    user_id              INT AUTO_INCREMENT PRIMARY KEY,
    username             VARCHAR(100) NOT NULL,
    password_hash        VARCHAR(255) NOT NULL,
    role                 ENUM('admin','hr_manager','project_manager','analyst') NOT NULL,
    is_active            TINYINT(1) NOT NULL DEFAULT 1,
    must_change_password TINYINT(1) NOT NULL DEFAULT 1,
    failed_attempts      INT NOT NULL DEFAULT 0,
    locked_until         DATETIME NULL,
    password_changed_at  DATETIME NULL,
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login           DATETIME NULL,
    created_by           INT NULL,
    UNIQUE KEY uq_app_users_username (username),
    CONSTRAINT fk_user_creator FOREIGN KEY (created_by)
        REFERENCES app_users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS app_audit_log (
    audit_id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_type         VARCHAR(40) NOT NULL,
    actor_user_id      INT NULL,
    target_user_id     INT NULL,
    username_attempted VARCHAR(100) NULL,
    details            JSON NULL,
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_created (created_at),
    INDEX idx_audit_actor (actor_user_id),
    INDEX idx_audit_event (event_type)
) ENGINE=InnoDB;

-- =============================================================================
-- Default Initial Administrator Seed (Idempotent)
-- Default Credentials:
--   Username: admin
--   Password: AdminPass1234!
-- Pre-computed bcrypt hash (cost 12):
--   $2b$12$yb/9LOt8LmDj2oiz3ZVAL.dnJRUz02QlpmyoXEk49fWMztT7i6Ge6
-- =============================================================================
INSERT INTO app_users (
    username,
    password_hash,
    role,
    is_active,
    must_change_password
) VALUES (
    'admin',
    '$2b$12$yb/9LOt8LmDj2oiz3ZVAL.dnJRUz02QlpmyoXEk49fWMztT7i6Ge6',
    'admin',
    1,
    1
)
ON DUPLICATE KEY UPDATE username = username;

