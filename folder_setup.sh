set -e

# folders
mkdir -p data/raw data/synthesized docs sql synthesizer \
         src/entities src/managers app/pages tests

# root files
touch README.md CONTRIBUTING.md requirements.txt .env.example
cat > .gitignore <<'EOF'
.env
__pycache__/
*.pyc
.venv/
venv/
.idea/
.vscode/
.DS_Store
data/synthesized/*.csv
!data/synthesized/.gitkeep
EOF

# docs
touch docs/er_diagram.drawio docs/dimensional_model.drawio docs/architecture.md

# sql
touch sql/01_staging_ddl.sql sql/02_oltp_ddl.sql sql/03_olap_ddl.sql \
      sql/04_oltp_load_dml.sql sql/05_dim_date_load.sql \
      sql/06_sp_load_dimensions.sql sql/07_sp_load_fact.sql \
      sql/08_analytics_queries.sql

# synthesizer
touch synthesizer/data_synthesizer.py synthesizer/history_generator.py \
      synthesizer/staging_loader.py

# src
touch src/db_manager.py \
      src/entities/employee.py src/entities/project.py src/entities/review.py \
      src/managers/base_manager.py src/managers/employee_manager.py \
      src/managers/project_manager.py src/managers/review_manager.py \
      src/managers/analytics_manager.py

# app
touch app/main.py \
      app/pages/1_Onboard_Employee.py app/pages/2_Projects.py \
      app/pages/3_Reviews.py app/pages/4_Update_Department.py \
      app/pages/5_Analytics_Dashboard.py

# keep empty dirs in git
touch data/raw/.gitkeep data/synthesized/.gitkeep tests/.gitkeep

echo "Structure created."