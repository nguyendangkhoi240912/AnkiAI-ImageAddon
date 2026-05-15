#!/bin/bash

#############################################################################
# AnkiAI-ImageAddon Update Script v1.0
# Automates version bumping, building, and deployment
# Usage: ./update.sh [version] [--upload] [--github]
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ADDON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_FILE="$ADDON_DIR/AnkiAI_ImageAddon/manifest.json"
BUILD_SCRIPT="$ADDON_DIR/build.py"
CURRENT_VERSION=$(grep '"version"' "$MANIFEST_FILE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

#############################################################################
# Functions
#############################################################################

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Show usage
show_usage() {
    cat << EOF
Usage: ./update.sh [OPTIONS]

OPTIONS:
    version VERSION         Specify version (e.g., 4.5.0)
    --bump-patch           Bump patch version (4.4.1 → 4.4.2)
    --bump-minor           Bump minor version (4.4.1 → 4.5.0)
    --bump-major           Bump major version (4.4.1 → 5.0.0)
    --upload               Upload to AnkiWeb after build
    --github               Create GitHub release after build
    --dry-run              Show what would be done, don't do it
    --help                 Show this help message

EXAMPLES:
    ./update.sh version 4.5.0              # Update to specific version
    ./update.sh --bump-patch --upload      # Bump patch and upload
    ./update.sh --bump-minor --github      # Bump minor and create GitHub release

EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            version)
                NEW_VERSION="$2"
                shift 2
                ;;
            --bump-patch)
                BUMP_PATCH=true
                shift
                ;;
            --bump-minor)
                BUMP_MINOR=true
                shift
                ;;
            --bump-major)
                BUMP_MAJOR=true
                shift
                ;;
            --upload)
                UPLOAD=true
                shift
                ;;
            --github)
                GITHUB=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Calculate new version
calculate_version() {
    if [ -n "$NEW_VERSION" ]; then
        return
    fi
    
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
    
    if [ "$BUMP_MAJOR" = true ]; then
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
    elif [ "$BUMP_MINOR" = true ]; then
        MINOR=$((MINOR + 1))
        PATCH=0
    elif [ "$BUMP_PATCH" = true ]; then
        PATCH=$((PATCH + 1))
    else
        print_error "Please specify version or use --bump-patch/--bump-minor/--bump-major"
        exit 1
    fi
    
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
}

# Validate version format
validate_version() {
    if ! [[ $NEW_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $NEW_VERSION (expected: X.Y.Z)"
        exit 1
    fi
}

# Update version in manifest
update_manifest() {
    print_info "Updating manifest.json from v$CURRENT_VERSION to v$NEW_VERSION..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would update: $MANIFEST_FILE"
        return
    fi
    
    # Create backup
    cp "$MANIFEST_FILE" "$MANIFEST_FILE.backup"
    
    # Update version
    sed -i.bak "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" "$MANIFEST_FILE"
    rm -f "$MANIFEST_FILE.bak"
    
    print_success "Manifest updated to v$NEW_VERSION"
}

# Build addon
build_addon() {
    print_info "Building addon package..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would run: python3 $BUILD_SCRIPT build"
        return
    fi
    
    cd "$ADDON_DIR"
    python3 "$BUILD_SCRIPT" build
    
    print_success "Addon built successfully"
}

# Create git commit and tag
git_commit_and_tag() {
    print_info "Creating git commit and tag..."
    
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_info "Not a git repository, skipping git operations"
        return
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would create commit and tag for v$NEW_VERSION"
        return
    fi
    
    # Stage changes
    git add -A
    
    # Commit
    git commit -m "Release v$NEW_VERSION: Build and optimization updates" || true
    
    # Tag
    git tag -a "v$NEW_VERSION" -m "AnkiAI-ImageAddon v$NEW_VERSION" || true
    
    print_success "Git commit and tag created"
}

# Get latest addon file
get_addon_file() {
    ADDON_FILE="$ADDON_DIR/AnkiAI_ImageAddon-$NEW_VERSION.ankiaddon"
    
    if [ ! -f "$ADDON_FILE" ]; then
        print_error "Addon file not found: $ADDON_FILE"
        exit 1
    fi
    
    print_info "Addon file: $ADDON_FILE"
}

# Show upload instructions
show_upload_instructions() {
    cat << EOF

${YELLOW}═══════════════════════════════════════════════════════════════${NC}
${YELLOW}📤 UPLOAD INSTRUCTIONS${NC}
${YELLOW}═══════════════════════════════════════════════════════════════${NC}

To upload to AnkiWeb:
1. Go to https://ankiweb.net/
2. Log in with your account
3. Navigate to Add-ons → Manage
4. Find AnkiAI-ImageAddon and click "Update"
5. Upload the file: $ADDON_FILE
6. Add release notes (see below)
7. Publish

Release Notes Template:
---
Version $NEW_VERSION
• Update description of what changed
• List new features
• List bug fixes
• List performance improvements
---

Alternative: Direct Distribution
• Share $ADDON_FILE with users
• Users: Tools → Add-ons → Install from file
• Users select the file and restart Anki

${YELLOW}═══════════════════════════════════════════════════════════════${NC}

EOF
}

# Show GitHub release instructions
show_github_instructions() {
    cat << EOF

${YELLOW}═══════════════════════════════════════════════════════════════${NC}
${YELLOW}🚀 GITHUB RELEASE INSTRUCTIONS${NC}
${YELLOW}═══════════════════════════════════════════════════════════════${NC}

To create a GitHub release:
1. Go to your GitHub repository
2. Navigate to Releases → Create a new release
3. Tag version: v$NEW_VERSION
4. Release title: AnkiAI-ImageAddon v$NEW_VERSION
5. Add release notes describing changes
6. Upload the addon file: $ADDON_FILE
7. Publish release

Or use GitHub CLI:
gh release create v$NEW_VERSION "$ADDON_FILE" \\
  --title "AnkiAI-ImageAddon v$NEW_VERSION" \\
  --notes "See DEPLOYMENT_SUMMARY_V$NEW_VERSION.md for details"

${YELLOW}═══════════════════════════════════════════════════════════════${NC}

EOF
}

# Generate changelog
generate_changelog() {
    print_info "You can now generate release notes by reviewing:"
    echo "  • CHANGELOG_V$NEW_VERSION.md (create with your changes)"
    echo "  • DEPLOYMENT_SUMMARY_V$NEW_VERSION.md"
    echo "  • git log --oneline v$CURRENT_VERSION..v$NEW_VERSION"
}

# Main workflow
main() {
    print_header "AnkiAI Update Workflow"
    print_info "Current version: $CURRENT_VERSION"
    
    # Parse arguments
    parse_args "$@"
    
    # Calculate or validate version
    if [ -z "$NEW_VERSION" ]; then
        calculate_version
    fi
    validate_version
    
    print_info "Target version: $NEW_VERSION"
    
    if [ "$DRY_RUN" = true ]; then
        echo ""
        print_header "DRY RUN - No changes will be made"
        echo ""
    fi
    
    # Update manifest
    update_manifest
    
    # Build addon
    build_addon
    
    # Git operations
    git_commit_and_tag
    
    # Get addon file
    get_addon_file
    
    print_header "Update Complete ✅"
    
    # Show file size
    SIZE=$(du -h "$ADDON_FILE" | cut -f1)
    print_info "Addon size: $SIZE"
    
    # Show next steps
    if [ "$UPLOAD" = true ] || [ "$GITHUB" = true ]; then
        echo ""
        if [ "$UPLOAD" = true ]; then
            show_upload_instructions
        fi
        if [ "$GITHUB" = true ]; then
            show_github_instructions
        fi
    else
        echo ""
        echo -e "${BLUE}Next steps:${NC}"
        echo "  1. Review changes: git diff HEAD~1"
        echo "  2. Upload to AnkiWeb or distribute the addon file"
        echo "  3. Update release notes/documentation"
        echo ""
        echo "For upload instructions, run:"
        echo "  ./update.sh --help"
    fi
}

#############################################################################
# Execute
#############################################################################

# Check if help is needed
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    show_usage
    exit 0
fi

# Run main
main "$@"
