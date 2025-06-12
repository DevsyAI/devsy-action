#!/bin/bash

# Devsy Action Installer
# 
# This script automatically sets up Devsy Action in your repository by:
# 1. Creating the workflow file (.github/workflows/devsy.yml)
# 2. Creating an optional setup script (.devsy/setup.sh)

set -e

echo "🚀 Installing Devsy Action..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: This script must be run from the root of a git repository"
    exit 1
fi

# Create .github/workflows directory
echo "📁 Creating .github/workflows directory..."
mkdir -p .github/workflows

# Download workflow file
echo "📄 Downloading workflow file..."
if command -v curl &> /dev/null; then
    curl -s -o .github/workflows/devsy.yml https://raw.githubusercontent.com/DevsyAI/devsy-action/main/devsy.yml
    echo "✅ Created .github/workflows/devsy.yml"
else
    echo "❌ Error: curl is required but not installed"
    exit 1
fi

# Ask if user wants setup script
echo ""
read -p "📦 Do you want to create a setup script for dependencies? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📁 Creating .devsy directory..."
    mkdir -p .devsy
    
    echo "📄 Downloading setup script template..."
    curl -s -o .devsy/setup.sh https://raw.githubusercontent.com/DevsyAI/devsy-action/main/setup.sh
    chmod +x .devsy/setup.sh
    echo "✅ Created .devsy/setup.sh (edit to uncomment sections you need)"
fi

echo ""
echo "🎉 Devsy Action installed successfully!"
echo ""
echo "Next steps:"
echo "1. 🔧 Configure repository settings:"
echo "   • Go to Settings → Actions → General"
echo "   • Check 'Allow GitHub Actions to create and approve pull requests'"
echo "   • Select 'Read and write permissions'"
echo ""
echo "2. 🔑 Add your Anthropic API key:"
echo "   • Go to Settings → Secrets and variables → Actions"
echo "   • Create secret: ANTHROPIC_API_KEY"
echo "   • Get API key from: https://console.anthropic.com"
echo ""
echo "3. 🔗 (Optional) Add callback token for webhooks:"
echo "   • Org Admin: Generate token at devsy.ai Settings page"
echo "   • Create secret: DEVSY_ORG_OAUTH_TOKEN"
echo ""
echo "4. 🚀 You're all set!"
echo "   • Use Devsy like you normally do in your existing tools"

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "4. 📦 Edit .devsy/setup.sh:"
    echo "   • Uncomment the sections for your project's language/framework"
    echo "   • This will install dependencies before Devsy runs"
fi

echo ""
echo "📖 Full documentation: https://github.com/DevsyAI/devsy-action"