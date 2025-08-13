#!/bin/bash
# scripts/release/create-final.sh
# Script to create final release tags for openai-model-registry

set -e  # Exit on any error

VERSION=""
RELEASE_TYPE="library"  # library or data
SIGN_TAG=true

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --data)
            RELEASE_TYPE="data"
            shift
            ;;
        --no-sign)
            SIGN_TAG=false
            shift
            ;;
        -*)
            echo "Unknown option $1"
            exit 1
            ;;
        *)
            if [[ -z "$VERSION" ]]; then
                VERSION=$1
            else
                echo "Too many arguments"
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version> [--data] [--no-sign]"
    echo "Example: $0 1.0.0"
    echo "Example: $0 1.0.0 --data"
    echo "Example: $0 1.0.0 --no-sign"
    echo ""
    echo "This script creates a final release tag and pushes it to origin."
    echo ""
    echo "Library release tag format: v<version>"
    echo "Data release tag format: data-v<version>"
    echo ""
    echo "Options:"
    echo "  --data       Create data release instead of library release"
    echo "  --no-sign    Create unsigned tag (useful when GPG is not configured)"
    echo ""
    echo "Current branch: $(git branch --show-current)"
    echo "Latest commit: $(git log --oneline -1)"
    exit 1
fi

# Validate version format (basic check)
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Error: Version must be in format X.Y.Z (e.g., 1.0.0)"
    echo "Provided: $VERSION"
    exit 1
fi

# Set tag name based on release type
if [[ "$RELEASE_TYPE" == "data" ]]; then
    TAG_NAME="data-v$VERSION"
    TAG_MESSAGE="Data Release $VERSION"
    RC_TAG_PATTERN="data-v$VERSION-rc"
else
    TAG_NAME="v$VERSION"
    TAG_MESSAGE="Release $VERSION"
    RC_TAG_PATTERN="v$VERSION-rc"
fi

# Validate we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo "❌ Error: Must be on main branch"
    echo "Current branch: $CURRENT_BRANCH"
    echo "Switch to main branch first: git checkout main"
    exit 1
fi

# Ensure we're up to date
echo "🔄 Ensuring main branch is up to date..."
git pull --ff-only origin main

# Check if tag already exists
if git tag -l | grep -q "^$TAG_NAME$"; then
    echo "❌ Error: Tag '$TAG_NAME' already exists"
    echo "Existing tags:"
    git tag -l | grep -E "^(v|data-v)" | sort -V | tail -10
    exit 1
fi

# Check if there's a corresponding RC tag
RC_TAGS=$(git tag -l | grep "^$RC_TAG_PATTERN" | sort -V)
if [[ -z "$RC_TAGS" ]]; then
    echo "⚠️  Warning: No release candidate found for version $VERSION"
    echo "   Expected pattern: $RC_TAG_PATTERN*"
    echo "   Consider creating an RC first: scripts/release/create-rc.sh $VERSION 1"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled by user"
        exit 1
    fi
else
    echo "✅ Found release candidate(s):"
    echo "$RC_TAGS"
    echo ""
fi

# Show what we're about to do
echo "🏷️  Creating $RELEASE_TYPE final release:"
echo "   Version: $VERSION"
echo "   Tag Name: $TAG_NAME"
echo "   Branch: $CURRENT_BRANCH"
echo "   Commit: $(git log --oneline -1)"
echo ""

# Confirm with user
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled by user"
    exit 1
fi

# Create the tag
echo "🏷️  Creating tag '$TAG_NAME'..."
if [[ "$SIGN_TAG" == "true" ]]; then
    git tag -a "$TAG_NAME" -m "$TAG_MESSAGE"
else
    git tag "$TAG_NAME"
fi

# Push the tag
echo "🚀 Pushing tag to origin..."
git push origin "$TAG_NAME"

echo ""
echo "✅ Final release created successfully!"
echo "   Tag: $TAG_NAME"
echo "   GitHub Actions will now:"
if [[ "$RELEASE_TYPE" == "data" ]]; then
    echo "   - Build and package data files"
    echo "   - Create GitHub release"
    echo "   - Mark as production release"
else
    echo "   - Build Python package"
    echo "   - Run tests"
    echo "   - Publish to PyPI"
    echo "   - Create GitHub release"
    echo "   - Mark as production release"
fi
echo ""
echo "📋 Next steps:"
echo "   1. Monitor GitHub Actions: https://github.com/yaniv-golan/openai-model-registry/actions"
if [[ "$RELEASE_TYPE" == "library" ]]; then
    echo "   2. Test from PyPI: pip install openai-model-registry==$VERSION"
    echo "   3. Update documentation if needed"
fi
echo "   4. Announce the release"
echo ""
