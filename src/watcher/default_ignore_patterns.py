DEFAULT_IGNORE_PATTERNS = [
    # Virtual environments
    "venv/", "env/", ".env/", ".venv/", "ENV/", "env.bak/", "venv.bak/",
    "pythonenv*/", "virtualenv/", ".python-version",
    
    # Python specific
    "__pycache__/", "*.pyc", "*.pyo", "*.pyd", ".Python", "*.so",
    ".pytest_cache/", ".coverage", "htmlcov/", ".tox/", ".nox/",
    "*.egg", "*.egg-info/", "dist/", "build/", "eggs/", "parts/",
    "bin/", "var/", "sdist/", "develop-eggs/", "*.manifest", "*.spec",
    "pip-log.txt", "pip-delete-this-directory.txt", ".python-version",
    
    # Node/React/Web Development
    "node_modules/", "jspm_packages/", "bower_components/",
    ".npm/", ".yarn/", ".pnp.*", ".next/", ".nuxt/", ".vuepress/dist",
    ".serverless/", ".fusebox/", ".dynamodb/",
    "build/", "dist/", "out/", "coverage/", ".cache/", ".parcel-cache/",
    "*.min.js", "*.min.css", "bundle.js", "bundle.css",
    ".env.local", ".env.development.local", ".env.test.local", ".env.production.local",
    
    # IDE and Editor specific
    ".idea/", ".vscode/", "*.swp", "*.swo", ".vs/", "*.sublime-workspace",
    "*.sublime-project", ".project", ".settings/", ".classpath", ".factorypath",
    ".nbproject/", ".gradle/", ".metals/", ".bloop/", ".history/",
    "*.iml", "*.ipr", "*.iws", ".idea_modules/", "out/", ".fleet/",
    
    # Common binary and media files
    "*.jpg", "*.jpeg", "*.png", "*.gif", "*.ico", "*.pdf", "*.psd", "*.ai",
    "*.mp3", "*.mp4", "*.wav", "*.flv", "*.mov", "*.wmv", "*.avi", "*.mkv",
    "*.webm", "*.ogg", "*.m4a", "*.aac", "*.wma", "*.mpa", "*.webp",
    "*.bmp", "*.tif", "*.tiff", "*.svg", "*.eps", "*.raw", "*.cr2", "*.nef",
    "*.heic", "*.avif",
    
    # Archives and compressed files
    "*.zip", "*.tar", "*.tar.gz", "*.rar", "*.7z", "*.gz", "*.bz2",
    "*.xz", "*.iso", "*.dmg", "*.tgz", "*.bzip2", "*.lz", "*.lzma",
    "*.tlz", "*.txz", "*.cab", "*.gzip",
    
    # Common data and database files
    "*.csv", "*.xls", "*.xlsx", "*.xlsm", "*.xlsb", "*.doc", "*.docx",
    "*.ppt", "*.pptx", "*.accdb", "*.mdb", "*.db", "*.db3", "*.sqlite",
    "*.sqlite3", "*.rdb", "*.hdb", "*.json", "*.yaml", "*.yml",
    "*.dat", "*.bak", "*.bkp", "*.dump", "*.sql", "*.mdf", "*.ldf",
    
    # Logs and temporary files
    "*.log", "tmp/", "temp/", "logs/", ".temp/", ".tmp/",
    "*.pid", "*.seed", "*.pid.lock", "*.log.*", "log/", ".log/",
    "*~", "*.bak", "*.swp", "*.tmp", "*.temp", "._*",
    
    # OS specific
    ".DS_Store", ".DS_Store?", "._*", ".Spotlight-V100",
    ".Trashes", "ehthumbs.db", "Thumbs.db", "Desktop.ini",
    "$RECYCLE.BIN/", "System Volume Information",
    
    # Version control
    ".git/", ".hg/", ".svn/", "CVS/", ".bzr/", "_darcs/",
    ".gitattributes", ".gitmodules", ".hgignore", ".hgsub", ".hgsubstate",
    
    # Build and dependency files
    "Gemfile.lock", "yarn.lock", "package-lock.json", "composer.lock",
    "pipfile.lock", "poetry.lock", "mix.lock", "cargo.lock",
    "*.pid", "*.seed", "*.pid.lock",
    
    # Configuration and local settings
    ".env*", "*.local", "*.local.*", "config.local.*",
    "settings.local.*", "local_settings.*", ".editorconfig",
    
    # Documentation and reports
    "docs/_build/", "site/", "_site/", "public/", ".docusaurus",
    "sphinx-docs/_build/", "coverage/", "reports/", ".coverage",
    ".hypothesis/", ".pytest_cache/",
    
    # Container and deployment
    ".docker/", "*.dockerignore", "docker-compose.override.yml",
    "kubernetes/", ".kube/", ".helm/", "chart/", "manifests/",
    
    # Security and credentials
    "*.pem", "*.key", "*.crt", "*.cer", "*.p12", "*.pfx",
    "*.csr", "*.srl", "id_rsa", "id_dsa", ".ssh/",
    
    # Compiled files and binaries
    "*.com", "*.class", "*.dll", "*.exe", "*.o", "*.obj",
    "*.app", "*.dylib", "*.lib", "*.out", "*.ko", "*.so.*",
    
    # Mobile development
    "*.apk", "*.aab", "*.ipa", "*.dSYM.zip", "*.dSYM",
    "Pods/", ".gradle/", "build/", "captures/", ".externalNativeBuild/",
    
    # Misc development files
    ".sass-cache/", ".stylelintcache", ".eslintcache",
    "*.swf", "*.air", "*.ipa", "*.orig", ".terraform/",
    ".vagrant/", ".bundle/", "vendor/bundle/",
]