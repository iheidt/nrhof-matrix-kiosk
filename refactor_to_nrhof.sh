#!/bin/bash
# refactor_to_nrhof.sh - Atomic package topology refactoring

set -e  # Exit on any error

echo "🚀 Starting package topology refactoring..."

# 1. Create nrhof directory structure
echo "📁 Creating nrhof/ directory..."
mkdir -p nrhof
touch nrhof/__init__.py

# 2. Git mv all packages (preserves history)
echo "📦 Moving packages with git mv..."
git mv core nrhof/
git mv ui nrhof/
git mv voice nrhof/
git mv routing nrhof/
git mv integrations nrhof/
git mv scenes nrhof/
git mv workers nrhof/
git mv renderers nrhof/

# 3. Move app.py to __main__.py
echo "🎯 Moving app.py to nrhof/__main__.py..."
git mv app.py nrhof/__main__.py

# 4. Bulk rewrite imports
echo "🔄 Updating imports..."
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom core\./from nrhof.core./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom ui\./from nrhof.ui./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom voice\./from nrhof.voice./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom routing\./from nrhof.routing./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom integrations\./from nrhof.integrations./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom scenes\./from nrhof.scenes./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom workers\./from nrhof.workers./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bfrom renderers\./from nrhof.renderers./g' {} +

# Also handle import statements (not just from)
find . -type f -name "*.py" -exec sed -i '' 's/\bimport core\./import nrhof.core./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bimport ui\./import nrhof.ui./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bimport voice\./import nrhof.voice./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bimport routing\./import nrhof.routing./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bimport integrations\./import nrhof.integrations./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bimport scenes\./import nrhof.scenes./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bimport workers\./import nrhof.workers./g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/\bimport renderers\./import nrhof.renderers./g' {} +

echo "✅ Package refactoring complete!"
echo ""
echo "Next steps:"
echo "1. Review changes: git status"
echo "2. Test: python -m nrhof"
echo "3. Commit: git add -A && git commit -m 'refactor: namespace packages under nrhof/'"
